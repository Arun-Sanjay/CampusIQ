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


# ── Teacher dashboard (Phase 4 wiring) ──

class TeacherStat(BaseModel):
    label: str
    value: str
    trend: float | None = None  # signed % change vs prior period (optional)


class RecentUploadRow(BaseModel):
    id: uuid.UUID
    name: str
    subject_code: str | None
    subject_name: str | None
    created_at: datetime
    status: Literal["pending", "processing", "ready", "failed"]


class TeacherDashboardResponse(BaseModel):
    teacher_id: uuid.UUID
    full_name: str
    department: str | None
    stats: list[TeacherStat]
    recent_uploads: list[RecentUploadRow]
    class_average: float | None
    students_total: int


# ── Admin dashboard (Phase 4 wiring) ──

class AdminStat(BaseModel):
    label: str
    value: str
    trend: float | None = None


class UserBreakdownRow(BaseModel):
    role: Literal["student", "teacher", "admin"]
    count: int


class PlatformActivityItem(BaseModel):
    text: str
    created_at: datetime


class PlatformHealth(BaseModel):
    api_response_ms: int
    storage_used_gb: float
    storage_quota_gb: float
    uptime_pct: float


class AdminDashboardResponse(BaseModel):
    stats: list[AdminStat]
    user_breakdown: list[UserBreakdownRow]
    recent_activity: list[PlatformActivityItem]
    platform_health: PlatformHealth


# ── Admin user list ──

class AdminUserRow(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Literal["student", "teacher", "admin"]
    is_active: bool
    branch: str | None = None
    semester: int | None = None
    department: str | None = None
    last_login: datetime | None = None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    items: list[AdminUserRow]


# ── Teacher: per-student detail ──

class StudentQuizScore(BaseModel):
    quiz_id: uuid.UUID
    label: str
    value: float
    completed_at: datetime


class StudentDetailResponse(BaseModel):
    student_id: uuid.UUID
    name: str
    branch: str | None
    semester: int | None
    quiz_scores: list[StudentQuizScore]
    weak_areas: list[str]
    xp_total: int
    streak_days: int
    community_contributions: int
