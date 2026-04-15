"""Pydantic schemas for college document endpoints (Phase 10, F5)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import CompressionStats

CollegeDocumentCategoryLiteral = Literal[
    "handbook",
    "timetable",
    "placement_record",
    "faculty_list",
    "hostel_rules",
    "other",
]

CollegeDocumentStatusLiteral = Literal["pending", "processing", "ready", "failed"]


class CollegeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    college_id: uuid.UUID | None
    uploaded_by_id: uuid.UUID
    title: str
    file_name: str
    file_type: str | None = None
    document_category: CollegeDocumentCategoryLiteral
    summary: str | None = None
    processing_status: CollegeDocumentStatusLiteral
    created_at: datetime
    compression_stats: CompressionStats | None = None


class CollegeDocumentChunkPreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    chunk_text: str
    compression_ratio: float | None = None
    compressed_bytes: int | None = None
    original_bytes: int | None = None


class CollegeDocumentCreateMetadata(BaseModel):
    """Non-file fields sent as a multipart form alongside the file."""

    title: str | None = Field(None, max_length=255)
    document_category: CollegeDocumentCategoryLiteral = "other"
