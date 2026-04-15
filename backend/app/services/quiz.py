"""Quiz CRUD, attempt scoring, adaptive difficulty, weak-area detection.

Phase 11 (F3) — DAA Unit IV (greedy adaptive difficulty), DMS Unit II
(boolean threshold detection of weak topics).
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.quiz import Difficulty, Question, QuestionType, Quiz, QuizAttempt
from app.models.user import Subject, User, UserRole
from app.services import campus_iq_score, xp
from app.schemas.quiz import (
    AttemptHistoryRow,
    GradedAnswer,
    QuestionAnswer,
    QuestionStudentView,
    QuestionTeacherView,
    QuizAttemptResponse,
    QuizForStudent,
    QuizForTeacher,
    QuizResponse,
    QuizUpdate,
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
    )


def _question_to_student_view(q: Question) -> QuestionStudentView:
    return QuestionStudentView(
        id=q.id,
        order_index=q.order_index,
        question_text=q.question_text,
        question_type=q.question_type.value,
        options=q.options,
        difficulty=q.difficulty.value,
        topic=q.topic,
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
        stmt = stmt.where(Quiz.is_published.is_(True))
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
    if user.role == UserRole.STUDENT and not quiz.is_published:
        raise HTTPException(status_code=404, detail="Quiz not found")

    subject = db.get(Subject, quiz.subject_id)
    stats = _quiz_aggregate_stats(db, [quiz.id])[quiz.id]

    base = _to_quiz_response(
        quiz,
        subject=subject,
        question_count=stats[0],
        attempt_count=stats[1],
        avg_score=stats[2],
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
                )
            )

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


def submit_attempt(
    db: Session,
    *,
    quiz_id: uuid.UUID,
    user: User,
    answers: list[QuestionAnswer],
    time_taken_seconds: int | None,
) -> QuizAttemptResponse:
    """Grade a student attempt, persist it, and return per-question feedback."""
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

    questions_by_id = {q.id: q for q in quiz.questions}
    if not questions_by_id:
        raise HTTPException(status_code=400, detail="Quiz has no questions")

    answers_by_qid: dict[uuid.UUID, str] = {}
    for a in answers:
        answers_by_qid[a.question_id] = a.student_answer

    graded: list[GradedAnswer] = []
    correct_count = 0

    # Iterate questions in their canonical order so the bit vector is stable
    for q in sorted(quiz.questions, key=lambda x: x.order_index):
        student_ans = (answers_by_qid.get(q.id) or "").strip()
        is_correct = _is_answer_correct(q, student_ans)
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
            )
        )

    total = len(quiz.questions)
    score_percent = round((correct_count / total) * 100, 2) if total else 0.0
    bit_vector = _build_answer_bit_vector(graded)

    # Persist the attempt
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=user.id,
        score=Decimal(str(score_percent)),
        total_questions=total,
        correct_count=correct_count,
        time_taken_seconds=time_taken_seconds,
        answers=[
            {
                "question_id": str(g.question_id),
                "student_answer": g.student_answer,
                "is_correct": g.is_correct,
                "topic": g.topic,
            }
            for g in graded
        ],
        answer_bit_vector=bit_vector,
    )
    db.add(attempt)
    db.flush()  # need attempt.id before XP / score recompute

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
