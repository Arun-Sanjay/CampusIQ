"""Roll per-question grades into a per-student ExamResult (the grade-engine seam).

Every grading path (AI auto-grader, test quizzes, manual entry) funnels through
``upsert_result`` so the grade engine has a single, uniform table to read.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.grading import (
    AnswerSheet,
    AnswerSheetStatus,
    Exam,
    ExamQuestion,
    ExamResult,
    QuestionGrade,
    ResultSource,
)
from app.services import grade_engine


def co_max_lookup(db: Session, exam: Exam) -> dict[str, float]:
    """Authoritative per-CO max marks: the exam's co_mark_grid if set, else summed
    from the scheme questions grouped by CO."""
    if exam.co_mark_grid:
        return {str(k): float(v) for k, v in exam.co_mark_grid.items()}
    out: dict[str, float] = {}
    qs = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)).all()
    for q in qs:
        if q.co:
            out[q.co] = out.get(q.co, 0.0) + float(q.max_marks or 0)
    return out


def build_per_co(db: Session, exam: Exam, grades: list[QuestionGrade]) -> dict:
    """Per-CO {obtained, max, pct} using effective (teacher-overridden) marks and
    the authoritative CO maxima."""
    per_question = [
        {"co": g.co, "obtained": g.effective_marks, "max": float(g.max_marks or 0)}
        for g in grades
    ]
    rows = grade_engine.compute_co_attainment(per_question)
    co_max = co_max_lookup(db, exam)
    per_co: dict[str, dict] = {}
    for row in rows:
        max_for_co = co_max.get(row.co, row.max) or row.max
        per_co[row.co] = {
            "obtained": row.obtained,
            "max": max_for_co,
            "pct": grade_engine.round2(grade_engine.safe_pct(row.obtained, max_for_co)),
        }
    return per_co


def upsert_result(db: Session, answer_sheet: AnswerSheet) -> ExamResult | None:
    """(Re)build the ExamResult + per_co for a graded, matched sheet."""
    if answer_sheet.student_id is None:
        return None
    exam = db.get(Exam, answer_sheet.exam_id)
    if exam is None:
        return None
    grades = db.scalars(
        select(QuestionGrade).where(QuestionGrade.answer_sheet_id == answer_sheet.id)
    ).all()
    per_co = build_per_co(db, exam, grades)
    total_obtained = sum(g.effective_marks for g in grades)
    total_max = float(exam.max_marks or 0) or sum(float(g.max_marks or 0) for g in grades)
    finalized = answer_sheet.status == AnswerSheetStatus.FINALIZED

    result = db.scalar(
        select(ExamResult).where(
            ExamResult.exam_id == exam.id,
            ExamResult.student_id == answer_sheet.student_id,
        )
    )
    if result is None:
        result = ExamResult(
            exam_id=exam.id, student_id=answer_sheet.student_id, source=ResultSource.AI
        )
        db.add(result)
    result.total_obtained = grade_engine.round2(total_obtained)
    result.total_max = grade_engine.round2(total_max)
    result.percentage = grade_engine.round2(grade_engine.safe_pct(total_obtained, total_max))
    result.per_co = per_co
    result.answer_sheet_id = answer_sheet.id
    result.source = ResultSource.AI
    result.is_teacher_approved = finalized
    result.finalized = finalized
    db.flush()
    return result


def upsert_manual_result(
    db: Session,
    exam: Exam,
    student_id: uuid.UUID,
    total_obtained: float,
    per_co: dict | None = None,
) -> ExamResult:
    """Teacher-entered marks for non-AI components (experiential, lab, SEE)."""
    total_max = float(exam.max_marks or 0)
    result = db.scalar(
        select(ExamResult).where(
            ExamResult.exam_id == exam.id, ExamResult.student_id == student_id
        )
    )
    if result is None:
        result = ExamResult(exam_id=exam.id, student_id=student_id)
        db.add(result)
    result.total_obtained = grade_engine.round2(total_obtained)
    result.total_max = grade_engine.round2(total_max)
    result.percentage = grade_engine.round2(grade_engine.safe_pct(total_obtained, total_max))
    result.per_co = per_co
    result.source = ResultSource.MANUAL
    result.is_teacher_approved = True
    result.finalized = True
    db.flush()
    return result


def class_attainment(db: Session, exam: Exam) -> dict:
    """Aggregate per-CO attainment across all of an exam's results (class view)."""
    results = db.scalars(select(ExamResult).where(ExamResult.exam_id == exam.id)).all()
    co_obtained: dict[str, float] = {}
    co_max: dict[str, float] = {}
    total_obtained = 0.0
    total_max = 0.0
    for r in results:
        total_obtained += float(r.total_obtained or 0)
        total_max += float(r.total_max or 0)
        for co, vals in (r.per_co or {}).items():
            co_obtained[co] = co_obtained.get(co, 0.0) + float(vals.get("obtained") or 0)
            co_max[co] = co_max.get(co, 0.0) + float(vals.get("max") or 0)
    per_co = [
        {
            "co": co,
            "obtained": grade_engine.round2(co_obtained[co]),
            "max": grade_engine.round2(co_max.get(co, 0.0)),
            "pct": grade_engine.round2(grade_engine.safe_pct(co_obtained[co], co_max.get(co, 0.0))),
        }
        for co in sorted(co_obtained)
    ]
    return {
        "exam_id": exam.id,
        "total_obtained": grade_engine.round2(total_obtained),
        "total_max": grade_engine.round2(total_max),
        "total_pct": grade_engine.round2(grade_engine.safe_pct(total_obtained, total_max)),
        "per_co": per_co,
        "graded_students": len(results),
    }
