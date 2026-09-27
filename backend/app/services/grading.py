"""Grading domain service: exams, scheme review, answer-sheet management, review
queue, overrides, finalize, CO attainment. Thin routes call into here.

The grade-engine orchestrator (assemble CIE/SEE → subject grade → SGPA/CGPA) lives
in the lower half of this module (added with the grades API).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.grading import (
    AnswerSheet,
    AnswerSheetStatus,
    CourseOutcome,
    Exam,
    ExamKind,
    ExamPart,
    ExamQuestion,
    ExamResult,
    Leniency,
    QuestionGrade,
    SchemeStatus,
    SemesterResult,
    SubjectGrade,
    SubjectGradeConfig,
)
from app.models.user import StudentProfile, Subject, SubjectEnrollment, User
from app.schemas.grading import (
    AnswerSheetDetail,
    AnswerSheetSummary,
    CourseOutcomeResponse,
    ExamResponse,
    GradeConfigResponse,
    QuestionGradeResponse,
    ReviewQueueItem,
    SchemeResponse,
)
from app.schemas.grades import (
    ClassGradeOverview,
    ClassGradeRow,
    SemesterGrades,
    SubjectGradeRow,
    TranscriptResponse,
)
from app.schemas.grading import COAttainmentRow
from app.services import answersheet_ingest, cover_marks, grade_engine, grading_results
from app.services.enrollment import _require_owned_subject, enrolled_student_ids_for_subject


# ── ownership helpers ────────────────────────────────────────────────────────
def _owned_exam(db: Session, teacher: User, exam_id: uuid.UUID) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    _require_owned_subject(db, teacher, exam.subject_id)
    return exam


def _owned_sheet(db: Session, teacher: User, sheet_id: uuid.UUID) -> tuple[AnswerSheet, Exam]:
    sheet = db.get(AnswerSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Answer sheet not found")
    exam = _owned_exam(db, teacher, sheet.exam_id)
    return sheet, exam


# ── response builders ────────────────────────────────────────────────────────
def to_exam_response(db: Session, exam: Exam) -> ExamResponse:
    qn = db.scalar(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)) or 0
    sheets = db.scalars(select(AnswerSheet).where(AnswerSheet.exam_id == exam.id)).all()
    graded = sum(1 for s in sheets if s.status in (AnswerSheetStatus.GRADED, AnswerSheetStatus.FINALIZED))
    review = sum(1 for s in sheets if s.status == AnswerSheetStatus.REVIEW)
    return ExamResponse(
        id=exam.id, subject_id=exam.subject_id, title=exam.title, kind=exam.kind.value,
        part=exam.part.value, component_key=exam.component_key, sequence=exam.sequence,
        max_marks=float(exam.max_marks or 0), co_mark_grid=exam.co_mark_grid,
        scheme_document_id=exam.scheme_document_id, scheme_status=exam.scheme_status.value,
        quiz_id=exam.quiz_id, leniency=exam.leniency.value, custom_rules=exam.custom_rules,
        ignore_spelling=exam.ignore_spelling, award_partial_method=exam.award_partial_method,
        confidence_review_threshold=float(exam.confidence_review_threshold),
        ocr_review_threshold=float(exam.ocr_review_threshold), is_published=exam.is_published,
        created_at=exam.created_at, question_count=qn, sheet_count=len(sheets),
        graded_count=graded, review_count=review,
    )


def _sheet_summary(db: Session, sheet: AnswerSheet) -> AnswerSheetSummary:
    name = usn = None
    if sheet.student_id:
        row = db.execute(
            select(User, StudentProfile)
            .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
            .where(User.id == sheet.student_id)
        ).first()
        if row:
            user, sp = row
            name = user.full_name
            usn = sp.usn if sp else None
    return AnswerSheetSummary(
        id=sheet.id, exam_id=sheet.exam_id, student_id=sheet.student_id, status=sheet.status.value,
        page_count=len(sheet.page_files or []), detected_usn=sheet.detected_usn,
        detected_name=sheet.detected_name,
        match_confidence=float(sheet.match_confidence) if sheet.match_confidence is not None else None,
        match_source=sheet.match_source, is_match_confirmed=sheet.is_match_confirmed,
        total_awarded=float(sheet.total_awarded) if sheet.total_awarded is not None else None,
        total_max=float(sheet.total_max) if sheet.total_max is not None else None,
        needs_review_count=sheet.needs_review_count, error_detail=sheet.error_detail,
        matched_student_name=name, matched_student_usn=usn,
    )


# ── exam CRUD ────────────────────────────────────────────────────────────────
def create_exam(db: Session, teacher: User, data) -> ExamResponse:
    _require_owned_subject(db, teacher, data.subject_id)
    exam = Exam(
        subject_id=data.subject_id, created_by_id=teacher.id, title=data.title,
        kind=ExamKind(data.kind), part=ExamPart(data.part), component_key=data.component_key,
        sequence=data.sequence, max_marks=data.max_marks,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return to_exam_response(db, exam)


def list_exams(db: Session, teacher: User, subject_id: uuid.UUID | None) -> list[ExamResponse]:
    stmt = select(Exam)
    if subject_id is not None:
        _require_owned_subject(db, teacher, subject_id)
        stmt = stmt.where(Exam.subject_id == subject_id)
    else:
        stmt = stmt.where(Exam.created_by_id == teacher.id)
    stmt = stmt.order_by(Exam.created_at.desc())
    return [to_exam_response(db, e) for e in db.scalars(stmt).all()]


def update_exam(db: Session, teacher: User, exam_id: uuid.UUID, data) -> ExamResponse:
    exam = _owned_exam(db, teacher, exam_id)
    payload = data.model_dump(exclude_unset=True)
    if "leniency" in payload and payload["leniency"] is not None:
        exam.leniency = Leniency(payload.pop("leniency"))
    for k, v in payload.items():
        setattr(exam, k, v)
    db.commit()
    db.refresh(exam)
    return to_exam_response(db, exam)


def delete_exam(db: Session, teacher: User, exam_id: uuid.UUID) -> None:
    exam = _owned_exam(db, teacher, exam_id)
    db.delete(exam)
    db.commit()


def set_scheme_document(db: Session, teacher: User, exam_id: uuid.UUID, document_id: uuid.UUID) -> Exam:
    exam = _owned_exam(db, teacher, exam_id)
    exam.scheme_document_id = document_id
    exam.scheme_status = SchemeStatus.PENDING
    db.commit()
    db.refresh(exam)
    return exam


# ── scheme review ────────────────────────────────────────────────────────────
def get_scheme(db: Session, teacher: User, exam_id: uuid.UUID) -> SchemeResponse:
    exam = _owned_exam(db, teacher, exam_id)
    questions = db.scalars(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.order_index)
    ).all()
    cos = db.scalars(
        select(CourseOutcome).where(CourseOutcome.subject_id == exam.subject_id).order_by(CourseOutcome.order_index)
    ).all()
    return SchemeResponse(
        exam=to_exam_response(db, exam),
        questions=[ExamQuestionResponse_from(q) for q in questions],
        course_outcomes=[CourseOutcomeResponse.model_validate(c) for c in cos],
        co_mark_grid=exam.co_mark_grid,
    )


def update_question(db: Session, teacher: User, exam_id: uuid.UUID, question_id: uuid.UUID, data):
    exam = _owned_exam(db, teacher, exam_id)
    q = db.get(ExamQuestion, question_id)
    if q is None or q.exam_id != exam.id:
        raise HTTPException(status_code=404, detail="Question not found")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("part"):
        q.part = ExamPart(payload.pop("part"))
    for k, v in payload.items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return ExamQuestionResponse_from(q)


def create_question(db: Session, teacher: User, exam_id: uuid.UUID, data):
    exam = _owned_exam(db, teacher, exam_id)
    q = ExamQuestion(
        exam_id=exam.id, order_index=data.order_index, part=ExamPart(data.part),
        label=data.label, parent_label=data.parent_label, question_text=data.question_text,
        model_answer=data.model_answer, max_marks=data.max_marks, co=data.co, bloom=data.bloom,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return ExamQuestionResponse_from(q)


def delete_question(db: Session, teacher: User, exam_id: uuid.UUID, question_id: uuid.UUID) -> None:
    exam = _owned_exam(db, teacher, exam_id)
    q = db.get(ExamQuestion, question_id)
    if q is None or q.exam_id != exam.id:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()


def confirm_scheme(db: Session, teacher: User, exam_id: uuid.UUID) -> ExamResponse:
    exam = _owned_exam(db, teacher, exam_id)
    qn = db.scalar(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)) or 0
    if qn == 0:
        raise HTTPException(status_code=400, detail="Add at least one question before confirming the scheme.")
    # Refresh max_marks from the sum if it's unset.
    if not exam.max_marks:
        total = db.scalar(select(func.sum(ExamQuestion.max_marks)).where(ExamQuestion.exam_id == exam.id)) or 0
        exam.max_marks = float(total)
    exam.scheme_status = SchemeStatus.READY
    db.commit()
    db.refresh(exam)
    return to_exam_response(db, exam)


# ── grade config + course outcomes ───────────────────────────────────────────
def get_config(db: Session, teacher: User, subject_id: uuid.UUID) -> GradeConfigResponse:
    _require_owned_subject(db, teacher, subject_id)
    cfg = db.scalar(select(SubjectGradeConfig).where(SubjectGradeConfig.subject_id == subject_id))
    if cfg is None:
        return GradeConfigResponse(subject_id=subject_id, components=[], cie_min_pct=40, see_min_pct=35,
                                   aggregate_min_pct=40, gate_lab_separately=False)
    return GradeConfigResponse.model_validate(cfg)


def update_config(db: Session, teacher: User, subject_id: uuid.UUID, data) -> GradeConfigResponse:
    _require_owned_subject(db, teacher, subject_id)
    cfg = db.scalar(select(SubjectGradeConfig).where(SubjectGradeConfig.subject_id == subject_id))
    if cfg is None:
        cfg = SubjectGradeConfig(subject_id=subject_id)
        db.add(cfg)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("components") is not None:
        cfg.components = [c if isinstance(c, dict) else c.model_dump() for c in data.components]
        payload.pop("components")
    for k, v in payload.items():
        setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return GradeConfigResponse.model_validate(cfg)


def list_course_outcomes(db: Session, teacher: User, subject_id: uuid.UUID) -> list[CourseOutcomeResponse]:
    _require_owned_subject(db, teacher, subject_id)
    cos = db.scalars(
        select(CourseOutcome).where(CourseOutcome.subject_id == subject_id).order_by(CourseOutcome.order_index)
    ).all()
    return [CourseOutcomeResponse.model_validate(c) for c in cos]


def create_course_outcome(db: Session, teacher: User, subject_id: uuid.UUID, data) -> CourseOutcomeResponse:
    _require_owned_subject(db, teacher, subject_id)
    existing = db.scalar(
        select(CourseOutcome).where(CourseOutcome.subject_id == subject_id, CourseOutcome.code == data.code)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"{data.code} already exists for this subject")
    co = CourseOutcome(subject_id=subject_id, code=data.code, description=data.description,
                       order_index=data.order_index)
    db.add(co)
    db.commit()
    db.refresh(co)
    return CourseOutcomeResponse.model_validate(co)


# ── answer sheets ────────────────────────────────────────────────────────────
def list_sheets(db: Session, teacher: User, exam_id: uuid.UUID) -> list[AnswerSheetSummary]:
    _owned_exam(db, teacher, exam_id)
    sheets = db.scalars(
        select(AnswerSheet).where(AnswerSheet.exam_id == exam_id).order_by(AnswerSheet.created_at)
    ).all()
    return [_sheet_summary(db, s) for s in sheets]


def get_sheet_detail(db: Session, teacher: User, sheet_id: uuid.UUID) -> AnswerSheetDetail:
    sheet, exam = _owned_sheet(db, teacher, sheet_id)
    rows = db.execute(
        select(QuestionGrade, ExamQuestion)
        .join(ExamQuestion, ExamQuestion.id == QuestionGrade.exam_question_id)
        .where(QuestionGrade.answer_sheet_id == sheet.id)
        .order_by(ExamQuestion.order_index)
    ).all()
    grades = [_grade_response(g, q) for g, q in rows]
    summary = _sheet_summary(db, sheet)
    return AnswerSheetDetail(**summary.model_dump(), page_files=sheet.page_files or [], grades=grades)


def set_match(db: Session, teacher: User, sheet_id: uuid.UUID, student_id: uuid.UUID | None) -> AnswerSheetSummary:
    sheet, exam = _owned_sheet(db, teacher, sheet_id)
    if student_id is not None:
        enrolled = db.scalar(
            select(SubjectEnrollment).where(
                SubjectEnrollment.subject_id == exam.subject_id,
                SubjectEnrollment.student_id == student_id,
            )
        )
        if enrolled is None:
            raise HTTPException(status_code=400, detail="That student is not enrolled in this subject.")
        dupe = db.scalar(
            select(AnswerSheet).where(
                AnswerSheet.exam_id == exam.id,
                AnswerSheet.student_id == student_id,
                AnswerSheet.id != sheet.id,
            )
        )
        if dupe is not None:
            raise HTTPException(status_code=409, detail="Another sheet is already mapped to that student.")
    sheet.student_id = student_id
    sheet.is_match_confirmed = student_id is not None
    sheet.match_source = "manual" if student_id else "unmatched"
    sheet.match_confidence = 1.0 if student_id else 0.0
    # Re-roll the result so the marks attach to the right student.
    if student_id is not None and sheet.status in (AnswerSheetStatus.GRADED, AnswerSheetStatus.REVIEW, AnswerSheetStatus.FINALIZED):
        grading_results.upsert_result(db, sheet)
    db.commit()
    return _sheet_summary(db, sheet)


def review_queue(db: Session, teacher: User, exam_id: uuid.UUID) -> list[ReviewQueueItem]:
    _owned_exam(db, teacher, exam_id)
    rows = db.execute(
        select(QuestionGrade, ExamQuestion, AnswerSheet)
        .join(ExamQuestion, ExamQuestion.id == QuestionGrade.exam_question_id)
        .join(AnswerSheet, AnswerSheet.id == QuestionGrade.answer_sheet_id)
        .where(AnswerSheet.exam_id == exam_id, QuestionGrade.needs_review.is_(True))
        .order_by(AnswerSheet.id)
    ).all()
    out: list[ReviewQueueItem] = []
    for g, q, sheet in rows:
        name = None
        if sheet.student_id:
            u = db.get(User, sheet.student_id)
            name = u.full_name if u else None
        out.append(ReviewQueueItem(
            answer_sheet_id=sheet.id, question_grade_id=g.id, student_name=name, label=q.label,
            extracted_answer=g.extracted_answer, awarded_marks=float(g.awarded_marks),
            max_marks=float(g.max_marks), confidence=float(g.confidence) if g.confidence is not None else None,
            rationale=g.rationale,
        ))
    return out


def override_grade(db: Session, teacher: User, question_grade_id: uuid.UUID, data) -> QuestionGradeResponse:
    g = db.get(QuestionGrade, question_grade_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Grade not found")
    sheet, exam = _owned_sheet(db, teacher, g.answer_sheet_id)
    if data.teacher_marks > float(g.max_marks):
        raise HTTPException(status_code=400, detail=f"Marks cannot exceed {float(g.max_marks)}.")
    g.is_overridden = True
    g.teacher_marks = data.teacher_marks
    g.teacher_note = data.teacher_note
    g.needs_review = False
    g.reviewed_by_id = teacher.id
    g.reviewed_at = datetime.now(timezone.utc)
    db.flush()
    _recompute_sheet_rollup(db, sheet)
    grading_results.upsert_result(db, sheet)
    recompute_subject_grade(db, exam.subject_id, sheet.student_id)
    db.commit()
    q = db.get(ExamQuestion, g.exam_question_id)
    return _grade_response(g, q)


def finalize_sheet(db: Session, teacher: User, sheet_id: uuid.UUID, *, force: bool = False) -> AnswerSheetSummary:
    sheet, exam = _owned_sheet(db, teacher, sheet_id)
    if sheet.student_id is None:
        raise HTTPException(status_code=400, detail="Map this sheet to a student before finalizing.")
    if sheet.needs_review_count > 0 and not force:
        raise HTTPException(status_code=400, detail="Resolve the review queue first (or finalize with force).")
    sheet.status = AnswerSheetStatus.FINALIZED
    sheet.finalized_at = datetime.now(timezone.utc)
    grading_results.upsert_result(db, sheet)
    recompute_subject_grade(db, exam.subject_id, sheet.student_id)
    db.commit()
    return _sheet_summary(db, sheet)


def finalize_all(db: Session, teacher: User, exam_id: uuid.UUID) -> int:
    _owned_exam(db, teacher, exam_id)
    sheets = db.scalars(
        select(AnswerSheet).where(
            AnswerSheet.exam_id == exam_id,
            AnswerSheet.status == AnswerSheetStatus.GRADED,
        )
    ).all()
    count = 0
    exam = db.get(Exam, exam_id)
    for s in sheets:
        if s.student_id is not None and s.needs_review_count == 0:
            s.status = AnswerSheetStatus.FINALIZED
            s.finalized_at = datetime.now(timezone.utc)
            grading_results.upsert_result(db, s)
            if exam is not None:
                recompute_subject_grade(db, exam.subject_id, s.student_id)
            count += 1
    db.commit()
    return count


def exam_attainment(db: Session, teacher: User, exam_id: uuid.UUID) -> dict:
    exam = _owned_exam(db, teacher, exam_id)
    return grading_results.class_attainment(db, exam)


def _recompute_sheet_rollup(db: Session, sheet: AnswerSheet) -> None:
    grades = db.scalars(select(QuestionGrade).where(QuestionGrade.answer_sheet_id == sheet.id)).all()
    sheet.total_awarded = sum(g.effective_marks for g in grades)
    sheet.total_max = sum(float(g.max_marks or 0) for g in grades)
    sheet.needs_review_count = sum(1 for g in grades if g.needs_review)
    if sheet.needs_review_count == 0 and sheet.status == AnswerSheetStatus.REVIEW:
        sheet.status = AnswerSheetStatus.GRADED


# ── small response helpers ───────────────────────────────────────────────────
def ExamQuestionResponse_from(q: ExamQuestion):
    from app.schemas.grading import ExamQuestionResponse
    return ExamQuestionResponse(
        id=q.id, label=q.label, parent_label=q.parent_label, part=q.part.value,
        question_text=q.question_text, model_answer=q.model_answer, max_marks=float(q.max_marks or 0),
        co=q.co, bloom=q.bloom, order_index=q.order_index,
    )


def _grade_response(g: QuestionGrade, q: ExamQuestion | None) -> QuestionGradeResponse:
    return QuestionGradeResponse(
        id=g.id, exam_question_id=g.exam_question_id, label=q.label if q else None,
        question_text=q.question_text if q else None, model_answer=q.model_answer if q else None,
        extracted_answer=g.extracted_answer, awarded_marks=float(g.awarded_marks),
        max_marks=float(g.max_marks), effective_marks=g.effective_marks, co=g.co,
        confidence=float(g.confidence) if g.confidence is not None else None,
        ocr_confidence=float(g.ocr_confidence) if g.ocr_confidence is not None else None,
        rationale=g.rationale, needs_review=g.needs_review, is_overridden=g.is_overridden,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Grade-engine orchestrator (Phase 3): finalized ExamResults → SubjectGrade →
# SemesterResult → CGPA. Reads only finalized results (the gradebook).
# ══════════════════════════════════════════════════════════════════════════════
def _scale(pairs: list[tuple[Exam, ExamResult]], target_max: float) -> float:
    """Proportional scale of a group's raw obtained/max onto target_max."""
    raw_o = sum(float(r.total_obtained) for _, r in pairs)
    raw_m = sum(float(r.total_max) for _, r in pairs)
    if raw_m <= 0:
        return 0.0
    return grade_engine.round2(raw_o / raw_m * float(target_max))


def recompute_subject_grade(db: Session, subject_id: uuid.UUID, student_id: uuid.UUID) -> SubjectGrade | None:
    """Reassemble a student's CIE/SEE from finalized ExamResults and recompute the
    subject grade, then cascade to SGPA + CGPA."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        return None
    cfg = db.scalar(select(SubjectGradeConfig).where(SubjectGradeConfig.subject_id == subject_id))
    rows = db.execute(
        select(Exam, ExamResult)
        .join(ExamResult, ExamResult.exam_id == Exam.id)
        .where(Exam.subject_id == subject_id, ExamResult.student_id == student_id, ExamResult.finalized.is_(True))
    ).all()
    cie_pairs = [(e, r) for e, r in rows if e.kind != ExamKind.SEE]
    see_pairs = [(e, r) for e, r in rows if e.kind == ExamKind.SEE]
    has_lab = subject.has_lab_split
    components = cfg.components if (cfg and cfg.components) else None

    # ── CIE ──
    if components:
        by_key: dict[str, list] = {}
        for e, r in cie_pairs:
            by_key.setdefault(e.component_key or "", []).append((e, r))
        cie_theory = cie_lab = 0.0
        for comp in components:
            grp = by_key.get(comp.get("key", ""), [])
            obt = [float(r.total_obtained) for _, r in grp]
            mx = [float(r.total_max) for _, r in grp]
            val = grade_engine.reduce_best_of(obt, mx, float(comp.get("max", 0))) if mx else 0.0
            if comp.get("part") == "lab":
                cie_lab += val
            else:
                cie_theory += val
        cie_theory = grade_engine.round2(cie_theory)
        cie_lab = grade_engine.round2(cie_lab)
        cie_obtained = grade_engine.round2(cie_theory + cie_lab)
    elif has_lab:
        cie_theory = _scale([(e, r) for e, r in cie_pairs if e.part == ExamPart.THEORY], subject.cie_theory_max or subject.cie_max)
        cie_lab = _scale([(e, r) for e, r in cie_pairs if e.part == ExamPart.LAB], subject.cie_lab_max or 0)
        cie_obtained = grade_engine.round2(cie_theory + cie_lab)
    else:
        cie_theory = _scale(cie_pairs, subject.cie_max)
        cie_lab = 0.0
        cie_obtained = cie_theory

    # ── SEE ──
    if not see_pairs:
        see_obtained = see_theory = see_lab = None
    elif has_lab:
        see_theory = _scale([(e, r) for e, r in see_pairs if e.part == ExamPart.THEORY], subject.see_theory_max or subject.see_max)
        see_lab = _scale([(e, r) for e, r in see_pairs if e.part == ExamPart.LAB], subject.see_lab_max or 0)
        see_obtained = grade_engine.round2((see_theory or 0) + (see_lab or 0))
    else:
        see_theory = _scale(see_pairs, subject.see_max)
        see_lab = None
        see_obtained = see_theory

    # ── gates config ──
    cie_min = float(cfg.cie_min_pct) if cfg else grade_engine.DEFAULT_CIE_MIN_PCT
    see_min = float(cfg.see_min_pct) if cfg else grade_engine.DEFAULT_SEE_MIN_PCT
    agg_min = float(cfg.aggregate_min_pct) if cfg else grade_engine.DEFAULT_AGGREGATE_MIN_PCT
    cie_lab_min = float(cfg.cie_lab_min_pct) if (cfg and cfg.cie_lab_min_pct is not None) else cie_min
    see_lab_min = float(cfg.see_lab_min_pct) if (cfg and cfg.see_lab_min_pct is not None) else see_min

    grade = db.scalar(
        select(SubjectGrade).where(SubjectGrade.subject_id == subject_id, SubjectGrade.student_id == student_id)
    )
    if grade is None:
        grade = SubjectGrade(subject_id=subject_id, student_id=student_id)
        db.add(grade)

    grade.cie_obtained = cie_obtained
    grade.cie_max = subject.cie_max
    grade.see_obtained = see_obtained
    grade.see_max = subject.see_max if see_pairs else None
    grade.cie_theory_obtained = cie_theory if has_lab else None
    grade.cie_lab_obtained = cie_lab if has_lab else None
    grade.see_theory_obtained = see_theory if has_lab else None
    grade.see_lab_obtained = see_lab if has_lab else None
    grade.credits_snapshot = subject.credits
    grade.semester = subject.semester

    if not grade.is_transitional and see_pairs:
        comp = grade_engine.compute_subject_grade(
            cie_obtained, subject.cie_max, see_obtained, subject.see_max,
            cie_min=cie_min, see_min=see_min, agg_min=agg_min, split=has_lab,
            cie_theory_obtained=cie_theory, cie_theory_max=subject.cie_theory_max,
            cie_lab_obtained=cie_lab, cie_lab_max=subject.cie_lab_max,
            see_theory_obtained=see_theory, see_theory_max=subject.see_theory_max,
            see_lab_obtained=see_lab, see_lab_max=subject.see_lab_max,
            cie_lab_min=cie_lab_min, see_lab_min=see_lab_min,
        )
        grade.cie_50, grade.see_50 = comp.cie_50, comp.see_50
        grade.final_score, grade.final_rounded = comp.final_score, comp.final_rounded
        grade.letter_grade = comp.letter
        grade.grade_point = comp.grade_point
        grade.passed = comp.passed
        grade.gate_failed = comp.gate_failed
        grade.finalized = True
    else:
        # SEE not entered yet (or transitional) → provisional, excluded from SGPA.
        grade.cie_50 = grade_engine.round2(grade_engine.safe_pct(cie_obtained, subject.cie_max) / 100 * 50)
        grade.see_50 = None
        grade.final_score = grade.final_rounded = None
        if not grade.is_transitional:
            grade.letter_grade = None
            grade.grade_point = None
            grade.passed = False
            grade.finalized = False

    db.flush()
    if subject.semester is not None:
        recompute_semester(db, student_id, subject.semester)
    else:
        recompute_cgpa(db, student_id)
    return grade


def _gradable_entries(grades: list[SubjectGrade]) -> list[tuple[int, int]]:
    return [
        (g.credits_snapshot or 0, g.grade_point or 0)
        for g in grades
        if g.grade_point is not None and not g.is_transitional and (g.credits_snapshot or 0) > 0
    ]


def recompute_semester(db: Session, student_id: uuid.UUID, semester: int) -> None:
    grades = db.scalars(
        select(SubjectGrade).where(SubjectGrade.student_id == student_id, SubjectGrade.semester == semester)
    ).all()
    res = grade_engine.compute_sgpa(_gradable_entries(grades))
    row = db.scalar(
        select(SemesterResult).where(SemesterResult.student_id == student_id, SemesterResult.semester == semester)
    )
    if row is None:
        row = SemesterResult(student_id=student_id, semester=semester)
        db.add(row)
    row.sgpa = res.sgpa
    row.total_credits = res.total_credits
    row.total_grade_points = res.total_grade_points
    db.flush()
    recompute_cgpa(db, student_id)


def recompute_cgpa(db: Session, student_id: uuid.UUID) -> float:
    grades = db.scalars(select(SubjectGrade).where(SubjectGrade.student_id == student_id)).all()
    cgpa = grade_engine.compute_cgpa(_gradable_entries(grades))
    sp = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    if sp is not None:
        sp.cgpa = cgpa
    db.flush()
    return cgpa


def recompute_all_for_subject(db: Session, subject_id: uuid.UUID) -> int:
    """Recompute every enrolled student's grade for a subject (after a config change)."""
    student_ids = db.scalars(
        select(SubjectEnrollment.student_id).where(SubjectEnrollment.subject_id == subject_id)
    ).all()
    for sid in student_ids:
        recompute_subject_grade(db, subject_id, sid)
    db.commit()
    return len(student_ids)


# ── manual mark entry (experiential / lab / SEE components) ──
def enter_manual_results(db: Session, teacher: User, exam_id: uuid.UUID, entries: list) -> int:
    exam = _owned_exam(db, teacher, exam_id)
    count = 0
    for entry in entries:
        grading_results.upsert_manual_result(db, exam, entry.student_id, entry.total_obtained, entry.per_co)
        recompute_subject_grade(db, exam.subject_id, entry.student_id)
        count += 1
    db.commit()
    return count


# ── Auto Marks Assigner: scan an answer-booklet cover page → record the marks ──
def scan_and_record_cover(db: Session, teacher: User, exam_id: uuid.UUID, files: list) -> list[dict]:
    """For each uploaded booklet, Claude-vision the COVER (first) page's marks
    tally and — when a roster student matches — write the result straight into
    the grade engine. Unmatched scans come back for the teacher to assign."""
    exam = _owned_exam(db, teacher, exam_id)
    out: list[dict] = []
    for f in files:
        try:
            pages = answersheet_ingest._file_to_pages(f)
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            pages = []
        if not pages:
            out.append({
                "saved": False, "message": "Could not read the file.",
                "total_obtained": 0, "total_max": float(exam.max_marks or 0),
            })
            continue

        scan = cover_marks.scan_cover(db, exam, pages[0])  # cover = first page
        saved = False
        matched_name = None
        if scan["student_id"] is not None:
            grading_results.upsert_manual_result(
                db, exam, scan["student_id"], scan["total_obtained"], scan["per_co"]
            )
            recompute_subject_grade(db, exam.subject_id, scan["student_id"])
            saved = True
            u = db.get(User, scan["student_id"])
            matched_name = u.full_name if u else None

        out.append({
            "detected_usn": scan["detected_usn"],
            "detected_name": scan["detected_name"],
            "student_id": scan["student_id"],
            "matched_student_name": matched_name,
            "match_confidence": scan["match_confidence"],
            "total_obtained": scan["total_obtained"],
            "total_max": scan["total_max"],
            "per_co": scan["per_co"],
            "saved": saved,
            "message": None if saved else "No roster match — pick a student to save.",
        })
    db.commit()
    return out


# ── grades read API (student transcript + teacher class overview) ──
def _subject_per_co(db: Session, subject_id: uuid.UUID, student_id: uuid.UUID) -> list[COAttainmentRow]:
    rows = db.execute(
        select(ExamResult)
        .join(Exam, Exam.id == ExamResult.exam_id)
        .where(Exam.subject_id == subject_id, ExamResult.student_id == student_id, ExamResult.finalized.is_(True))
    ).scalars().all()
    obt: dict[str, float] = {}
    mx: dict[str, float] = {}
    for r in rows:
        for co, v in (r.per_co or {}).items():
            obt[co] = obt.get(co, 0.0) + float(v.get("obtained") or 0)
            mx[co] = mx.get(co, 0.0) + float(v.get("max") or 0)
    return [
        COAttainmentRow(co=co, obtained=grade_engine.round2(obt[co]), max=grade_engine.round2(mx.get(co, 0.0)),
                        pct=grade_engine.round2(grade_engine.safe_pct(obt[co], mx.get(co, 0.0))))
        for co in sorted(obt)
    ]


def _grade_row(db: Session, g: SubjectGrade, subj: Subject, student_id: uuid.UUID) -> SubjectGradeRow:
    f = lambda x: float(x) if x is not None else None  # noqa: E731
    return SubjectGradeRow(
        subject_id=subj.id, subject_code=subj.code, subject_name=subj.name,
        credits=g.credits_snapshot or subj.credits, semester=g.semester,
        cie_obtained=f(g.cie_obtained), cie_max=f(g.cie_max), see_obtained=f(g.see_obtained), see_max=f(g.see_max),
        cie_50=f(g.cie_50), see_50=f(g.see_50), final_score=f(g.final_score), final_rounded=g.final_rounded,
        letter_grade=g.letter_grade.value if g.letter_grade else None, grade_point=g.grade_point,
        passed=g.passed, gate_failed=g.gate_failed.value, is_transitional=g.is_transitional,
        finalized=g.finalized, per_co=_subject_per_co(db, subj.id, student_id),
    )


def student_transcript(db: Session, student_id: uuid.UUID) -> TranscriptResponse:
    grades = db.scalars(select(SubjectGrade).where(SubjectGrade.student_id == student_id)).all()
    by_sem: dict[int, list[SubjectGradeRow]] = {}
    for g in grades:
        subj = db.get(Subject, g.subject_id)
        if subj is None:
            continue
        by_sem.setdefault(g.semester or 0, []).append(_grade_row(db, g, subj, student_id))
    semesters: list[SemesterGrades] = []
    for sem in sorted(by_sem):
        sr = db.scalar(select(SemesterResult).where(SemesterResult.student_id == student_id, SemesterResult.semester == sem))
        semesters.append(SemesterGrades(
            semester=sem, sgpa=float(sr.sgpa) if sr else 0.0,
            total_credits=sr.total_credits if sr else 0, subjects=by_sem[sem],
        ))
    sp = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    cgpa = float(sp.cgpa) if sp and sp.cgpa is not None else 0.0
    return TranscriptResponse(cgpa=cgpa, percentage=grade_engine.round2(cgpa * 10), semesters=semesters)


def class_grade_overview(db: Session, teacher: User, subject_id: uuid.UUID) -> ClassGradeOverview:
    subject = _require_owned_subject(db, teacher, subject_id)
    student_ids = enrolled_student_ids_for_subject(db, subject_id)
    rows: list[ClassGradeRow] = []
    for sid in student_ids:
        u = db.get(User, sid)
        if u is None:
            continue
        sp = db.scalar(select(StudentProfile).where(StudentProfile.user_id == sid))
        g = db.scalar(select(SubjectGrade).where(SubjectGrade.subject_id == subject_id, SubjectGrade.student_id == sid))
        rows.append(ClassGradeRow(
            student_id=sid, student_name=u.full_name, usn=sp.usn if sp else None,
            cie_obtained=float(g.cie_obtained) if g and g.cie_obtained is not None else None,
            cie_max=float(g.cie_max) if g and g.cie_max is not None else None,
            see_obtained=float(g.see_obtained) if g and g.see_obtained is not None else None,
            final_score=float(g.final_score) if g and g.final_score is not None else None,
            letter_grade=g.letter_grade.value if g and g.letter_grade else None,
            grade_point=g.grade_point if g else None,
            passed=g.passed if g else False, finalized=g.finalized if g else False,
        ))
    # Class CO attainment across all finalized results for the subject's exams.
    res = db.execute(
        select(ExamResult).join(Exam, Exam.id == ExamResult.exam_id)
        .where(Exam.subject_id == subject_id, ExamResult.finalized.is_(True))
    ).scalars().all()
    obt: dict[str, float] = {}
    mx: dict[str, float] = {}
    for r in res:
        for co, v in (r.per_co or {}).items():
            obt[co] = obt.get(co, 0.0) + float(v.get("obtained") or 0)
            mx[co] = mx.get(co, 0.0) + float(v.get("max") or 0)
    co_rows = [
        COAttainmentRow(co=co, obtained=grade_engine.round2(obt[co]), max=grade_engine.round2(mx.get(co, 0.0)),
                        pct=grade_engine.round2(grade_engine.safe_pct(obt[co], mx.get(co, 0.0))))
        for co in sorted(obt)
    ]
    return ClassGradeOverview(
        subject_id=subject.id, subject_code=subject.code, subject_name=subject.name,
        students=rows, co_attainment=co_rows,
    )
