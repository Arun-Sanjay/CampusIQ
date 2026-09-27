"""Ingest uploaded answer sheets (batch or single) into AnswerSheet rows.

Pages are rasterized + downscaled and stored privately under
``backend/uploads/grading/{exam_id}/{sheet_id}/`` (NOT a static mount — served only
via an authenticated route). The route schedules grade_answer_sheet() per sheet.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.grading import AnswerSheet
from app.services import grading_images
from app.services.document import UPLOAD_ROOT

MAX_FILE_BYTES = 30 * 1024 * 1024  # 30 MB per file (a multi-page booklet scan)
GRADING_ROOT = UPLOAD_ROOT / "grading"


def _file_to_pages(file: UploadFile) -> list[bytes]:
    raw = file.file.read(MAX_FILE_BYTES + 1)
    try:
        file.file.close()
    except Exception:  # noqa: BLE001
        pass
    if not raw:
        return []
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB limit.",
        )
    ext = Path(file.filename or "").suffix.lower()
    is_pdf = ext == ".pdf" or (file.content_type == "application/pdf")
    try:
        if is_pdf:
            return grading_images.pdf_to_page_images(raw)
        return [grading_images.normalize_image_bytes(raw)]
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read '{file.filename}': {e}")


def _save_pages(exam_id: uuid.UUID, sheet_id: uuid.UUID, pages: list[bytes]) -> tuple[str, list[str]]:
    d = GRADING_ROOT / str(exam_id) / str(sheet_id)
    d.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for i, b in enumerate(pages):
        name = f"page_{i:03d}.png"
        (d / name).write_bytes(b)
        names.append(name)
    return str(d), names


def _create_sheet(
    db: Session,
    exam_id: uuid.UUID,
    pages: list[bytes],
    batch_id: uuid.UUID | None,
    *,
    student_id: uuid.UUID | None = None,
) -> AnswerSheet:
    sheet = AnswerSheet(
        exam_id=exam_id,
        student_id=student_id,
        batch_id=batch_id,
        match_source=("manual" if student_id else "unmatched"),
        is_match_confirmed=bool(student_id),
    )
    db.add(sheet)
    db.flush()  # assign id
    storage_dir, names = _save_pages(exam_id, sheet.id, pages)
    sheet.storage_dir = storage_dir
    sheet.page_files = names
    db.flush()
    return sheet


def ingest_single(
    db: Session,
    exam_id: uuid.UUID,
    file: UploadFile,
    *,
    student_id: uuid.UUID | None = None,
) -> AnswerSheet:
    """One student's script (PDF or single image), optionally pre-matched."""
    pages = _file_to_pages(file)
    if not pages:
        raise HTTPException(status_code=400, detail="Empty upload.")
    sheet = _create_sheet(db, exam_id, pages, None, student_id=student_id)
    db.commit()
    return sheet


def ingest_batch(
    db: Session,
    exam_id: uuid.UUID,
    files: list[UploadFile],
    *,
    pages_per_student: int | None = None,
) -> list[AnswerSheet]:
    """A whole class at once.

    - One multi-page PDF + ``pages_per_student`` → split into per-student bundles.
    - Many image/PDF files → one sheet per file (e.g. one photo per student).
    - One PDF, no ``pages_per_student`` → a single sheet (teacher can re-split).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    batch_id = uuid.uuid4()
    sheets: list[AnswerSheet] = []
    if len(files) == 1 and pages_per_student:
        pages = _file_to_pages(files[0])
        for bundle in grading_images.chunk_pages(pages, pages_per_student):
            if bundle:
                sheets.append(_create_sheet(db, exam_id, bundle, batch_id))
    else:
        for f in files:
            pages = _file_to_pages(f)
            if pages:
                sheets.append(_create_sheet(db, exam_id, pages, batch_id))
    db.commit()
    return sheets
