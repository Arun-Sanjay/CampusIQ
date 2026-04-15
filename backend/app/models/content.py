"""Content models: document chunks, college documents, announcements."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, LargeBinary, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._enum_helper import enum_values

# Embedding dimension — matches Sentence Transformers all-MiniLM-L6-v2 (Phase 8)
EMBEDDING_DIM = 384


class DocumentChunk(Base):
    """Text chunks extracted from documents. Huffman-compressed + embedded for RAG."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Huffman compression (Phase 7 — DAA Unit IV)
    compressed_text: Mapped[bytes | None] = mapped_column(LargeBinary)
    codebook: Mapped[dict | None] = mapped_column(JSON)
    compression_ratio: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # pgvector embedding (Phase 8 — Sentence Transformers all-MiniLM-L6-v2, 384 dims)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")  # type: ignore[name-defined]


class CollegeDocumentCategory(str, enum.Enum):
    HANDBOOK = "handbook"
    TIMETABLE = "timetable"
    PLACEMENT_RECORD = "placement_record"
    FACULTY_LIST = "faculty_list"
    HOSTEL_RULES = "hostel_rules"
    OTHER = "other"


class CollegeDocument(Base):
    """Admin-uploaded college documents for CollegeGPT (F5)."""

    __tablename__ = "college_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # college_id is nullable in v1 (single-tenant). When multi-tenant support
    # lands in a later phase, admins will be tied to specific colleges.
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str | None] = mapped_column(String(100))
    document_category: Mapped[CollegeDocumentCategory] = mapped_column(
        Enum(
            CollegeDocumentCategory,
            name="college_document_category",
            values_callable=enum_values,
        ),
        default=CollegeDocumentCategory.OTHER,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CollegeDocumentChunk(Base):
    """Chunks for CollegeGPT — separate table from subject doc chunks."""

    __tablename__ = "college_document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    college_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("college_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    compressed_text: Mapped[bytes | None] = mapped_column(LargeBinary)
    codebook: Mapped[dict | None] = mapped_column(JSON)
    compression_ratio: Mapped[float | None] = mapped_column(Numeric(5, 2))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnnouncementTarget(str, enum.Enum):
    ALL = "all"
    SUBJECT = "subject"
    COLLEGE = "college"


class Announcement(Base):
    """Teacher/admin announcements."""

    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[AnnouncementTarget] = mapped_column(
        Enum(AnnouncementTarget, name="announcement_target", values_callable=enum_values),
        default=AnnouncementTarget.ALL,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
