"""Pydantic schemas for per-subject enrollment (teacher roster)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EnrolledStudent(BaseModel):
    student_id: uuid.UUID
    username: str
    full_name: str
    email: str
    branch: str | None = None
    semester: int | None = None
    enrolled_at: datetime


class SubjectRoster(BaseModel):
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    students: list[EnrolledStudent]


class EnrollRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)


class TeacherSubjectCount(BaseModel):
    subject_id: uuid.UUID
    code: str
    name: str
    student_count: int
