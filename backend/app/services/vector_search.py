"""pgvector-backed semantic search over document chunks.

Used by:
- Phase 9: AI Note Assistant (RAG)
- Phase 10: CollegeGPT (separate `college_document_chunks` table)
- Phase 17: Job-fit scoring

On Postgres + pgvector we lean on the `<=>` cosine-distance operator with
the HNSW index for O(log n) retrieval. On SQLite (the local dev DB) there
is no such operator, so we fall back to a Python loop that computes cosine
distance over the candidate chunks. The chunk count is small enough at
the local-dev scale that the O(n) fallback is fine.
"""
from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import CollegeDocument, CollegeDocumentChunk, DocumentChunk
from app.models.user import Document, Subject, User, UserRole
from app.services import embeddings

logger = logging.getLogger(__name__)


def _is_sqlite(db: Session) -> bool:
    """True if the bound engine is SQLite."""
    bind = db.bind or db.get_bind()
    return bool(bind and bind.dialect.name == "sqlite")


def _embedding_to_list(value: object) -> list[float] | None:
    """Normalise a stored embedding to a plain list[float].

    pgvector_sqlalchemy's Vector type returns a numpy array on Postgres
    and a list on SQLite, but on SQLite the value can come back as a JSON
    string when the Vector adapter isn't fully wired. Handle every shape
    gracefully — return None if we can't make sense of it.
    """
    if value is None:
        return None
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()  # numpy.ndarray
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, (list, tuple)):
        try:
            return [float(x) for x in value]
        except Exception:  # noqa: BLE001
            return None
    if isinstance(value, str):
        # Most likely a JSON-ish string like "[0.1, -0.2, ...]"
        cleaned = value.strip().lstrip("[").rstrip("]")
        if not cleaned:
            return None
        try:
            return [float(x) for x in cleaned.split(",")]
        except Exception:  # noqa: BLE001
            return None
    return None


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """0 = identical, 2 = opposite. Mirrors pgvector's `<=>` operator."""
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 2.0
    return 1.0 - dot / math.sqrt(na * nb)


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

    Visibility rules (same as `document._can_view_document`):
    - Admins see everything.
    - Teachers see only the public chunks of their own subjects (never see
      a student's private notes).
    - Students see all public chunks PLUS their own private notes' chunks
      (the NotebookLM-style personal-notes integration).
    """
    if not query.strip():
        return []

    # 1. Embed the query
    query_vector = embeddings.embed_text(query)
    if not query_vector:
        logger.warning("vector_search: query embedding empty (model unavailable?)")
        return []

    # 2. Build the SELECT. On Postgres we order by `embedding <=> vec` in SQL;
    #    on SQLite we have to pull candidates and rank them in Python.
    from sqlalchemy import or_

    use_python_cosine = _is_sqlite(db)

    base_stmt = (
        select(DocumentChunk, Document, Subject)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Subject, Document.subject_id == Subject.id)
        .where(DocumentChunk.embedding.isnot(None))
    )

    # Scope filter (identical for both dialects).
    if user.role == UserRole.TEACHER:
        # Teacher: only public chunks within their own subjects.
        base_stmt = base_stmt.where(Subject.teacher_id == user.id)
        base_stmt = base_stmt.where(Document.owner_student_id.is_(None))
    elif user.role == UserRole.STUDENT:
        # Student: public chunks of any subject + their own private-note chunks.
        base_stmt = base_stmt.where(
            or_(
                Document.owner_student_id.is_(None),
                Document.owner_student_id == user.id,
            )
        )
    # admins: no filter

    if subject_id is not None:
        base_stmt = base_stmt.where(Subject.id == subject_id)
    if document_id is not None:
        base_stmt = base_stmt.where(Document.id == document_id)

    if use_python_cosine:
        # SQLite path: rank in Python over the candidate set.
        rows = db.execute(base_stmt).all()
        scored: list[tuple[float, DocumentChunk, Document, Subject]] = []
        for chunk, document, subject in rows:
            emb = _embedding_to_list(chunk.embedding)
            if emb is None or len(emb) != len(query_vector):
                continue
            d = _cosine_distance(query_vector, emb)
            scored.append((d, chunk, document, subject))
        scored.sort(key=lambda x: x[0])
        scored = scored[:top_k]
        hits: list[SearchHit] = []
        for distance, chunk, document, subject in scored:
            similarity = max(0.0, 1.0 - distance / 2.0)
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

    # Postgres path: pgvector `<=>` + ORDER BY in SQL.
    distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        base_stmt.add_columns(distance_expr.label("distance"))
        .order_by(distance_expr)
        .limit(top_k)
    )
    rows = db.execute(stmt).all()

    hits: list[SearchHit] = []
    for chunk, document, subject, distance in rows:
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

    use_python_cosine = _is_sqlite(db)

    base_stmt = (
        select(CollegeDocumentChunk, CollegeDocument)
        .join(
            CollegeDocument,
            CollegeDocumentChunk.college_document_id == CollegeDocument.id,
        )
        .where(CollegeDocumentChunk.embedding.isnot(None))
    )

    if college_document_id is not None:
        base_stmt = base_stmt.where(CollegeDocument.id == college_document_id)
    if category is not None:
        base_stmt = base_stmt.where(CollegeDocument.document_category == category)

    if use_python_cosine:
        # SQLite path: rank in Python.
        rows = db.execute(base_stmt).all()
        scored: list[tuple[float, CollegeDocumentChunk, CollegeDocument]] = []
        for chunk, document in rows:
            emb = _embedding_to_list(chunk.embedding)
            if emb is None or len(emb) != len(query_vector):
                continue
            d = _cosine_distance(query_vector, emb)
            scored.append((d, chunk, document))
        scored.sort(key=lambda x: x[0])
        scored = scored[:top_k]
        hits: list[CollegeSearchHit] = []
        for distance, chunk, document in scored:
            similarity = max(0.0, 1.0 - distance / 2.0)
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

    # Postgres path.
    distance_expr = CollegeDocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        base_stmt.add_columns(distance_expr.label("distance"))
        .order_by(distance_expr)
        .limit(top_k)
    )
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
