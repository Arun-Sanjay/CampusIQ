"""College document service: admin upload + CRUD for CollegeGPT (Phase 10, F5).

Mirrors `services/document.py` but writes to the `college_documents` /
`college_document_chunks` tables. The processing pipeline lives in
`services/college_document_processor.py`.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import (
    CollegeDocument,
    CollegeDocumentCategory,
    CollegeDocumentChunk,
)
from app.models.user import User, UserRole
from app.schemas.college_document import (
    CollegeDocumentChunkPreview,
    CollegeDocumentResponse,
)
from app.schemas.document import CompressionStats
from app.services.document import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_BYTES,
)

# ── Config ──
_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend/
COLLEGE_UPLOAD_ROOT = _BACKEND_ROOT / "uploads" / "college"


def _ensure_upload_dir() -> None:
    COLLEGE_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage college documents.",
        )


def _compression_stats_for(db: Session, college_document_id: uuid.UUID) -> CompressionStats:
    chunks = (
        db.query(CollegeDocumentChunk)
        .filter(CollegeDocumentChunk.college_document_id == college_document_id)
        .all()
    )
    if not chunks:
        return CompressionStats()

    original = sum(len(c.chunk_text.encode("utf-8")) for c in chunks)
    compressed = sum(len(c.compressed_text or b"") for c in chunks)
    savings = 0.0
    if original > 0:
        savings = round((1 - compressed / original) * 100, 2)

    return CompressionStats(
        original_bytes=original,
        compressed_bytes=compressed,
        savings_percent=savings,
        chunk_count=len(chunks),
    )


def _to_response(
    document: CollegeDocument, *, db: Session | None = None
) -> CollegeDocumentResponse:
    stats = _compression_stats_for(db, document.id) if db is not None else None
    return CollegeDocumentResponse(
        id=document.id,
        college_id=document.college_id,
        uploaded_by_id=document.uploaded_by_id,
        title=document.title,
        file_name=document.file_name,
        file_type=document.file_type,
        document_category=document.document_category.value,
        summary=document.summary,
        processing_status=document.processing_status,
        created_at=document.created_at,
        compression_stats=stats,
    )


def list_college_documents(
    db: Session,
    user: User,
    *,
    category: CollegeDocumentCategory | None = None,
) -> list[CollegeDocumentResponse]:
    """All college documents — visible to every authenticated user."""
    stmt = select(CollegeDocument).order_by(CollegeDocument.created_at.desc())
    if category is not None:
        stmt = stmt.where(CollegeDocument.document_category == category)
    documents = db.scalars(stmt).all()
    return [_to_response(d, db=db) for d in documents]


def get_college_document(
    db: Session, college_document_id: uuid.UUID, user: User
) -> CollegeDocument:
    document = db.get(CollegeDocument, college_document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="College document not found")
    return document


def list_college_chunks(
    db: Session, college_document_id: uuid.UUID, user: User
) -> list[CollegeDocumentChunkPreview]:
    document = get_college_document(db, college_document_id, user)
    chunks = (
        db.query(CollegeDocumentChunk)
        .filter(CollegeDocumentChunk.college_document_id == document.id)
        .order_by(CollegeDocumentChunk.chunk_index)
        .all()
    )
    return [
        CollegeDocumentChunkPreview(
            id=c.id,
            chunk_index=c.chunk_index,
            chunk_text=c.chunk_text,
            compression_ratio=float(c.compression_ratio) if c.compression_ratio is not None else None,
            compressed_bytes=len(c.compressed_text) if c.compressed_text else None,
            original_bytes=len(c.chunk_text.encode("utf-8")),
        )
        for c in chunks
    ]


def upload_college_document(
    db: Session,
    file: UploadFile,
    user: User,
    *,
    title: str | None = None,
    document_category: CollegeDocumentCategory = CollegeDocumentCategory.OTHER,
) -> CollegeDocumentResponse:
    """Validate + save a file to disk, then create a CollegeDocument row."""
    _require_admin(user)
    _ensure_upload_dir()

    original_name = file.filename or "untitled"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File extension '{ext}' not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content type '{file.content_type}' not allowed.",
        )

    file_uuid = uuid.uuid4()
    safe_name = Path(original_name).name
    storage_path = COLLEGE_UPLOAD_ROOT / f"{file_uuid}_{safe_name}"

    bytes_written = 0
    try:
        with storage_path.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    out.close()
                    storage_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    document = CollegeDocument(
        college_id=user.college_id,
        uploaded_by_id=user.id,
        title=(title or safe_name).strip(),
        file_name=safe_name,
        storage_path=str(storage_path.resolve()),
        file_type=file.content_type,
        document_category=document_category,
        processing_status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_response(document, db=db)


def delete_college_document(
    db: Session, college_document_id: uuid.UUID, user: User
) -> None:
    _require_admin(user)
    document = get_college_document(db, college_document_id, user)

    try:
        Path(document.storage_path).unlink(missing_ok=True)
    except Exception:
        pass

    db.delete(document)
    db.commit()
