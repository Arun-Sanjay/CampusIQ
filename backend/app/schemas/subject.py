"""Pydantic schemas for subject endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubjectBase(BaseModel):
    # Student-created personal subjects don't require a unique course code —
    # the backend auto-generates one. Teachers must still supply a real code.
    code: str | None = Field(
        None,
        min_length=2,
        max_length=50,
        description="Unique subject code, e.g. 'CS341'. Optional for student-created personal subjects.",
    )
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=500)
    semester: int | None = Field(None, ge=1, le=8)
    branch: str | None = Field(None, max_length=100)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=500)
    semester: int | None = Field(None, ge=1, le=8)
    branch: str | None = Field(None, max_length=100)


class SubjectResponse(BaseModel):
    """Subject row returned by the API. `code` is always populated server-side."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    teacher_id: uuid.UUID
    # NULL = public teacher subject. Set = student's personal notebook.
    owner_student_id: uuid.UUID | None = None
    college_id: uuid.UUID | None = None
    code: str
    name: str
    description: str | None = None
    semester: int | None = None
    branch: str | None = None
    created_at: datetime

    # Computed counts (populated by the service layer)
    document_count: int = 0
    quiz_count: int = 0
    student_count: int = 0
