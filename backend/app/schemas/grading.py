"""Pydantic schemas for the AI auto-grader + grading domain."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LeniencyLiteral = Literal["strict", "moderate", "lenient"]
ExamKindLiteral = Literal["quiz", "test", "experiential", "lab", "see"]
ExamPartLiteral = Literal["theory", "lab"]
SchemeStatusLiteral = Literal["pending", "parsing", "review", "ready", "failed"]
AnswerSheetStatusLiteral = Literal["uploaded", "ocr", "graded", "review", "finalized", "failed"]


# ── Course outcomes ──────────────────────────────────────────────────────────
class CourseOutcomeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=8)
    description: str | None = None
    order_index: int = 0


class CourseOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    description: str | None = None
    order_index: int = 0


# ── Grade config ─────────────────────────────────────────────────────────────
class ComponentDef(BaseModel):
    key: str
    label: str
    part: ExamPartLiteral = "theory"
    max: float
    kind: ExamKindLiteral = "test"


class GradeConfigUpdate(BaseModel):
    components: list[ComponentDef] | None = None
    cie_min_pct: float | None = Field(None, ge=0, le=100)
    see_min_pct: float | None = Field(None, ge=0, le=100)
    aggregate_min_pct: float | None = Field(None, ge=0, le=100)
    cie_lab_min_pct: float | None = Field(None, ge=0, le=100)
    see_lab_min_pct: float | None = Field(None, ge=0, le=100)
    gate_lab_separately: bool | None = None
    grade_bands: list | None = None


class GradeConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    subject_id: uuid.UUID
    components: list | None = None
    cie_min_pct: float
    see_min_pct: float
    aggregate_min_pct: float
    cie_lab_min_pct: float | None = None
    see_lab_min_pct: float | None = None
    gate_lab_separately: bool = False
    grade_bands: list | None = None


# ── Exam questions / scheme ──────────────────────────────────────────────────
class ExamQuestionBase(BaseModel):
    label: str = Field(..., max_length=20)
    parent_label: str | None = Field(None, max_length=20)
    part: ExamPartLiteral = "theory"
    question_text: str
    model_answer: str | None = None
    max_marks: float = Field(0, ge=0)
    co: str | None = Field(None, max_length=8)
    bloom: str | None = Field(None, max_length=4)
    order_index: int = 0


class ExamQuestionCreate(ExamQuestionBase):
    pass


class ExamQuestionUpdate(BaseModel):
    label: str | None = None
    parent_label: str | None = None
    part: ExamPartLiteral | None = None
    question_text: str | None = None
    model_answer: str | None = None
    max_marks: float | None = Field(None, ge=0)
    co: str | None = None
    bloom: str | None = None
    order_index: int | None = None


class ExamQuestionResponse(ExamQuestionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


# ── Exam ─────────────────────────────────────────────────────────────────────
class ExamCreate(BaseModel):
    subject_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    kind: ExamKindLiteral = "test"
    part: ExamPartLiteral = "theory"
    component_key: str | None = Field(None, max_length=50)
    sequence: int | None = None
    max_marks: float = Field(0, ge=0)


class ExamUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    component_key: str | None = None
    sequence: int | None = None
    max_marks: float | None = Field(None, ge=0)
    co_mark_grid: dict | None = None
    leniency: LeniencyLiteral | None = None
    custom_rules: str | None = None
    ignore_spelling: bool | None = None
    award_partial_method: bool | None = None
    confidence_review_threshold: float | None = Field(None, ge=0, le=1)
    ocr_review_threshold: float | None = Field(None, ge=0, le=1)
    is_published: bool | None = None


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    kind: ExamKindLiteral
    part: ExamPartLiteral
    component_key: str | None = None
    sequence: int | None = None
    max_marks: float
    co_mark_grid: dict | None = None
    scheme_document_id: uuid.UUID | None = None
    scheme_status: SchemeStatusLiteral
    quiz_id: uuid.UUID | None = None
    leniency: LeniencyLiteral
    custom_rules: str | None = None
    ignore_spelling: bool
    award_partial_method: bool
    confidence_review_threshold: float
    ocr_review_threshold: float
    is_published: bool
    created_at: datetime
    # populated by the service
    question_count: int = 0
    sheet_count: int = 0
    graded_count: int = 0
    review_count: int = 0


class SchemeResponse(BaseModel):
    exam: ExamResponse
    questions: list[ExamQuestionResponse] = []
    course_outcomes: list[CourseOutcomeResponse] = []
    co_mark_grid: dict | None = None


# ── Answer sheets + grades ───────────────────────────────────────────────────
class AnswerSheetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    exam_id: uuid.UUID
    student_id: uuid.UUID | None = None
    status: AnswerSheetStatusLiteral
    page_count: int = 0
    detected_usn: str | None = None
    detected_name: str | None = None
    match_confidence: float | None = None
    match_source: str | None = None
    is_match_confirmed: bool = False
    total_awarded: float | None = None
    total_max: float | None = None
    needs_review_count: int = 0
    error_detail: str | None = None
    # hydrated by the service
    matched_student_name: str | None = None
    matched_student_usn: str | None = None


class QuestionGradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    exam_question_id: uuid.UUID
    label: str | None = None
    question_text: str | None = None
    model_answer: str | None = None
    extracted_answer: str | None = None
    awarded_marks: float
    max_marks: float
    effective_marks: float
    co: str | None = None
    confidence: float | None = None
    ocr_confidence: float | None = None
    rationale: str | None = None
    needs_review: bool
    is_overridden: bool


class AnswerSheetDetail(AnswerSheetSummary):
    page_files: list[str] = []
    grades: list[QuestionGradeResponse] = []


class QuestionGradeOverride(BaseModel):
    teacher_marks: float = Field(..., ge=0)
    teacher_note: str | None = None


class MatchUpdate(BaseModel):
    student_id: uuid.UUID | None = None  # None clears the match


class ReviewQueueItem(BaseModel):
    answer_sheet_id: uuid.UUID
    question_grade_id: uuid.UUID
    student_name: str | None = None
    label: str | None = None
    extracted_answer: str | None = None
    awarded_marks: float
    max_marks: float
    confidence: float | None = None
    rationale: str | None = None


# ── CO attainment + results ──────────────────────────────────────────────────
class COAttainmentRow(BaseModel):
    co: str
    obtained: float
    max: float
    pct: float


class ExamAttainmentResponse(BaseModel):
    exam_id: uuid.UUID
    total_obtained: float
    total_max: float
    total_pct: float
    per_co: list[COAttainmentRow] = []
    graded_students: int = 0


class ExamResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    exam_id: uuid.UUID
    student_id: uuid.UUID
    total_obtained: float
    total_max: float
    percentage: float
    per_co: dict | None = None
    source: Literal["ai", "manual", "quiz"]
    is_teacher_approved: bool
    finalized: bool


class ManualResultEntry(BaseModel):
    student_id: uuid.UUID
    total_obtained: float = Field(..., ge=0)
    per_co: dict | None = None


class BulkManualResults(BaseModel):
    results: list[ManualResultEntry]


class CoverScanResult(BaseModel):
    """One scanned answer-booklet cover page: extracted marks + roster match."""
    detected_usn: str | None = None
    detected_name: str | None = None
    student_id: uuid.UUID | None = None
    matched_student_name: str | None = None
    match_confidence: float | None = None
    total_obtained: float = 0
    total_max: float = 0
    per_co: dict | None = None
    saved: bool = False
    message: str | None = None
