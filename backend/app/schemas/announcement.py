"""Pydantic schemas for announcements (Phase 13)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnnouncementTargetLiteral = Literal["all", "subject", "college"]


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=5000)
    target: AnnouncementTargetLiteral = "all"
    subject_id: uuid.UUID | None = None  # required if target == 'subject'


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    body: str | None = Field(None, max_length=5000)


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str | None = None
    subject_id: uuid.UUID | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    college_id: uuid.UUID | None = None
    title: str
    body: str
    target: AnnouncementTargetLiteral
    created_at: datetime
