"""Parse an uploaded scheme/answer-key paper into structured ExamQuestions.

Runs as a BackgroundTask with its own session (like document_processor). Text
extraction first (most schemes are digital PDFs); falls back to Claude vision for
scanned schemes. Output goes to REVIEW status — the teacher confirms before grading.
"""
from __future__ import annotations

import json
import logging
import uuid

from app.models.grading import CourseOutcome, Exam, ExamQuestion, SchemeStatus
from app.models.user import Document
from app.services import claude_client, grading_images, text_extraction

logger = logging.getLogger(__name__)

SCHEME_SYSTEM = """You are an exam-scheme parser for an Indian engineering college (RVCE).
You are given a question paper that INCLUDES the model answers and a marking scheme.
Each question is tagged with marks, a Bloom's Taxonomy level (L1-L6) and a Course
Outcome (CO1-CO5). Papers usually have Part A (short/objective) and Part B (long).

Return STRICT JSON only (no prose, no markdown fences) in exactly this shape:
{
  "title": "string",
  "total_marks": number,
  "course_outcomes": [{"code": "CO1", "text": "..."}],
  "co_mark_grid": {"CO1": 10, "CO2": 25},
  "questions": [
    {"label": "1a", "parent_label": "1", "part": "part_a"|"part_b",
     "question_text": "...", "model_answer": "...", "max_marks": 5,
     "co": "CO3", "bloom": "L2"}
  ]
}
Rules: copy the model answer (the "Ans:" content) verbatim into model_answer.
Preserve sub-part labels exactly (1a, 1b, 2a...). Map part_a to short Part-A items,
part_b otherwise. If a CO or Bloom level is missing, use null. Never invent marks —
sum of question max_marks should equal total_marks. co_mark_grid maps each CO to the
TOTAL marks allocated to it across the paper.

If the document is study NOTES, a topic summary, or a light/informal reference
rather than a formal question-paper-with-answers, DON'T fail — infer a reasonable
set of 5-10 exam questions and concise model answers from the key topics it covers,
assign plausible marks that sum to total_marks, and spread them across CO1-CO5.
Approximate is fine; the teacher will review and can edit before grading."""


def _strip_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -3]
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    # trim to the outermost object
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start : end + 1]
    return t


def _parse(raw: str) -> dict | None:
    try:
        return json.loads(_strip_json(raw))
    except Exception as e:  # noqa: BLE001
        logger.warning("scheme parse: bad JSON: %s", e)
        return None


def parse_scheme_text(text: str) -> dict | None:
    out = claude_client.generate_completion(
        system=SCHEME_SYSTEM,
        user_message=f"Parse this scheme paper into the JSON structure.\n\n---\n{text[:18000]}\n---",
        max_tokens=4096,
        temperature=0.1,
    )
    return _parse(out)


def parse_scheme_vision(image_pages: list[bytes]) -> dict | None:
    out = claude_client.generate_completion_vision(
        system=SCHEME_SYSTEM,
        text="Parse this scanned scheme paper (images) into the JSON structure.",
        images=image_pages,
        max_tokens=4096,
        temperature=0.1,
    )
    return _parse(out)


def _persist(db, exam: Exam, data: dict) -> None:
    # Clear any prior parse (re-parse is idempotent).
    for q in list(exam.questions):
        db.delete(q)
    db.query(CourseOutcome).filter(CourseOutcome.subject_id == exam.subject_id).delete()
    db.flush()

    if data.get("total_marks"):
        try:
            exam.max_marks = float(data["total_marks"])
        except (TypeError, ValueError):
            pass
    if isinstance(data.get("co_mark_grid"), dict):
        exam.co_mark_grid = {str(k): v for k, v in data["co_mark_grid"].items()}

    for i, co in enumerate(data.get("course_outcomes") or []):
        code = (co.get("code") or "").strip()
        if not code:
            continue
        db.add(CourseOutcome(subject_id=exam.subject_id, code=code,
                             description=co.get("text"), order_index=i))

    valid_cos = {c.get("code") for c in (data.get("course_outcomes") or []) if c.get("code")}
    for i, q in enumerate(data.get("questions") or []):
        label = str(q.get("label") or f"Q{i + 1}").strip()
        part = "lab" if str(q.get("part")) == "lab" else "theory"
        # Map the scheme's part_a/part_b to theory (we use ExamPart for theory/lab,
        # and part_a/part_b is a presentation detail captured implicitly by order).
        try:
            max_marks = float(q.get("max_marks") or 0)
        except (TypeError, ValueError):
            max_marks = 0.0
        co = q.get("co") if q.get("co") in valid_cos else (q.get("co") or None)
        db.add(ExamQuestion(
            exam_id=exam.id,
            order_index=i,
            part=part,
            label=label[:20],
            parent_label=(str(q["parent_label"])[:20] if q.get("parent_label") else None),
            question_text=str(q.get("question_text") or ""),
            model_answer=q.get("model_answer"),
            max_marks=max_marks,
            co=(str(co)[:8] if co else None),
            bloom=(str(q["bloom"])[:4] if q.get("bloom") else None),
        ))


def process_scheme(exam_id: uuid.UUID) -> None:
    """BackgroundTask entrypoint: parse the exam's scheme document → REVIEW."""
    # Function-local import so tests' repointed SessionLocal (conftest) is used.
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        exam = db.get(Exam, exam_id)
        if exam is None or exam.scheme_document_id is None:
            return
        exam.scheme_status = SchemeStatus.PARSING
        db.commit()

        doc = db.get(Document, exam.scheme_document_id)
        if doc is None:
            exam.scheme_status = SchemeStatus.FAILED
            db.commit()
            return

        data: dict | None = None
        try:
            text = text_extraction.extract_text(doc.storage_path)
        except Exception:  # noqa: BLE001
            text = ""
        if text and len(text.strip()) > 200:
            data = parse_scheme_text(text)
        if data is None and str(doc.storage_path).lower().endswith(".pdf"):
            try:
                pages = grading_images.pdf_to_page_images(doc.storage_path)[:8]
                data = parse_scheme_vision(pages)
            except Exception as e:  # noqa: BLE001
                logger.warning("scheme vision fallback failed: %s", e)

        if not data or not data.get("questions"):
            # Light/notes-scheme fallback: rather than fail, create a single
            # holistic question graded against the uploaded material as a whole.
            material = (text or "").strip()
            if material:
                data = {
                    "questions": [{
                        "label": "Q1",
                        "part": "part_b",
                        "question_text": "Answer as per the exam — graded holistically against the uploaded reference material.",
                        "model_answer": material[:6000],
                        "max_marks": float(exam.max_marks or 0) or 100,
                        "co": None,
                        "bloom": None,
                    }],
                }
            else:
                exam.scheme_status = SchemeStatus.FAILED
                db.commit()
                return

        _persist(db, exam, data)
        exam.scheme_status = SchemeStatus.REVIEW
        db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("process_scheme failed for %s", exam_id)
        try:
            exam = db.get(Exam, exam_id)
            if exam is not None:
                exam.scheme_status = SchemeStatus.FAILED
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()
