"""Document service: upload, list, retrieve, delete."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import DocumentChunk
from app.models.user import Document, DocumentStatus, Subject, User, UserRole
from app.schemas.document import (
    CompressionStats,
    DocumentChunkPreview,
    DocumentResponse,
    DocumentWithSubject,
)

# ── Config ──
# Uploads are stored at <repo>/backend/uploads/{subject_id}/{file_uuid}_{filename}.
# This is a local-disk solution for Phase 6 — Supabase Storage migration happens later.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend/
UPLOAD_ROOT = _BACKEND_ROOT / "uploads"
ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-powerpoint",  # .ppt
    "text/plain",
    "text/markdown",
}
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _ensure_upload_dir() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _validate_teacher_owns_subject(db: Session, subject_id: uuid.UUID, user: User) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if user.role == UserRole.TEACHER and subject.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this subject")
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers or admins can upload documents")
    return subject


def _compression_stats_for(db: Session, document_id: uuid.UUID) -> CompressionStats:
    """Aggregate compression stats across a document's chunks."""
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
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


def _to_response(document: Document, *, db: Session | None = None) -> DocumentResponse:
    stats = _compression_stats_for(db, document.id) if db is not None else None
    return DocumentResponse(
        id=document.id,
        subject_id=document.subject_id,
        uploaded_by_id=document.uploaded_by_id,
        title=document.title,
        file_name=document.file_name,
        content_type=document.content_type,
        file_size_bytes=document.file_size_bytes,
        summary=document.summary,
        processing_status=document.processing_status.value,
        created_at=document.created_at,
        compression_stats=stats,
    )


def _to_response_with_subject(
    document: Document,
    subject: Subject,
    stats: CompressionStats | None = None,
) -> DocumentWithSubject:
    return DocumentWithSubject(
        id=document.id,
        subject_id=document.subject_id,
        uploaded_by_id=document.uploaded_by_id,
        title=document.title,
        file_name=document.file_name,
        content_type=document.content_type,
        file_size_bytes=document.file_size_bytes,
        summary=document.summary,
        processing_status=document.processing_status.value,
        created_at=document.created_at,
        subject_code=subject.code,
        subject_name=subject.name,
        compression_stats=stats,
    )


def list_documents(
    db: Session,
    user: User,
    *,
    subject_id: uuid.UUID | None = None,
) -> list[DocumentWithSubject]:
    """List documents. Teachers see their own; admins see all."""
    stmt = select(Document, Subject).join(Subject, Document.subject_id == Subject.id)

    if user.role == UserRole.TEACHER:
        stmt = stmt.where(Subject.teacher_id == user.id)
    # admins: no scope filter
    # students: for now, also see documents in subjects they can access (phase 6 = all published)

    if subject_id is not None:
        stmt = stmt.where(Document.subject_id == subject_id)

    stmt = stmt.order_by(Document.created_at.desc())
    rows = db.execute(stmt).all()
    return [
        _to_response_with_subject(doc, subj, _compression_stats_for(db, doc.id))
        for (doc, subj) in rows
    ]


def list_chunks(db: Session, document_id: uuid.UUID, user: User) -> list[DocumentChunkPreview]:
    """Return all chunks for a document (for inspection / Phase 9 RAG)."""
    document = get_document(db, document_id, user)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    previews: list[DocumentChunkPreview] = []
    for c in chunks:
        previews.append(
            DocumentChunkPreview(
                id=c.id,
                chunk_index=c.chunk_index,
                chunk_text=c.chunk_text,
                compression_ratio=float(c.compression_ratio) if c.compression_ratio is not None else None,
                compressed_bytes=len(c.compressed_text) if c.compressed_text else None,
                original_bytes=len(c.chunk_text.encode("utf-8")),
            )
        )
    return previews


def get_document(db: Session, document_id: uuid.UUID, user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if user.role == UserRole.TEACHER:
        subject = db.get(Subject, document.subject_id)
        if subject is None or subject.teacher_id != user.id:
            raise HTTPException(status_code=403, detail="You don't own this document")

    return document


def upload_document(
    db: Session,
    subject_id: uuid.UUID,
    file: UploadFile,
    user: User,
    *,
    title: str | None = None,
) -> DocumentResponse:
    """Validate + save a file to disk, then create a Document row."""
    _ensure_upload_dir()
    subject = _validate_teacher_owns_subject(db, subject_id, user)

    # Validate filename and extension
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

    # Build the storage path
    subject_dir = UPLOAD_ROOT / str(subject.id)
    subject_dir.mkdir(parents=True, exist_ok=True)
    file_uuid = uuid.uuid4()
    safe_name = Path(original_name).name  # strip any path components
    storage_path = subject_dir / f"{file_uuid}_{safe_name}"

    # Stream to disk with size enforcement
    bytes_written = 0
    try:
        with storage_path.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)  # 1 MB chunks
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

    # Create the DB row. processing_status stays 'pending' until Phase 7 kicks off processing.
    document = Document(
        subject_id=subject.id,
        uploaded_by_id=user.id,
        title=(title or safe_name).strip(),
        file_name=safe_name,
        storage_path=str(storage_path.resolve()),
        content_type=file.content_type,
        file_size_bytes=bytes_written,
        processing_status=DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return _to_response(document, db=db)


def delete_document(db: Session, document_id: uuid.UUID, user: User) -> None:
    document = get_document(db, document_id, user)

    # Try to remove the file from disk (best effort)
    try:
        Path(document.storage_path).unlink(missing_ok=True)
    except Exception:
        pass

    db.delete(document)
    db.commit()
