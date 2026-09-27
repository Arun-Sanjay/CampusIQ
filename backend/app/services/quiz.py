"""Quiz CRUD, attempt scoring, adaptive difficulty, weak-area detection.

Phase 11 (F3) — DAA Unit IV (greedy adaptive difficulty), DMS Unit II
(boolean threshold detection of weak topics).
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.quiz import CIEComponent, Difficulty, Question, QuestionType, Quiz, QuizAttempt, QuizMode
from app.models.user import Subject, User, UserRole
from app.services import campus_iq_score, enrollment, xp
from app.schemas.quiz import (
    AttemptHistoryRow,
    COAttainmentRow,
    GradedAnswer,
    ProctorEventIn,
    ProctorReport,
    ProctorReportRow,
    QuestionAnswer,
    QuestionStudentView,
    QuestionTeacherView,
    QuizAttemptResponse,
    QuizForStudent,
    QuizForTeacher,
    QuizResponse,
    QuizUpdate,
    StartAttemptResponse,
    WeakAreaResponse,
)

logger = logging.getLogger(__name__)


# ── Adaptive difficulty thresholds (greedy heuristic) ──
PROMOTE_AVG_THRESHOLD = 80.0   # avg ≥ 80%  → next difficulty up
DEMOTE_AVG_THRESHOLD = 50.0    # avg ≤ 50%  → next difficulty down
ADAPTIVE_WINDOW = 3            # consider the last N attempts of the same subject

# ── Weak-area boolean threshold ──
WEAK_TOPIC_SCORE_THRESHOLD = 60.0    # < 60% correct on a topic
WEAK_TOPIC_MIN_ATTEMPTS = 2          # only flag once we have ≥ 2 data points


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════

def _require_teacher(user: User) -> None:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can manage quizzes.",
        )


def _validate_quiz_owner(quiz: Quiz, user: User) -> None:
    if user.role == UserRole.TEACHER and quiz.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this quiz")


def _quiz_aggregate_stats(db: Session, quiz_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int, float | None]]:
    """Return {quiz_id: (question_count, attempt_count, avg_score)}."""
    if not quiz_ids:
        return {}

    q_counts = dict(
        db.execute(
            select(Question.quiz_id, func.count(Question.id))
            .where(Question.quiz_id.in_(quiz_ids))
            .group_by(Question.quiz_id)
        ).all()
    )
    attempt_counts = dict(
        db.execute(
            select(QuizAttempt.quiz_id, func.count(QuizAttempt.id))
            .where(QuizAttempt.quiz_id.in_(quiz_ids))
            .group_by(QuizAttempt.quiz_id)
        ).all()
    )
    avg_scores = dict(
        db.execute(
            select(QuizAttempt.quiz_id, func.avg(QuizAttempt.score))
            .where(QuizAttempt.quiz_id.in_(quiz_ids))
            .group_by(QuizAttempt.quiz_id)
        ).all()
    )

    return {
        qid: (
            int(q_counts.get(qid, 0)),
            int(attempt_counts.get(qid, 0)),
            float(avg_scores[qid]) if avg_scores.get(qid) is not None else None,
        )
        for qid in quiz_ids
    }


def _to_quiz_response(
    quiz: Quiz,
    *,
    subject: Subject | None,
    question_count: int,
    attempt_count: int,
    avg_score: float | None,
    attempts_used: int = 0,
    can_attempt: bool = True,
) -> QuizResponse:
    return QuizResponse(
        id=quiz.id,
        subject_id=quiz.subject_id,
        document_id=quiz.document_id,
        created_by_id=quiz.created_by_id,
        title=quiz.title,
        description=quiz.description,
        difficulty=quiz.difficulty.value,
        time_limit_minutes=quiz.time_limit_minutes,
        is_published=quiz.is_published,
        is_ai_generated=quiz.is_ai_generated,
        created_at=quiz.created_at,
        question_count=question_count,
        attempt_count=attempt_count,
        avg_score=avg_score,
        subject_code=subject.code if subject else None,
        subject_name=subject.name if subject else None,
        mode=quiz.mode.value,
        max_attempts=quiz.max_attempts,
        requires_proctoring=quiz.requires_proctoring,
        available_from=quiz.available_from,
        available_until=quiz.available_until,
        cie_component=quiz.cie_component.value if quiz.cie_component else None,
        total_marks=quiz.total_marks,
        attempts_used=attempts_used,
        can_attempt=can_attempt,
    )


def _student_attempt_state(db: Session, quiz: Quiz, student_id: uuid.UUID) -> tuple[int, bool]:
    """(submitted attempts used, can_attempt) for this student on this quiz."""
    # A started-but-unsubmitted attempt has total_questions == 0; a real
    # submission sets it >= 1. Count only submitted attempts.
    used = db.scalar(
        select(func.count()).select_from(QuizAttempt).where(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.student_id == student_id,
            QuizAttempt.total_questions > 0,
        )
    ) or 0
    within_window = _within_availability(quiz)
    attempts_ok = quiz.max_attempts == 0 or used < quiz.max_attempts
    return used, bool(within_window and attempts_ok)


def _as_naive_utc(dt: datetime | None) -> datetime | None:
    """Normalize to naive UTC so SQLite (naive) and aware datetimes compare."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _within_availability(quiz: Quiz) -> bool:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    af = _as_naive_utc(quiz.available_from)
    au = _as_naive_utc(quiz.available_until)
    if af and now < af:
        return False
    if au and now > au:
        return False
    return True


def _question_to_student_view(q: Question) -> QuestionStudentView:
    return QuestionStudentView(
        id=q.id,
        order_index=q.order_index,
        question_text=q.question_text,
        question_type=q.question_type.value,
        options=q.options,
        difficulty=q.difficulty.value,
        topic=q.topic,
        marks=q.marks,
        co=q.co,
        bloom=q.bloom,
    )


def _question_to_teacher_view(q: Question) -> QuestionTeacherView:
    return QuestionTeacherView(
        id=q.id,
        order_index=q.order_index,
        question_text=q.question_text,
        question_type=q.question_type.value,
        options=q.options,
        difficulty=q.difficulty.value,
        topic=q.topic,
        marks=q.marks,
        co=q.co,
        bloom=q.bloom,
        correct_answer=q.correct_answer,
        explanation=q.explanation,
    )


# ════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════

def list_quizzes(
    db: Session,
    user: User,
    *,
    subject_id: uuid.UUID | None = None,
    only_mine: bool = False,
) -> list[QuizResponse]:
    """List quizzes visible to the current user.

    - Teachers: their own quizzes
    - Admins: all quizzes
    - Students: only published quizzes (or quizzes they've attempted)
    """
    stmt = (
        select(Quiz, Subject)
        .join(Subject, Quiz.subject_id == Subject.id)
        .order_by(Quiz.created_at.desc())
    )

    if user.role == UserRole.TEACHER:
        stmt = stmt.where(Quiz.created_by_id == user.id)
    elif user.role == UserRole.STUDENT:
        # Published quizzes, but only from subjects the student is enrolled in.
        enrolled = enrollment.enrolled_subject_ids_for_student(db, user.id)
        stmt = stmt.where(Quiz.is_published.is_(True))
        stmt = stmt.where(Quiz.subject_id.in_(enrolled))
    elif only_mine and user.role == UserRole.ADMIN:
        stmt = stmt.where(Quiz.created_by_id == user.id)

    if subject_id is not None:
        stmt = stmt.where(Quiz.subject_id == subject_id)

    rows = db.execute(stmt).all()
    quiz_ids = [q.id for q, _ in rows]
    stats = _quiz_aggregate_stats(db, quiz_ids)

    return [
        _to_quiz_response(
            q,
            subject=s,
            question_count=stats.get(q.id, (0, 0, None))[0],
            attempt_count=stats.get(q.id, (0, 0, None))[1],
            avg_score=stats.get(q.id, (0, 0, None))[2],
        )
        for q, s in rows
    ]


def get_quiz_for_student(db: Session, quiz_id: uuid.UUID, user: User) -> QuizForStudent:
    """Return a quiz with questions but no answers (used by the taking screen)."""
    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions))
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if user.role == UserRole.STUDENT:
        if not quiz.is_published:
            raise HTTPException(status_code=404, detail="Quiz not found")
        # Must be enrolled in the quiz's subject (don't leak existence → 404).
        if quiz.subject_id not in enrollment.enrolled_subject_ids_for_student(db, user.id):
            raise HTTPException(status_code=404, detail="Quiz not found")

    subject = db.get(Subject, quiz.subject_id)
    stats = _quiz_aggregate_stats(db, [quiz.id])[quiz.id]

    used, can = (
        _student_attempt_state(db, quiz, user.id) if user.role == UserRole.STUDENT else (0, True)
    )
    base = _to_quiz_response(
        quiz,
        subject=subject,
        question_count=stats[0],
        attempt_count=stats[1],
        avg_score=stats[2],
        attempts_used=used,
        can_attempt=can,
    )
    return QuizForStudent(
        **base.model_dump(),
        questions=[_question_to_student_view(q) for q in quiz.questions],
    )


def get_quiz_for_teacher(db: Session, quiz_id: uuid.UUID, user: User) -> QuizForTeacher:
    """Return the full quiz including answers + explanations (teacher / admin)."""
    _require_teacher(user)
    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions))
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _validate_quiz_owner(quiz, user)

    subject = db.get(Subject, quiz.subject_id)
    stats = _quiz_aggregate_stats(db, [quiz.id])[quiz.id]

    base = _to_quiz_response(
        quiz,
        subject=subject,
        question_count=stats[0],
        attempt_count=stats[1],
        avg_score=stats[2],
    )
    return QuizForTeacher(
        **base.model_dump(),
        questions=[_question_to_teacher_view(q) for q in quiz.questions],
    )


def update_quiz(
    db: Session,
    quiz_id: uuid.UUID,
    data: QuizUpdate,
    user: User,
) -> QuizForTeacher:
    """Update quiz metadata and optionally replace questions."""
    _require_teacher(user)
    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions))
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _validate_quiz_owner(quiz, user)

    if data.title is not None:
        quiz.title = data.title.strip()
    if data.description is not None:
        quiz.description = data.description
    if data.difficulty is not None:
        quiz.difficulty = Difficulty(data.difficulty)
    if data.time_limit_minutes is not None:
        quiz.time_limit_minutes = data.time_limit_minutes
    if data.is_published is not None:
        quiz.is_published = data.is_published
    if data.mode is not None:
        quiz.mode = QuizMode(data.mode)
    if data.max_attempts is not None:
        quiz.max_attempts = data.max_attempts
    if data.requires_proctoring is not None:
        quiz.requires_proctoring = data.requires_proctoring
    if data.available_from is not None:
        quiz.available_from = data.available_from
    if data.available_until is not None:
        quiz.available_until = data.available_until
    if data.cie_component is not None:
        quiz.cie_component = CIEComponent(data.cie_component)

    if data.questions is not None:
        # Replace all questions wholesale (simpler than diffing for now)
        for q in list(quiz.questions):
            db.delete(q)
        db.flush()
        for idx, qu in enumerate(data.questions):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    order_index=qu.order_index or idx,
                    question_text=qu.question_text,
                    question_type=QuestionType(qu.question_type),
                    options=qu.options,
                    correct_answer=qu.correct_answer,
                    explanation=qu.explanation,
                    difficulty=Difficulty(qu.difficulty),
                    topic=qu.topic,
                    marks=qu.marks,
                    co=qu.co,
                    bloom=qu.bloom,
                )
            )
        quiz.total_marks = sum(qu.marks for qu in data.questions)

    db.commit()
    db.refresh(quiz)
    return get_quiz_for_teacher(db, quiz.id, user)


def delete_quiz(db: Session, quiz_id: uuid.UUID, user: User) -> None:
    _require_teacher(user)
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _validate_quiz_owner(quiz, user)
    db.delete(quiz)
    db.commit()


# ════════════════════════════════════════════════════════════════
# Attempt scoring + adaptive difficulty
# ════════════════════════════════════════════════════════════════

def _build_answer_bit_vector(graded: list[GradedAnswer]) -> str:
    """Per-question 1/0 string for the Hamming similarity checker (Phase 19, F23)."""
    return "".join("1" if g.is_correct else "0" for g in graded)


def _next_difficulty_recommendation(
    db: Session,
    *,
    student_id: uuid.UUID,
    subject_id: uuid.UUID,
    current_difficulty: Difficulty,
) -> Difficulty:
    """Greedy adaptive selection (DAA Unit IV).

    Look at the student's last N attempts on this subject. If they're cruising
    (avg ≥ 80%), promote to the next harder difficulty. If they're struggling
    (avg ≤ 50%), demote. Otherwise stay put.
    """
    recent_scores = db.scalars(
        select(QuizAttempt.score)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .where(QuizAttempt.student_id == student_id)
        .where(Quiz.subject_id == subject_id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(ADAPTIVE_WINDOW)
    ).all()
    if not recent_scores:
        return current_difficulty

    avg = sum(float(s) for s in recent_scores) / len(recent_scores)
    order = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
    idx = order.index(current_difficulty)

    if avg >= PROMOTE_AVG_THRESHOLD and idx < len(order) - 1:
        return order[idx + 1]
    if avg <= DEMOTE_AVG_THRESHOLD and idx > 0:
        return order[idx - 1]
    return current_difficulty


def start_attempt(db: Session, *, quiz_id: uuid.UUID, user: User) -> StartAttemptResponse:
    """Begin an attempt: server-stamp started_at (timer anchor), enforce the
    availability window + single-attempt limit. Reuses an in-progress row if any."""
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students take quizzes.")
    quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions)))
    if quiz is None or not quiz.is_published:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if quiz.subject_id not in enrollment.enrolled_subject_ids_for_student(db, user.id):
        raise HTTPException(status_code=404, detail="Quiz not found")
    if not _within_availability(quiz):
        raise HTTPException(status_code=403, detail="This quiz is not currently available.")
    used, _ = _student_attempt_state(db, quiz, user.id)
    if quiz.max_attempts > 0 and used >= quiz.max_attempts:
        raise HTTPException(status_code=409, detail="You have already used all attempts for this quiz.")

    attempt = db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == user.id, QuizAttempt.total_questions == 0
        )
    )
    if attempt is None:
        attempt = QuizAttempt(
            quiz_id=quiz.id, student_id=user.id, score=Decimal("0"), total_questions=0,
            correct_count=0, mode=quiz.mode, is_proctored=quiz.requires_proctoring,
            attempt_number=used + 1, started_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
    db.commit()
    db.refresh(attempt)
    tl = quiz.time_limit_minutes * 60 if quiz.time_limit_minutes else None
    # SQLite drops tzinfo on round-trip; re-attach UTC so the client parses it
    # correctly (a naive ISO string is read as LOCAL time by JS Date()).
    started = attempt.started_at or datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return StartAttemptResponse(
        attempt_id=attempt.id, started_at=started,
        server_now=datetime.now(timezone.utc), time_limit_seconds=tl,
        requires_proctoring=quiz.requires_proctoring, mode=quiz.mode.value,
    )


def record_proctor_event(db: Session, *, quiz_id: uuid.UUID, user: User, event: ProctorEventIn) -> None:
    """Increment the relevant proctor counter + append to the violation log."""
    attempt = db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == user.id, QuizAttempt.total_questions == 0
        ).order_by(QuizAttempt.started_at.desc())
    )
    if attempt is None:
        return
    t = event.type
    if t in ("tab_switch", "blur"):
        attempt.tab_switch_count += 1
    elif t == "fullscreen_exit":
        attempt.fullscreen_exits += 1
    elif t in ("copy", "paste", "contextmenu", "devtools"):
        attempt.copy_paste_attempts += 1
    elif t == "face_absent":
        attempt.face_absent_seconds += int(event.seconds or 1)
    elif t == "face_multiple":
        attempt.face_multiple_seconds += int(event.seconds or 1)
    log = list(attempt.violations or [])
    log.append({"type": t, "detail": event.detail})
    attempt.violations = log[-500:]
    db.commit()


def _feed_cie_from_attempt(db: Session, quiz: Quiz, attempt: QuizAttempt, graded: list[GradedAnswer]) -> None:
    """Test-mode attempt → an ExamResult so it feeds the subject's CIE.

    Best-effort: never let grading wiring break quiz submission.
    """
    if quiz.mode != QuizMode.TEST or quiz.cie_component is None:
        return
    from app.models.grading import Exam, ExamKind, ExamResult, ResultSource, SchemeStatus
    from app.services import grade_engine, grading

    comp = quiz.cie_component.value  # quiz_1 / test_2 ...
    component_key = "quizzes" if comp.startswith("quiz") else "tests"
    sequence = 2 if comp.endswith("_2") else 1
    exam = db.scalar(select(Exam).where(Exam.quiz_id == quiz.id))
    if exam is None:
        exam = Exam(
            subject_id=quiz.subject_id, created_by_id=quiz.created_by_id, title=quiz.title,
            kind=ExamKind.TEST if component_key == "tests" else ExamKind.QUIZ,
            component_key=component_key, sequence=sequence,
            max_marks=quiz.total_marks or sum(float(g.marks_possible) for g in graded),
            quiz_id=quiz.id, scheme_status=SchemeStatus.READY, is_published=True,
        )
        db.add(exam)
        db.flush()
    per_q = [{"co": g.co, "obtained": float(g.marks_awarded), "max": float(g.marks_possible)} for g in graded if g.co]
    co_rows = grade_engine.compute_co_attainment(per_q)
    per_co = {r.co: {"obtained": r.obtained, "max": r.max, "pct": r.pct} for r in co_rows}
    total_obt = sum(float(g.marks_awarded) for g in graded)
    total_max = sum(float(g.marks_possible) for g in graded)
    result = db.scalar(select(ExamResult).where(ExamResult.exam_id == exam.id, ExamResult.student_id == attempt.student_id))
    if result is None:
        result = ExamResult(exam_id=exam.id, student_id=attempt.student_id)
        db.add(result)
    result.total_obtained = grade_engine.round2(total_obt)
    result.total_max = grade_engine.round2(total_max)
    result.percentage = grade_engine.round2(grade_engine.safe_pct(total_obt, total_max))
    result.per_co = per_co
    result.quiz_attempt_id = attempt.id
    result.source = ResultSource.QUIZ
    result.is_teacher_approved = True
    result.finalized = True
    db.flush()
    grading.recompute_subject_grade(db, quiz.subject_id, attempt.student_id)


def submit_attempt(
    db: Session,
    *,
    quiz_id: uuid.UUID,
    user: User,
    answers: list[QuestionAnswer],
    time_taken_seconds: int | None,
    started_attempt_id: uuid.UUID | None = None,
    proctor=None,
    violations: list[dict] | None = None,
) -> QuizAttemptResponse:
    """Grade a student attempt (marks-based), persist it, return per-question feedback."""
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit quiz attempts.",
        )

    quiz = db.scalar(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions))
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if not quiz.is_published:
        raise HTTPException(status_code=400, detail="Quiz has not been published yet")
    if quiz.subject_id not in enrollment.enrolled_subject_ids_for_student(db, user.id):
        raise HTTPException(
            status_code=403, detail="You are not enrolled in this subject"
        )

    questions_by_id = {q.id: q for q in quiz.questions}
    if not questions_by_id:
        raise HTTPException(status_code=400, detail="Quiz has no questions")

    # Reuse the started attempt (test mode); else enforce single-attempt for the
    # practice-submit-directly path and create a fresh row.
    started = None
    if started_attempt_id is not None:
        started = db.get(QuizAttempt, started_attempt_id)
        if started is None or started.student_id != user.id or started.quiz_id != quiz.id:
            raise HTTPException(status_code=404, detail="Attempt not found")
        if started.total_questions > 0:
            raise HTTPException(status_code=409, detail="This attempt was already submitted.")
    else:
        used, _ = _student_attempt_state(db, quiz, user.id)
        if quiz.max_attempts > 0 and used >= quiz.max_attempts:
            raise HTTPException(status_code=409, detail="You have already used all attempts for this quiz.")

    answers_by_qid: dict[uuid.UUID, str] = {}
    for a in answers:
        answers_by_qid[a.question_id] = a.student_answer

    graded: list[GradedAnswer] = []
    correct_count = 0
    marks_obtained = 0.0
    marks_possible = 0.0

    # Iterate questions in their canonical order so the bit vector is stable
    for q in sorted(quiz.questions, key=lambda x: x.order_index):
        student_ans = (answers_by_qid.get(q.id) or "").strip()
        is_correct = _is_answer_correct(q, student_ans)
        q_marks = float(q.marks or 1)
        awarded = q_marks if is_correct else 0.0
        marks_possible += q_marks
        marks_obtained += awarded
        if is_correct:
            correct_count += 1
        graded.append(
            GradedAnswer(
                question_id=q.id,
                question_text=q.question_text,
                student_answer=student_ans,
                correct_answer=q.correct_answer,
                is_correct=is_correct,
                topic=q.topic,
                difficulty=q.difficulty.value,
                explanation=q.explanation,
                marks_awarded=awarded,
                marks_possible=q_marks,
                co=q.co,
            )
        )

    total = len(quiz.questions)
    score_percent = round((correct_count / total) * 100, 2) if total else 0.0
    bit_vector = _build_answer_bit_vector(graded)
    answers_json = [
        {
            "question_id": str(g.question_id),
            "student_answer": g.student_answer,
            "is_correct": g.is_correct,
            "topic": g.topic,
            "marks_awarded": g.marks_awarded,
            "co": g.co,
        }
        for g in graded
    ]

    # Persist (reuse started row in test mode, else create).
    attempt = started or QuizAttempt(quiz_id=quiz.id, student_id=user.id, mode=quiz.mode)
    attempt.score = Decimal(str(score_percent))
    attempt.total_questions = total
    attempt.correct_count = correct_count
    attempt.time_taken_seconds = time_taken_seconds
    attempt.answers = answers_json
    attempt.answer_bit_vector = bit_vector
    attempt.marks_obtained = Decimal(str(round(marks_obtained, 2)))
    attempt.marks_possible = Decimal(str(round(marks_possible, 2)))
    attempt.is_proctored = quiz.requires_proctoring
    attempt.completed_at = datetime.now(timezone.utc)
    if proctor is not None:
        attempt.tab_switch_count = max(attempt.tab_switch_count or 0, proctor.tab_switch_count)
        attempt.fullscreen_exits = max(attempt.fullscreen_exits or 0, proctor.fullscreen_exits)
        attempt.copy_paste_attempts = max(attempt.copy_paste_attempts or 0, proctor.copy_paste_attempts)
        attempt.face_absent_seconds = max(attempt.face_absent_seconds or 0, proctor.face_absent_seconds)
        attempt.face_multiple_seconds = max(attempt.face_multiple_seconds or 0, proctor.face_multiple_seconds)
        attempt.auto_submitted = proctor.auto_submitted
    if violations:
        merged = list(attempt.violations or []) + violations
        attempt.violations = merged[-500:]
    if started is None:
        db.add(attempt)
    db.flush()  # need attempt.id before XP / score recompute

    # ── Test mode → feed CIE (best-effort) ──
    if quiz.mode == QuizMode.TEST:
        try:
            _feed_cie_from_attempt(db, quiz, attempt, graded)
        except Exception as e:  # noqa: BLE001
            logger.warning("CIE feed failed for attempt %s: %s", attempt.id, e)

    # ── Phase 12 hooks ──
    # Award XP scaled by score + difficulty + streak
    try:
        xp.award_xp_for_quiz_attempt(db, user, attempt=attempt, quiz=quiz)
    except Exception as e:  # don't fail the whole submit if XP plumbing breaks
        logger.warning("XP award failed for attempt %s: %s", attempt.id, e)

    # Recompute the student's CampusIQ score (academic pillar)
    try:
        campus_iq_score.recompute_score(db, user)
    except Exception as e:
        logger.warning("CampusIQ score recompute failed: %s", e)

    db.commit()
    db.refresh(attempt)

    # Phase 9 — push a real-time notification to the student.
    try:
        from app.models.algorithm import NotificationType
        from app.services import notifications as notifications_service

        notifications_service.publish_sync(
            db,
            user_id=user.id,
            notification_type=NotificationType.QUIZ_RESULT,
            title=f"Quiz scored: {quiz.title}",
            content=f"You scored {score_percent:.0f}% ({correct_count}/{total} correct).",
            extra={
                "quiz_id": str(quiz.id),
                "attempt_id": str(attempt.id),
                "score_percent": score_percent,
            },
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("Quiz attempt notification failed: %s", e)

    # Weak-topic detection on this attempt only (the route can also call
    # compute_weak_areas() for the full historical view)
    topic_results: dict[str, list[bool]] = defaultdict(list)
    for g in graded:
        if g.topic:
            topic_results[g.topic].append(g.is_correct)
    weak_topics_now = [
        topic
        for topic, results in topic_results.items()
        if (sum(results) / len(results)) * 100 < WEAK_TOPIC_SCORE_THRESHOLD
    ]

    # Greedy next-difficulty hint
    next_diff = _next_difficulty_recommendation(
        db,
        student_id=user.id,
        subject_id=quiz.subject_id,
        current_difficulty=quiz.difficulty,
    )

    # Per-CO attainment for this attempt (marks-based).
    co_obt: dict[str, float] = defaultdict(float)
    co_pos: dict[str, float] = defaultdict(float)
    for g in graded:
        if g.co:
            co_obt[g.co] += float(g.marks_awarded)
            co_pos[g.co] += float(g.marks_possible)
    co_attainment = [
        COAttainmentRow(
            co=co, obtained=round(co_obt[co], 2), possible=round(co_pos[co], 2),
            pct=round((co_obt[co] / co_pos[co] * 100) if co_pos[co] else 0.0, 2),
        )
        for co in sorted(co_obt)
    ]

    return QuizAttemptResponse(
        id=attempt.id,
        quiz_id=quiz.id,
        student_id=user.id,
        score=score_percent,
        total_questions=total,
        correct_count=correct_count,
        time_taken_seconds=time_taken_seconds,
        completed_at=attempt.completed_at,
        graded_answers=graded,
        weak_topics=weak_topics_now,
        next_difficulty_recommendation=next_diff.value,
        mode=attempt.mode.value,
        marks_obtained=float(attempt.marks_obtained) if attempt.marks_obtained is not None else None,
        marks_possible=float(attempt.marks_possible) if attempt.marks_possible is not None else None,
        is_proctored=attempt.is_proctored,
        auto_submitted=attempt.auto_submitted,
        co_attainment=co_attainment,
    )


def _is_answer_correct(question: Question, student_answer: str) -> bool:
    if not student_answer:
        return False
    correct = (question.correct_answer or "").strip()
    if question.question_type == QuestionType.MCQ:
        return student_answer.strip().lower() == correct.lower()
    # short answer: case-insensitive substring match
    return correct.lower() in student_answer.strip().lower()


# ════════════════════════════════════════════════════════════════
# History + weak areas
# ════════════════════════════════════════════════════════════════

def list_attempts_for_student(
    db: Session,
    user: User,
    *,
    subject_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[AttemptHistoryRow]:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403, detail="Only students have an attempt history."
        )

    stmt = (
        select(QuizAttempt, Quiz, Subject)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Subject, Quiz.subject_id == Subject.id)
        .where(QuizAttempt.student_id == user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(limit)
    )
    if subject_id is not None:
        stmt = stmt.where(Quiz.subject_id == subject_id)

    rows = db.execute(stmt).all()
    return [
        AttemptHistoryRow(
            id=a.id,
            quiz_id=q.id,
            quiz_title=q.title,
            subject_code=s.code,
            subject_name=s.name,
            score=float(a.score),
            total_questions=a.total_questions,
            correct_count=a.correct_count,
            time_taken_seconds=a.time_taken_seconds,
            difficulty=q.difficulty.value,
            completed_at=a.completed_at,
        )
        for a, q, s in rows
    ]


def compute_weak_areas(db: Session, user: User) -> list[WeakAreaResponse]:
    """Boolean threshold detection (DMS Unit II).

    For each topic the student has answered questions on, compute their overall
    correctness percentage. A topic is "weak" iff:
        attempts ≥ WEAK_TOPIC_MIN_ATTEMPTS  AND
        score_percent < WEAK_TOPIC_SCORE_THRESHOLD
    """
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403, detail="Only students have weak-area diagnostics."
        )

    rows = db.execute(
        select(QuizAttempt, Quiz, Subject)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Subject, Quiz.subject_id == Subject.id)
        .where(QuizAttempt.student_id == user.id)
    ).all()

    # topic -> {correct, total, subject_code, subject_name}
    bucket: dict[str, dict] = defaultdict(
        lambda: {"correct": 0, "total": 0, "subject_code": None, "subject_name": None}
    )

    for attempt, _quiz, subject in rows:
        if not attempt.answers:
            continue
        for ans in attempt.answers:
            topic = (ans.get("topic") or "").strip()
            if not topic:
                continue
            b = bucket[topic]
            b["total"] += 1
            if ans.get("is_correct"):
                b["correct"] += 1
            # Last subject seen wins — fine for the dashboard view
            b["subject_code"] = subject.code
            b["subject_name"] = subject.name

    weak: list[WeakAreaResponse] = []
    for topic, b in bucket.items():
        if b["total"] < WEAK_TOPIC_MIN_ATTEMPTS:
            continue
        score = round((b["correct"] / b["total"]) * 100, 2)
        if score >= WEAK_TOPIC_SCORE_THRESHOLD:
            continue
        weak.append(
            WeakAreaResponse(
                topic=topic,
                subject_code=b["subject_code"],
                subject_name=b["subject_name"],
                score_percent=score,
                attempts_count=b["total"],
                suggestion=_weak_area_suggestion(topic, score),
            )
        )

    weak.sort(key=lambda w: w.score_percent)
    return weak


def _weak_area_suggestion(topic: str, score: float) -> str:
    if score < 35:
        return f"Re-read the {topic} section from your notes and retake an easier quiz on this topic."
    if score < 50:
        return f"Practice 5-10 more {topic} questions and review the explanations."
    return f"Skim {topic} once more and try a medium-difficulty quiz to confirm understanding."


def get_proctor_report(db: Session, quiz_id: uuid.UUID, user: User) -> ProctorReport:
    """Per-student proctoring + marks report for a quiz (teacher/admin)."""
    _require_teacher(user)
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    _validate_quiz_owner(quiz, user)
    rows = db.execute(
        select(QuizAttempt, User)
        .join(User, User.id == QuizAttempt.student_id)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.total_questions > 0)
        .order_by(QuizAttempt.completed_at.desc())
    ).all()
    return ProctorReport(
        quiz_id=quiz.id, quiz_title=quiz.title,
        rows=[
            ProctorReportRow(
                attempt_id=a.id, student_id=u.id, student_name=u.full_name,
                marks_obtained=float(a.marks_obtained) if a.marks_obtained is not None else None,
                marks_possible=float(a.marks_possible) if a.marks_possible is not None else None,
                score=float(a.score), tab_switch_count=a.tab_switch_count,
                fullscreen_exits=a.fullscreen_exits, copy_paste_attempts=a.copy_paste_attempts,
                face_absent_seconds=a.face_absent_seconds, face_multiple_seconds=a.face_multiple_seconds,
                auto_submitted=a.auto_submitted, violations=a.violations or [], completed_at=a.completed_at,
            )
            for a, u in rows
        ],
    )
