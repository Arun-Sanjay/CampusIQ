"""Chunk-level CRUD for college documents — powers the admin Knowledge Editor.

Re-uses the same primitives as the full ingestion pipeline
(`huffman.encode`, `embeddings.embed_text`) but operates on a single chunk
at a time so admins can hand-edit individual facts without re-running
the whole extraction loop.

The chunk is the canonical record for retrieval: vector_search reads
`chunk_text` + `embedding`, so editing those is enough for CollegeGPT to
reflect the change. The original PDF on disk is never modified.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import CollegeDocument, CollegeDocumentChunk
from app.models.user import User, UserRole
from app.schemas.college_document import CollegeDocumentChunkPreview
from app.services import embeddings, huffman

logger = logging.getLogger(__name__)


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can edit college document chunks.",
        )


def _load_chunk(
    db: Session, doc_id: uuid.UUID, chunk_id: uuid.UUID
) -> CollegeDocumentChunk:
    chunk = db.get(CollegeDocumentChunk, chunk_id)
    if chunk is None or chunk.college_document_id != doc_id:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


def _ensure_document(db: Session, doc_id: uuid.UUID) -> CollegeDocument:
    document = db.get(CollegeDocument, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="College document not found")
    return document


def _to_preview(chunk: CollegeDocumentChunk) -> CollegeDocumentChunkPreview:
    return CollegeDocumentChunkPreview(
        id=chunk.id,
        chunk_index=chunk.chunk_index,
        chunk_text=chunk.chunk_text,
        compression_ratio=(
            float(chunk.compression_ratio)
            if chunk.compression_ratio is not None
            else None
        ),
        compressed_bytes=len(chunk.compressed_text) if chunk.compressed_text else None,
        original_bytes=len(chunk.chunk_text.encode("utf-8")),
    )


def _apply_text(chunk: CollegeDocumentChunk, new_text: str) -> None:
    """Rewrite a chunk's text in place: compress + (re-)embed and update
    all derived fields. The caller is responsible for `db.commit()`."""
    cleaned = new_text.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="Chunk text cannot be empty.")

    result = huffman.encode(cleaned)
    chunk.chunk_text = cleaned
    chunk.compressed_text = result.compressed
    chunk.codebook = result.codebook
    chunk.compression_ratio = Decimal(str(result.savings_percent))

    if embeddings.is_available():
        vector = embeddings.embed_text(cleaned)
        if vector:
            chunk.embedding = vector
        else:
            logger.warning(
                "chunk_edit: embed_text returned empty for chunk %s; keeping prior embedding",
                chunk.id,
            )
    else:
        logger.warning(
            "chunk_edit: embeddings model unavailable; keeping prior embedding on chunk %s",
            chunk.id,
        )


def update_chunk_text(
    db: Session,
    user: User,
    doc_id: uuid.UUID,
    chunk_id: uuid.UUID,
    new_text: str,
) -> CollegeDocumentChunkPreview:
    _require_admin(user)
    _ensure_document(db, doc_id)
    chunk = _load_chunk(db, doc_id, chunk_id)
    _apply_text(chunk, new_text)
    db.commit()
    db.refresh(chunk)
    return _to_preview(chunk)


def append_chunk(
    db: Session,
    user: User,
    doc_id: uuid.UUID,
    new_text: str,
    *,
    chunk_index: int | None = None,
) -> CollegeDocumentChunkPreview:
    _require_admin(user)
    document = _ensure_document(db, doc_id)

    if chunk_index is None:
        max_index = db.scalar(
            select(func.max(CollegeDocumentChunk.chunk_index)).where(
                CollegeDocumentChunk.college_document_id == document.id
            )
        )
        chunk_index = 0 if max_index is None else max_index + 1
    else:
        existing = db.scalar(
            select(CollegeDocumentChunk.id).where(
                CollegeDocumentChunk.college_document_id == document.id,
                CollegeDocumentChunk.chunk_index == chunk_index,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Chunk index {chunk_index} already exists on this document.",
            )

    chunk = CollegeDocumentChunk(
        college_document_id=document.id,
        chunk_index=chunk_index,
        chunk_text=new_text.strip(),  # `_apply_text` will overwrite anyway
    )
    db.add(chunk)
    db.flush()  # populate chunk.id
    _apply_text(chunk, new_text)
    db.commit()
    db.refresh(chunk)
    return _to_preview(chunk)


def delete_chunk(
    db: Session,
    user: User,
    doc_id: uuid.UUID,
    chunk_id: uuid.UUID,
) -> None:
    _require_admin(user)
    _ensure_document(db, doc_id)
    chunk = db.get(CollegeDocumentChunk, chunk_id)
    if chunk is None or chunk.college_document_id != doc_id:
        # Idempotent: nothing to do if already gone.
        return
    db.delete(chunk)
    db.commit()
