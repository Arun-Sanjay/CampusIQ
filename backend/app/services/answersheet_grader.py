"""The flagship: OCR + grade a student's handwritten answer sheet with Claude vision.

One fused vision call per student (OCR + grade + USN/name detection) keeps cost to
~1 Claude call/student. Runs as a BackgroundTask with its own session, serialized
per-exam so a batch upload doesn't fan out N parallel Claude calls.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.models.grading import (
    AnswerSheet,
    AnswerSheetStatus,
    Exam,
    ExamQuestion,
    QuestionGrade,
    SchemeStatus,
)
from app.services import answersheet_match, claude_client, grading_results

logger = logging.getLogger(__name__)

# Serialize grading per exam so a batch upload runs one Claude call at a time
# (cost guardrail — no Celery, BackgroundTasks only).
_exam_locks: dict[uuid.UUID, threading.Lock] = {}
_exam_locks_guard = threading.Lock()


def _lock_for(exam_id: uuid.UUID) -> threading.Lock:
    with _exam_locks_guard:
        lk = _exam_locks.get(exam_id)
        if lk is None:
            lk = _exam_locks[exam_id] = threading.Lock()
        return lk


GRADING_SYSTEM = """You are an expert, fair exam grader for an Indian engineering college.
You receive: (1) a marking scheme (questions with model answers, max marks, and CO tags)
and (2) photographed pages of ONE student's handwritten answer script.

Do two things:
1. Transcribe the student's handwriting for each question (verbatim, best effort).
2. Award marks for each scheme question by comparing the student's answer to the model
   answer, following the leniency level and any custom rules provided.

Return STRICT JSON only (no prose, no markdown fences):
{
  "detected_usn": "string or null",
  "detected_name": "string or null",
  "answers": [
    {"label": "1a", "extracted_answer": "...", "awarded_marks": 3, "max_marks": 5,
     "co": "CO3", "ocr_confidence": 0.0-1.0, "confidence": 0.0-1.0,
     "rationale": "one short line", "needs_review": false}
  ]
}
Rules: output EXACTLY one entry per scheme question (use its label). Never award more
than max_marks. If a question is unanswered, award 0. If handwriting is illegible or you
are unsure, set low confidence/ocr_confidence and needs_review true. detected_usn is the
University Seat Number from the header (e.g. 1RV23CS001) if visible.
If a model answer is brief, missing, or holistic (the scheme may be light notes rather
than a full key), grade against the question's intent, the reference material provided,
and your own subject expertise — award marks for correct, relevant content."""

_LENIENCY_TEXT = {
    "strict": "Be strict: award marks only for content that closely matches the model answer.",
    "moderate": "Be balanced: reward correct concepts; minor omissions lose partial marks.",
    "lenient": "Be generous: award marks for correct approach/method even if incomplete or the final answer differs.",
}


def _strip_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start : end + 1]
    return t


def _build_prompt(exam: Exam, questions: list[ExamQuestion]) -> str:
    scheme = [
        {
            "label": q.label,
            "question": q.question_text,
            "model_answer": q.model_answer or "",
            "max_marks": float(q.max_marks or 0),
            "co": q.co,
        }
        for q in questions
    ]
    rules = _LENIENCY_TEXT.get(exam.leniency.value, _LENIENCY_TEXT["moderate"])
    extra = []
    if exam.ignore_spelling:
        extra.append("Ignore spelling and grammar mistakes.")
    if exam.award_partial_method:
        extra.append("Award partial marks for a correct method even if the final answer is wrong.")
    if exam.custom_rules:
        extra.append(f"Teacher rules: {exam.custom_rules}")
    return (
        f"Leniency: {rules}\n"
        + ("\n".join(extra) + "\n" if extra else "")
        + f"\nMARKING SCHEME (JSON):\n{json.dumps(scheme, ensure_ascii=False)}\n\n"
        "Grade the student's script (images below) and return the JSON described."
    )


def _read_pages(sheet: AnswerSheet) -> list[bytes]:
    out: list[bytes] = []
    base = Path(sheet.storage_dir) if sheet.storage_dir else None
    for fname in (sheet.page_files or []):
        try:
            path = base / fname if base else Path(fname)
            out.append(path.read_bytes())
        except Exception as e:  # noqa: BLE001
            logger.warning("could not read page %s: %s", fname, e)
    return out


def grade_answer_sheet(answer_sheet_id: uuid.UUID, *, force: bool = False) -> None:
    """BackgroundTask entrypoint: OCR + grade one sheet, write grades + ExamResult."""
    # Function-local import so tests' repointed SessionLocal (conftest) is used.
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        sheet = db.get(AnswerSheet, answer_sheet_id)
        if sheet is None:
            return
        exam = db.get(Exam, sheet.exam_id)
        if exam is None or exam.scheme_status != SchemeStatus.READY:
            sheet.status = AnswerSheetStatus.FAILED
            sheet.error_detail = "Exam scheme is not confirmed (status must be 'ready')."
            db.commit()
            return

        lock = _lock_for(exam.id)
        with lock:
            sheet.status = AnswerSheetStatus.OCR
            db.commit()

            questions = list(
                db.scalars(
                    select(ExamQuestion)
                    .where(ExamQuestion.exam_id == exam.id)
                    .order_by(ExamQuestion.order_index)
                ).all()
            )
            pages = _read_pages(sheet)
            if not questions or not pages:
                sheet.status = AnswerSheetStatus.FAILED
                sheet.error_detail = "No scheme questions or no answer pages found."
                db.commit()
                return

            raw = claude_client.generate_completion_vision(
                system=GRADING_SYSTEM,
                text=_build_prompt(exam, questions),
                images=pages,
                max_tokens=4096,
                temperature=0.1,
            )
            try:
                data = json.loads(_strip_json(raw))
            except Exception as e:  # noqa: BLE001
                logger.warning("grader: bad JSON for sheet %s: %s", sheet.id, e)
                sheet.status = AnswerSheetStatus.FAILED
                sheet.error_detail = "AI grading returned no parseable result."
                db.commit()
                return

            answers = {str(a.get("label")): a for a in (data.get("answers") or [])}

            # Roster match (don't override a teacher-confirmed match).
            if not sheet.is_match_confirmed:
                sheet.detected_usn = (data.get("detected_usn") or None)
                sheet.detected_name = (data.get("detected_name") or None)
                sid, conf, source = answersheet_match.match_student(
                    db, exam.subject_id, sheet.detected_usn, sheet.detected_name
                )
                sheet.student_id = sid
                sheet.match_confidence = conf
                sheet.match_source = source

            # Idempotent re-grade: clear prior non-overridden grades (keep overrides
            # unless force=True), then rewrite from the fresh AI output.
            existing = db.scalars(
                select(QuestionGrade).where(QuestionGrade.answer_sheet_id == sheet.id)
            ).all()
            overrides = {}
            for g in existing:
                if g.is_overridden and not force:
                    overrides[g.exam_question_id] = g
                else:
                    db.delete(g)
            db.flush()

            conf_thr = float(exam.confidence_review_threshold or 0.65)
            ocr_thr = float(exam.ocr_review_threshold or 0.55)
            needs_review = 0
            for q in questions:
                if q.id in overrides:
                    if overrides[q.id].needs_review:
                        needs_review += 1
                    continue
                a = answers.get(q.label, {})
                max_marks = float(q.max_marks or 0)
                try:
                    awarded = max(0.0, min(max_marks, float(a.get("awarded_marks") or 0)))
                except (TypeError, ValueError):
                    awarded = 0.0
                conf = a.get("confidence")
                ocr = a.get("ocr_confidence")
                flag = bool(a.get("needs_review")) or (conf is not None and float(conf) < conf_thr) \
                    or (ocr is not None and float(ocr) < ocr_thr) or (q.label not in answers)
                if flag:
                    needs_review += 1
                db.add(QuestionGrade(
                    answer_sheet_id=sheet.id,
                    exam_question_id=q.id,
                    extracted_answer=a.get("extracted_answer"),
                    awarded_marks=awarded,
                    max_marks=max_marks,
                    co=q.co,
                    confidence=(float(conf) if conf is not None else None),
                    ocr_confidence=(float(ocr) if ocr is not None else None),
                    rationale=a.get("rationale"),
                    needs_review=flag,
                ))
            db.flush()

            grades = db.scalars(
                select(QuestionGrade).where(QuestionGrade.answer_sheet_id == sheet.id)
            ).all()
            sheet.total_awarded = sum(g.effective_marks for g in grades)
            sheet.total_max = sum(float(g.max_marks or 0) for g in grades)
            sheet.needs_review_count = needs_review
            sheet.graded_at = datetime.now(timezone.utc)
            sheet.status = AnswerSheetStatus.GRADED if needs_review == 0 else AnswerSheetStatus.REVIEW

            grading_results.upsert_result(db, sheet)
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("grade_answer_sheet failed for %s", answer_sheet_id)
        try:
            sheet = db.get(AnswerSheet, answer_sheet_id)
            if sheet is not None:
                sheet.status = AnswerSheetStatus.FAILED
                sheet.error_detail = "Grading failed unexpectedly."
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()
