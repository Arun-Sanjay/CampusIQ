"""Pydantic schemas for the peer Doubt Community (Phase 17, F4)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DoubtCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    subject_id: uuid.UUID | None = None


class DoubtAnswerCreate(BaseModel):
    answer_text: str = Field(..., min_length=1, max_length=5000)


class DoubtAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doubt_id: uuid.UUID
    answered_by_id: uuid.UUID | None
    answered_by_name: str | None = None
    answer_text: str
    is_ai_generated: bool
    is_accepted: bool
    upvote_count: int
    created_at: datetime


class DoubtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str | None = None
    subject_id: uuid.UUID | None = None
    subject_code: str | None = None
    title: str
    body: str
    tags: list[str]
    is_resolved: bool
    upvote_count: int
    view_count: int
    answer_count: int
    has_ai_answer: bool
    created_at: datetime


class DoubtDetailResponse(DoubtResponse):
    answers: list[DoubtAnswerResponse]
