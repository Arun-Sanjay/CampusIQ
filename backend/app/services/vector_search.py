"""pgvector-backed semantic search over document chunks.

Used by:
- Phase 9: AI Note Assistant (RAG)
- Phase 10: CollegeGPT (separate `college_document_chunks` table)
- Phase 17: Job-fit scoring

DAA Unit IV — cosine distance via pgvector's `<=>` operator. The IVFFlat
index created in Phase 4 makes this O(√n) instead of O(n).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import CollegeDocument, CollegeDocumentChunk, DocumentChunk
from app.models.user import Document, Subject, User, UserRole
from app.services import embeddings

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    """A single search result — chunk + parent doc + similarity score."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    chunk_index: int
    chunk_text: str
    similarity: float  # 1.0 = identical, 0.0 = orthogonal


@dataclass
class CollegeSearchHit:
    """A single CollegeGPT search result — college doc chunk + similarity score."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    document_category: str
    chunk_index: int
    chunk_text: str
    similarity: float


def search_chunks(
    db: Session,
    query: str,
    user: User,
    *,
    subject_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    top_k: int = 5,
) -> list[SearchHit]:
    """Find the `top_k` most semantically similar chunks to the query.

    Scope rules:
    - Teachers see only their own subjects' chunks
    - Admins see everything
    - Students (Phase 9+) see chunks from any published subject — for now we
      apply the same teacher rule because student access isn't wired yet.
    """
    if not query.strip():
        return []

    # 1. Embed the query
    query_vector = embeddings.embed_text(query)
    if not query_vector:
        logger.warning("vector_search: query embedding empty (model unavailable?)")
        return []

    # 2. Build the SELECT — pgvector cosine distance is `embedding <=> vec`,
    #    where 0 = identical and 2 = opposite. Convert to similarity = 1 - dist/2.
    distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)

    stmt = (
        select(
            DocumentChunk,
            Document,
            Subject,
            distance_expr.label("distance"),
        )
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Subject, Document.subject_id == Subject.id)
        .where(DocumentChunk.embedding.isnot(None))
    )

    # Scope filter
    if user.role == UserRole.TEACHER:
        stmt = stmt.where(Subject.teacher_id == user.id)
    # admins: no filter

    if subject_id is not None:
        stmt = stmt.where(Subject.id == subject_id)
    if document_id is not None:
        stmt = stmt.where(Document.id == document_id)

    stmt = stmt.order_by(distance_expr).limit(top_k)

    rows = db.execute(stmt).all()

    hits: list[SearchHit] = []
    for chunk, document, subject, distance in rows:
        # cosine distance ranges 0..2 in pgvector; flip to 0..1 similarity
        similarity = max(0.0, 1.0 - float(distance) / 2.0)
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                subject_id=subject.id,
                subject_code=subject.code,
                subject_name=subject.name,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                similarity=similarity,
            )
        )

    return hits


def search_college_chunks(
    db: Session,
    query: str,
    user: User,
    *,
    college_document_id: uuid.UUID | None = None,
    category: str | None = None,
    top_k: int = 5,
) -> list[CollegeSearchHit]:
    """Find the `top_k` most semantically similar chunks across CollegeGPT documents.

    All authenticated users can query college documents (CollegeGPT is open to
    students, teachers, and admins). Optionally narrow to a single document or
    a single document category (e.g. "placement_record" for the Placement
    Chatbot).
    """
    if not query.strip():
        return []

    query_vector = embeddings.embed_text(query)
    if not query_vector:
        logger.warning("vector_search.college: query embedding empty (model unavailable?)")
        return []

    distance_expr = CollegeDocumentChunk.embedding.cosine_distance(query_vector)

    stmt = (
        select(
            CollegeDocumentChunk,
            CollegeDocument,
            distance_expr.label("distance"),
        )
        .join(
            CollegeDocument,
            CollegeDocumentChunk.college_document_id == CollegeDocument.id,
        )
        .where(CollegeDocumentChunk.embedding.isnot(None))
    )

    if college_document_id is not None:
        stmt = stmt.where(CollegeDocument.id == college_document_id)
    if category is not None:
        stmt = stmt.where(CollegeDocument.document_category == category)

    stmt = stmt.order_by(distance_expr).limit(top_k)

    rows = db.execute(stmt).all()

    hits: list[CollegeSearchHit] = []
    for chunk, document, distance in rows:
        similarity = max(0.0, 1.0 - float(distance) / 2.0)
        hits.append(
            CollegeSearchHit(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                document_category=document.document_category.value,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                similarity=similarity,
            )
        )

    return hits
