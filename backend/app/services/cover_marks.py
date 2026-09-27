"""Auto Marks Assigner — scan an answer-booklet COVER page and record the marks.

A lighter path than full AI grading: instead of OCR-ing and grading every answer,
this reads the marks tally already written on the FRONT/cover page of an exam
booklet (per-question and/or per-CO marks an evaluator filled in), maps it to
Course Outcomes, and hands it back so the result lands straight in the student's
record (ExamResult → grade engine). One Claude vision call per cover page.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.grading import Exam, ExamQuestion
from app.services import answersheet_match, claude_client, grade_engine, grading_results

logger = logging.getLogger(__name__)

COVER_SYSTEM = """You are reading the FRONT/COVER page of an Indian engineering college (RVCE) exam answer booklet.
The cover page has a "marks awarded" tally table filled in by the evaluator, plus a header with the student's USN and name.

Extract, as STRICT JSON only (no prose, no markdown fences):
{
  "detected_usn": "string or null",      // University Seat Number, e.g. 1RV23CS001
  "detected_name": "string or null",
  "total_awarded": number or null,       // grand total marks if written
  "total_max": number or null,           // maximum marks if written
  "per_question": [                       // one row per question in the tally, if present
    {"label": "1a", "awarded": 4, "max": 5, "co": "CO3"}    // co may be null if not shown
  ],
  "per_co": [                             // CO-wise totals if the cover shows a CO breakdown
    {"co": "CO1", "obtained": 8, "max": 10}
  ]
}
Rules: Read ONLY the marks already written on the page — do NOT grade or compute anything yourself.
Every number must come from the printed/handwritten table. If a field isn't on the page, use null or [].
'awarded'/'obtained' is the marks given; 'max' is the maximum for that row."""


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


def _compute(db: Session, exam: Exam, data: dict) -> tuple[dict | None, float, float]:
    """Build the {co:{obtained,max,pct}} dict + (total_obtained, total_max) from the
    extracted cover data, preferring explicit per-CO totals, then per-question rows
    mapped to COs via the scheme (when a scheme exists)."""
    co_obtained: dict[str, float] = {}
    co_max: dict[str, float] = {}

    per_co_raw = data.get("per_co") or []
    if per_co_raw:
        for row in per_co_raw:
            co = str(row.get("co") or "").strip()
            if not co:
                continue
            co_obtained[co] = co_obtained.get(co, 0.0) + _num(row.get("obtained"))
            co_max[co] = co_max.get(co, 0.0) + _num(row.get("max"))
    else:
        # Map per-question rows to COs. Use the row's own CO tag, else look it up
        # from the scheme by label (when the exam has questions defined).
        by_label = {
            q.label.strip().lower(): q
            for q in db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)).all()
        }
        for row in (data.get("per_question") or []):
            label = str(row.get("label") or "").strip().lower()
            q = by_label.get(label)
            co = row.get("co") or (q.co if q else None)
            if not co:
                continue
            co = str(co).strip()
            co_obtained[co] = co_obtained.get(co, 0.0) + _num(row.get("awarded"))
            co_max[co] = co_max.get(co, 0.0) + (_num(row.get("max")) or float(q.max_marks or 0) if q else _num(row.get("max")))

    # Prefer authoritative per-CO maxima from the exam (co_mark_grid / scheme).
    auth_max = grading_results.co_max_lookup(db, exam)
    per_co: dict[str, dict] = {}
    for co in co_obtained:
        mx = auth_max.get(co) or co_max.get(co, 0.0)
        per_co[co] = {
            "obtained": grade_engine.round2(co_obtained[co]),
            "max": grade_engine.round2(mx),
            "pct": grade_engine.round2(grade_engine.safe_pct(co_obtained[co], mx)),
        }

    total_obtained = data.get("total_awarded")
    if total_obtained is None:
        total_obtained = (
            sum(co_obtained.values()) if co_obtained
            else sum(_num(r.get("awarded")) for r in (data.get("per_question") or []))
        )
    total_obtained = float(total_obtained or 0)
    total_max = (
        float(exam.max_marks or 0)
        or _num(data.get("total_max"))
        or (sum(co_max.values()) if co_max else 0.0)
    )
    return (per_co or None), total_obtained, total_max


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def scan_cover(db: Session, exam: Exam, image_bytes: bytes) -> dict:
    """Vision-read one cover page → extracted marks + best-effort roster match.

    Returns a dict (NOT persisted): the caller decides whether to save it (e.g.
    only when a student matched). Never raises — degrades to empty extraction.
    """
    raw = claude_client.generate_completion_vision(
        system=COVER_SYSTEM,
        text="Read this answer-booklet cover page's marks tally and header. Return the JSON described.",
        images=[image_bytes],
        max_tokens=1500,
        temperature=0.0,
    )
    try:
        data = json.loads(_strip_json(raw))
    except Exception as exc:  # noqa: BLE001
        logger.warning("cover scan: bad JSON: %s", exc)
        data = {}

    per_co, total_obtained, total_max = _compute(db, exam, data)
    usn = (data.get("detected_usn") or None)
    name = (data.get("detected_name") or None)
    sid, conf, source = answersheet_match.match_student(db, exam.subject_id, usn, name)
    return {
        "detected_usn": usn,
        "detected_name": name,
        "student_id": sid,
        "match_confidence": conf,
        "match_source": source,
        "total_obtained": grade_engine.round2(total_obtained),
        "total_max": grade_engine.round2(total_max),
        "per_co": per_co,
    }
