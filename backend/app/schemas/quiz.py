"""Pydantic schemas for the Quiz Engine (Phase 11, F3)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DifficultyLiteral = Literal["easy", "medium", "hard"]
QuestionTypeLiteral = Literal["mcq", "short_answer"]
QuizModeLiteral = Literal["practice", "test"]
CIEComponentLiteral = Literal["quiz_1", "quiz_2", "test_1", "test_2"]


# ── Question schemas ──

class QuestionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_index: int
    question_text: str
    question_type: QuestionTypeLiteral
    options: list[str] | None = None
    difficulty: DifficultyLiteral
    topic: str | None = None
    marks: int = 1
    co: str | None = None
    bloom: str | None = None


class QuestionStudentView(QuestionBase):
    """What students see while taking a quiz — answers and explanations are hidden."""

    pass


class QuestionTeacherView(QuestionBase):
    """Full question record for teachers and post-submission review."""

    correct_answer: str
    explanation: str | None = None


# ── Quiz schemas ──

class QuizBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    document_id: uuid.UUID | None
    created_by_id: uuid.UUID
    title: str
    description: str | None = None
    difficulty: DifficultyLiteral
    time_limit_minutes: int | None = None
    is_published: bool
    is_ai_generated: bool
    created_at: datetime
    question_count: int = 0
    attempt_count: int = 0
    avg_score: float | None = None
    # Practice/test mode + proctoring (Phase 4)
    mode: QuizModeLiteral = "practice"
    max_attempts: int = 0
    requires_proctoring: bool = False
    available_from: datetime | None = None
    available_until: datetime | None = None
    cie_component: CIEComponentLiteral | None = None
    total_marks: int | None = None
    attempts_used: int = 0
    can_attempt: bool = True


class QuizResponse(QuizBase):
    """Quiz summary used in list views."""

    subject_code: str | None = None
    subject_name: str | None = None


class QuizForStudent(QuizResponse):
    """Quiz returned to students — questions don't include correct answers."""

    questions: list[QuestionStudentView] = []


class QuizForTeacher(QuizResponse):
    """Full quiz returned to teachers / admins (with answers + explanations)."""

    questions: list[QuestionTeacherView] = []


# ── Quiz generation ──

class QuizGenerateRequest(BaseModel):
    subject_id: uuid.UUID
    document_id: uuid.UUID | None = None
    topic_hint: str | None = Field(None, max_length=255)
    num_questions: int = Field(5, ge=3, le=20)
    difficulty: DifficultyLiteral = "medium"
    mode: QuizModeLiteral = "practice"
    total_marks_target: int | None = Field(None, ge=1, le=200)
    cie_component: CIEComponentLiteral | None = None
    requires_proctoring: bool | None = None
    time_limit_minutes: int | None = Field(None, ge=1, le=300)


# ── Quiz updates ──

class QuestionUpdate(BaseModel):
    id: uuid.UUID | None = None  # None = new question
    question_text: str
    question_type: QuestionTypeLiteral = "mcq"
    options: list[str] | None = None
    correct_answer: str
    explanation: str | None = None
    difficulty: DifficultyLiteral = "medium"
    topic: str | None = None
    order_index: int = 0
    marks: int = 1
    co: str | None = None
    bloom: str | None = None


class QuizUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: DifficultyLiteral | None = None
    time_limit_minutes: int | None = None
    is_published: bool | None = None
    questions: list[QuestionUpdate] | None = None
    mode: QuizModeLiteral | None = None
    max_attempts: int | None = None
    requires_proctoring: bool | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    cie_component: CIEComponentLiteral | None = None


# ── Attempts ──

class QuestionAnswer(BaseModel):
    question_id: uuid.UUID
    student_answer: str


class ProctorSummary(BaseModel):
    tab_switch_count: int = 0
    fullscreen_exits: int = 0
    copy_paste_attempts: int = 0
    face_absent_seconds: int = 0
    face_multiple_seconds: int = 0
    auto_submitted: bool = False


class QuizAttemptCreate(BaseModel):
    answers: list[QuestionAnswer] = Field(default_factory=list)
    time_taken_seconds: int | None = None
    started_attempt_id: uuid.UUID | None = None
    proctor: ProctorSummary | None = None
    violations: list[dict] | None = None


class GradedAnswer(BaseModel):
    question_id: uuid.UUID
    question_text: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    topic: str | None = None
    difficulty: DifficultyLiteral
    explanation: str | None = None
    marks_awarded: float = 0
    marks_possible: float = 0
    co: str | None = None


class COAttainmentRow(BaseModel):
    co: str
    obtained: float
    possible: float
    pct: float


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    student_id: uuid.UUID
    score: float
    total_questions: int
    correct_count: int
    time_taken_seconds: int | None = None
    completed_at: datetime
    graded_answers: list[GradedAnswer] = []
    weak_topics: list[str] = []
    next_difficulty_recommendation: DifficultyLiteral | None = None
    mode: QuizModeLiteral = "practice"
    marks_obtained: float | None = None
    marks_possible: float | None = None
    is_proctored: bool = False
    auto_submitted: bool = False
    co_attainment: list[COAttainmentRow] = []


class StartAttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    started_at: datetime
    server_now: datetime
    time_limit_seconds: int | None = None
    requires_proctoring: bool = False
    mode: QuizModeLiteral = "practice"


class ProctorEventIn(BaseModel):
    type: Literal[
        "tab_switch", "blur", "fullscreen_exit", "copy", "paste", "contextmenu",
        "face_absent", "face_multiple", "resume", "devtools",
    ]
    seconds: float | None = None
    detail: dict | None = None


class ProctorReportRow(BaseModel):
    attempt_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    marks_obtained: float | None = None
    marks_possible: float | None = None
    score: float
    tab_switch_count: int = 0
    fullscreen_exits: int = 0
    copy_paste_attempts: int = 0
    face_absent_seconds: int = 0
    face_multiple_seconds: int = 0
    auto_submitted: bool = False
    violations: list[dict] = []
    completed_at: datetime


class ProctorReport(BaseModel):
    quiz_id: uuid.UUID
    quiz_title: str
    rows: list[ProctorReportRow] = []


class AttemptHistoryRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    subject_code: str
    subject_name: str
    score: float
    total_questions: int
    correct_count: int
    time_taken_seconds: int | None
    difficulty: DifficultyLiteral
    completed_at: datetime


class WeakAreaResponse(BaseModel):
    topic: str
    subject_code: str | None = None
    subject_name: str | None = None
    score_percent: float
    attempts_count: int
    suggestion: str
