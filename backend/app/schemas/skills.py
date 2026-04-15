"""Pydantic schemas for the Adaptive Learning Engine (Phase 15)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SkillNodeResponse(BaseModel):
    name: str
    domain: str
    description: str
    difficulty_tier: int


class SkillEdgeResponse(BaseModel):
    from_skill: str
    to_skill: str
    base_weight_hours: float
    adjusted_weight_hours: float | None = None  # populated in dynamic responses
    domain: str | None = None


class CompanyProfile(BaseModel):
    id: uuid.UUID
    company: str
    role: str
    required_skills: list[str]
    preferred_skills: list[str]
    difficulty_tier: int


class MasteryItem(BaseModel):
    skill: str
    mastery: float


class MasterySnapshotResponse(BaseModel):
    declared_skills: list[str]
    quiz_topics: dict[str, float]
    per_skill: list[MasteryItem]


class GapBreakdownResponse(BaseModel):
    student_has: list[str]
    missing: list[str]
    present_count: int
    required_count: int
    coverage_percent: float
    gap_percent: float
    cosine_similarity: float


class PathEdge(BaseModel):
    from_skill: str
    to_skill: str
    weight: float


class SkillPathResult(BaseModel):
    target: str
    total_hours: float
    nodes: list[str]
    edges: list[PathEdge]
    reachable: bool


class MSTEdge(BaseModel):
    from_skill: str
    to_skill: str
    weight: float


class MSTResponse(BaseModel):
    nodes: list[str]
    edges: list[MSTEdge]
    total_weight: float


class KnapsackItemResponse(BaseModel):
    topic: str
    hours: float
    value: float
    reason: str
    included: bool


class KnapsackResponse(BaseModel):
    budget_hours: float
    total_hours: float
    total_value: float
    predicted_improvement_percent: float
    items: list[KnapsackItemResponse]


class AdaptivePlanRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=100)
    role: str | None = None
    available_hours: float = Field(..., ge=1, le=80)


class AdaptivePlanResponse(BaseModel):
    plan_id: uuid.UUID | None
    company: CompanyProfile
    mastery: MasterySnapshotResponse
    gap: GapBreakdownResponse
    paths: list[SkillPathResult]
    mst: MSTResponse
    knapsack: KnapsackResponse


class StudyOptimizerHistoryRow(BaseModel):
    id: uuid.UUID
    target_company: str | None
    target_role: str | None
    available_hours: float
    included_topics: list[dict]
    predicted_improvement: float
    actual_improvement: float | None
    created_at: datetime
