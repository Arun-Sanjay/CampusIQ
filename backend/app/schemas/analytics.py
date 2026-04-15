"""Pydantic schemas for teacher analytics (Phase 13)."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

TrendLiteral = Literal["up", "down", "flat"]


class AnalyticsHeadline(BaseModel):
    class_average: float | None
    completion_rate: float | None      # % of (students × published quizzes) actually attempted
    most_missed_topic: str | None
    active_students: int


class WeakTopicRow(BaseModel):
    topic: str
    score_percent: float
    attempts: int
    subject_code: str | None = None


class ScoreBucket(BaseModel):
    label: str               # "0-19", "20-39", etc
    range_start: int
    range_end: int
    count: int


class StudentPerformanceRow(BaseModel):
    student_id: uuid.UUID
    name: str
    quizzes_taken: int
    avg_score: float | None
    last_attempt_at: str | None
    trend: TrendLiteral
    weak_area: str | None


class ClassAnalytics(BaseModel):
    teacher_id: uuid.UUID
    subject_id: uuid.UUID | None
    headline: AnalyticsHeadline
    weak_topics: list[WeakTopicRow]
    score_distribution: list[ScoreBucket]
    student_performance: list[StudentPerformanceRow]
