"""Pydantic schemas for Job Tracker (Phase 17, F12)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobTypeLiteral = Literal["full_time", "internship", "contract", "part_time"]
ApplicationStatusLiteral = Literal[
    "saved",
    "applied",
    "oa_received",
    "interview_scheduled",
    "offer_received",
    "rejected",
]
JobListingSourceLiteral = Literal["admin_added", "student_added"]


class JobListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    requirements: str | None = None
    location: str | None = None
    job_type: JobTypeLiteral = "full_time"
    application_deadline: date | None = None


class JobListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company_name: str
    description: str | None
    requirements: str | None
    location: str | None
    job_type: JobTypeLiteral
    application_deadline: date | None
    source: JobListingSourceLiteral
    created_at: datetime
    fit_score: float | None = None  # computed per-student, attached at list time


class JobApplicationCreate(BaseModel):
    job_listing_id: uuid.UUID
    status: ApplicationStatusLiteral = "saved"
    notes: str | None = None


class JobApplicationUpdate(BaseModel):
    status: ApplicationStatusLiteral | None = None
    notes: str | None = None


class JobApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    job_listing_id: uuid.UUID
    status: ApplicationStatusLiteral
    fit_score: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    job: JobListingResponse


class JobBoardResponse(BaseModel):
    """Kanban-ready grouping of the student's applications by status."""

    saved: list[JobApplicationResponse]
    applied: list[JobApplicationResponse]
    oa_received: list[JobApplicationResponse]
    interview_scheduled: list[JobApplicationResponse]
    offer_received: list[JobApplicationResponse]
    rejected: list[JobApplicationResponse]
