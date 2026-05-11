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


# ─────────────────────────────────────────────────────────────────
# Knowledge Editor — admin-only chunk CRUD + AI-mediated suggestions
# ─────────────────────────────────────────────────────────────────


class ChunkUpdate(BaseModel):
    """PATCH body — rewrite a single chunk's text. Re-embeds + recompresses
    server-side; the response is the updated `CollegeDocumentChunkPreview`."""

    chunk_text: str = Field(..., min_length=10, max_length=20_000)


class ChunkCreate(BaseModel):
    """POST body — append a new chunk to a college document. If `chunk_index`
    is omitted the server assigns `max(existing_index) + 1`."""

    chunk_text: str = Field(..., min_length=10, max_length=20_000)
    chunk_index: int | None = Field(default=None, ge=0)


class KnowledgeSuggestRequest(BaseModel):
    """POST /suggest body — admin types a natural-language update."""

    statement: str = Field(..., min_length=4, max_length=2000)
    hint_category: CollegeDocumentCategoryLiteral | None = None


class SuggestionCandidate(BaseModel):
    """A doc the admin can target when no existing chunk matches."""

    document_id: uuid.UUID
    document_title: str
    document_category: CollegeDocumentCategoryLiteral
    similarity: float


class KnowledgeSuggestion(BaseModel):
    """Response from POST /suggest.

    `kind == "update_existing"` means we found a chunk above the similarity
    threshold; the UI shows a diff of `current_chunk_text` vs
    `proposed_chunk_text` and the Apply button calls PATCH.

    `kind == "create_new"` means nothing matched; the UI shows the proposed
    text + a dropdown of `candidate_documents` so the admin can pick which
    doc to append to.
    """

    kind: Literal["update_existing", "create_new"]
    similarity: float
    document_id: uuid.UUID | None = None
    document_title: str | None = None
    document_category: CollegeDocumentCategoryLiteral | None = None
    chunk_id: uuid.UUID | None = None
    chunk_index: int | None = None
    current_chunk_text: str | None = None
    proposed_chunk_text: str
    candidate_documents: list[SuggestionCandidate] = []
