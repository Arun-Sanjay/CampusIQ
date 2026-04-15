"""Pydantic schemas for leaderboard / skill tree / profile (Phase 18)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TierLiteral = Literal["diamond", "platinum", "gold", "silver", "bronze"]
UnlockStateLiteral = Literal["locked", "unlocked", "mastered"]


# ── Leaderboard ──

class LeaderboardRowResponse(BaseModel):
    rank: int
    student_id: str
    name: str
    total_score: float
    academic: float
    skill: float
    interview: float
    placement: float
    tier: TierLiteral
    xp_total: int
    current_level: int
    is_current_user: bool


class LeaderboardResponse(BaseModel):
    rows: list[LeaderboardRowResponse]
    my_row: LeaderboardRowResponse | None = None
    total_students: int


# ── Skill Tree ──

class SkillNodeStateResponse(BaseModel):
    name: str
    domain: str
    description: str
    difficulty_tier: int
    mastery: float
    state: UnlockStateLiteral


class DomainProgressResponse(BaseModel):
    name: str
    total_skills: int
    mastered_count: int
    unlocked_count: int
    progress_percent: float
    skills: list[SkillNodeStateResponse]


class SkillTreeResponse(BaseModel):
    domains: list[DomainProgressResponse]
    mastered_count: int
    total_count: int
    overall_percent: float


# ── Profile ──

class BadgeResponse(BaseModel):
    id: str
    badge_type: str
    name: str
    description: str | None
    icon: str | None
    earned_at: str


class PublicProfileResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    role: str
    branch: str | None
    semester: int | None
    cgpa: float | None
    github_url: str | None
    linkedin_url: str | None
    skills: list[str]
    target_companies: list[str]
    target_role: str | None
    xp_total: int
    current_level: int
    streak_days: int
    campus_iq_score: float
    rank: int | None
    tier: TierLiteral
    academic_pillar: float
    skill_pillar: float
    interview_pillar: float
    placement_pillar: float
    badges: list[BadgeResponse]
    member_since: datetime


class ProfileUpdateRequest(BaseModel):
    branch: str | None = Field(None, max_length=100)
    semester: int | None = Field(None, ge=1, le=12)
    cgpa: float | None = Field(None, ge=0, le=10)
    github_url: str | None = Field(None, max_length=500)
    linkedin_url: str | None = Field(None, max_length=500)
    skills: list[str] | None = None
    target_companies: list[str] | None = None
    target_role: str | None = Field(None, max_length=255)
