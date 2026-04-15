"""Pydantic schemas for subject endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubjectBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique subject code, e.g. 'CS341'")
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


class SubjectResponse(SubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    teacher_id: uuid.UUID
    college_id: uuid.UUID | None = None
    created_at: datetime

    # Computed counts (populated by the service layer)
    document_count: int = 0
    quiz_count: int = 0
    student_count: int = 0
