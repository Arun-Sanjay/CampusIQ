"""Pydantic schemas for the Student Dashboard (Phase 12 + Phase 13)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.announcement import AnnouncementResponse

TaskPriorityLiteral = Literal["urgent", "high", "medium", "low"]
TaskKindLiteral = Literal["quiz", "retake", "weak_area", "daily_login"]


class XPProgress(BaseModel):
    xp_total: int
    current_level: int
    streak_days: int
    streak_multiplier: float
    xp_into_level: int             # XP earned past the start of the current level
    next_level_threshold: int      # cumulative XP at the start of the next level
    xp_to_next_level: int          # next_level_threshold - xp_total


class CampusIQScoreBreakdown(BaseModel):
    total: float
    academic: float
    skill: float
    interview: float
    placement: float
    last_calculated_at: datetime | None = None


class TaskItemResponse(BaseModel):
    title: str
    reason: str
    priority: TaskPriorityLiteral
    score: float
    kind: TaskKindLiteral
    action_url: str | None = None
    quiz_id: uuid.UUID | None = None
    subject_code: str | None = None


class ActivityItem(BaseModel):
    id: uuid.UUID
    event_type: str
    xp_earned: int
    created_at: datetime
    title: str        # human-readable summary built server-side


class DashboardStats(BaseModel):
    quizzes_attempted: int
    quizzes_passed: int
    avg_quiz_score: float | None
    weekly_rank: int | None = None  # filled in by leaderboard later


class DashboardResponse(BaseModel):
    student_id: uuid.UUID
    full_name: str
    semester: int | None
    branch: str | None
    xp: XPProgress
    score: CampusIQScoreBreakdown
    stats: DashboardStats
    tasks: list[TaskItemResponse]
    recent_activity: list[ActivityItem]
    announcements: list[AnnouncementResponse] = []
