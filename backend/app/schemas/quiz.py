"""Pydantic schemas for the Quiz Engine (Phase 11, F3)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DifficultyLiteral = Literal["easy", "medium", "hard"]
QuestionTypeLiteral = Literal["mcq", "short_answer"]


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


class QuizUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: DifficultyLiteral | None = None
    time_limit_minutes: int | None = None
    is_published: bool | None = None
    questions: list[QuestionUpdate] | None = None


# ── Attempts ──

class QuestionAnswer(BaseModel):
    question_id: uuid.UUID
    student_answer: str


class QuizAttemptCreate(BaseModel):
    answers: list[QuestionAnswer] = Field(..., min_length=1)
    time_taken_seconds: int | None = None


class GradedAnswer(BaseModel):
    question_id: uuid.UUID
    question_text: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    topic: str | None = None
    difficulty: DifficultyLiteral
    explanation: str | None = None


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
