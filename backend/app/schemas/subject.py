"""Pydantic schemas for subject endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SubjectCategoryLiteral = Literal["theory", "theory_practice", "practical", "project", "audit"]


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
    # ── Grading config (Handbook §4) ──
    category: SubjectCategoryLiteral = "theory"
    credits: int = Field(0, ge=0, le=30)
    cie_max: int = Field(100, ge=1)
    see_max: int = Field(100, ge=1)
    has_lab_split: bool = False
    cie_theory_max: int | None = Field(None, ge=0)
    cie_lab_max: int | None = Field(None, ge=0)
    see_theory_max: int | None = Field(None, ge=0)
    see_lab_max: int | None = Field(None, ge=0)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=500)
    semester: int | None = Field(None, ge=1, le=8)
    branch: str | None = Field(None, max_length=100)
    category: SubjectCategoryLiteral | None = None
    credits: int | None = Field(None, ge=0, le=30)
    cie_max: int | None = Field(None, ge=1)
    see_max: int | None = Field(None, ge=1)
    has_lab_split: bool | None = None
    cie_theory_max: int | None = Field(None, ge=0)
    cie_lab_max: int | None = Field(None, ge=0)
    see_theory_max: int | None = Field(None, ge=0)
    see_lab_max: int | None = Field(None, ge=0)


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
    category: SubjectCategoryLiteral = "theory"
    credits: int = 0
    cie_max: int = 100
    see_max: int = 100
    has_lab_split: bool = False
    cie_theory_max: int | None = None
    cie_lab_max: int | None = None
    see_theory_max: int | None = None
    see_lab_max: int | None = None
    created_at: datetime

    # Computed counts (populated by the service layer)
    document_count: int = 0
    quiz_count: int = 0
    student_count: int = 0
