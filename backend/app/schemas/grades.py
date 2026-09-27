"""Pydantic schemas for student transcript + teacher class grade overview."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.grading import COAttainmentRow


class SubjectGradeRow(BaseModel):
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    credits: int
    semester: int | None = None
    cie_obtained: float | None = None
    cie_max: float | None = None
    see_obtained: float | None = None
    see_max: float | None = None
    cie_50: float | None = None
    see_50: float | None = None
    final_score: float | None = None
    final_rounded: int | None = None
    letter_grade: str | None = None
    grade_point: int | None = None
    passed: bool = False
    gate_failed: str = "none"
    is_transitional: bool = False
    finalized: bool = False
    per_co: list[COAttainmentRow] = []


class SemesterGrades(BaseModel):
    semester: int
    sgpa: float
    total_credits: int
    subjects: list[SubjectGradeRow] = []


class TranscriptResponse(BaseModel):
    cgpa: float
    percentage: float  # CGPA × 10
    semesters: list[SemesterGrades] = []


class ClassGradeRow(BaseModel):
    student_id: uuid.UUID
    student_name: str
    usn: str | None = None
    cie_obtained: float | None = None
    cie_max: float | None = None
    see_obtained: float | None = None
    final_score: float | None = None
    letter_grade: str | None = None
    grade_point: int | None = None
    passed: bool = False
    finalized: bool = False


class ClassGradeOverview(BaseModel):
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    students: list[ClassGradeRow] = []
    co_attainment: list[COAttainmentRow] = []
