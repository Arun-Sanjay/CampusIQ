"""Pydantic schemas for the Resume Builder (Phase 14, F6)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResumeTemplateLiteral = Literal["technical", "product", "research", "general"]


def _to_str(value) -> str:
    """Coerce any scalar (int / float / None / str) into a string.

    Claude frequently returns years / CGPA / phone numbers as ints or floats,
    even when the schema says string. Rather than rejecting the whole patch,
    we normalise these into strings at validation time.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        # Drop trailing .0 on whole-number floats (2024.0 → "2024")
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


# ── Structured resume content ──

class ResumePersonal(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    # Optional. Stored as a `data:image/...;base64,...` URL so the photo
    # travels with the rest of the resume content (no separate uploads
    # endpoint, no extra cleanup). The frontend resizes images down to
    # ~400px on its longest edge before storing, keeping payload sane.
    photo_url: str = ""

    @field_validator("name", "email", "phone", "location", "linkedin", "github", "portfolio", "photo_url", mode="before")
    @classmethod
    def _coerce_personal(cls, v):
        return _to_str(v)


class ResumeEducation(BaseModel):
    institution: str = ""
    degree: str = ""
    branch: str = ""
    start_year: str = ""
    end_year: str = ""
    cgpa: str = ""
    highlights: list[str] = []

    @field_validator(
        "institution", "degree", "branch", "start_year", "end_year", "cgpa", mode="before"
    )
    @classmethod
    def _coerce_edu(cls, v):
        return _to_str(v)


class ResumeExperience(BaseModel):
    company: str = ""
    role: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = []

    @field_validator(
        "company", "role", "location", "start_date", "end_date", mode="before"
    )
    @classmethod
    def _coerce_exp(cls, v):
        return _to_str(v)


class ResumeProject(BaseModel):
    name: str = ""
    description: str = ""
    tech: list[str] = []
    url: str = ""
    highlights: list[str] = []

    @field_validator("name", "description", "url", mode="before")
    @classmethod
    def _coerce_project(cls, v):
        return _to_str(v)


class ResumeContent(BaseModel):
    personal: ResumePersonal = ResumePersonal()
    summary: str = ""
    education: list[ResumeEducation] = []
    experience: list[ResumeExperience] = []
    projects: list[ResumeProject] = []
    skills: list[str] = []
    certifications: list[str] = []
    achievements: list[str] = []


# ── API request / response shapes ──

class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    template: ResumeTemplateLiteral
    content: ResumeContent
    ats_score: float | None = None
    last_job_description: str | None = None
    last_updated: datetime
    created_at: datetime


class ResumeContentUpdate(BaseModel):
    """Manual edit — replaces the full content blob."""

    template: ResumeTemplateLiteral | None = None
    content: ResumeContent


class ResumeChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ResumeChatResponse(BaseModel):
    ai_message: str
    content: ResumeContent
    patch_applied: bool


class ATSScoreRequest(BaseModel):
    job_description: str = Field(..., min_length=20, max_length=8000)


class ATSScoreResponse(BaseModel):
    score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    suggestions: list[str]


class GitHubImportRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    top_n: int = Field(5, ge=1, le=10)


class GitHubProjectImport(BaseModel):
    name: str
    description: str
    tech: list[str]
    url: str
    stars: int


class GitHubImportResponse(BaseModel):
    username: str
    imported_count: int
    projects: list[GitHubProjectImport]
    content: ResumeContent


class ResumeChatHistoryItem(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ResumeChatHistory(BaseModel):
    messages: list[ResumeChatHistoryItem]
