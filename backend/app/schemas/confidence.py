"""Pydantic schemas for Confidence Coach (Phase 20, F11)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceSessionCreate(BaseModel):
    """Form fields posted alongside the audio blob by the frontend.

    The audio itself rides as a multipart field, not part of this schema.
    `eye_contact_pct` and `posture_pct` come from the browser's MediaPipe
    Face Mesh + Pose pipeline — we store the client-side aggregate so the
    backend doesn't need to re-run ML on every recording.
    """

    prompt: str = Field(..., min_length=1, max_length=600)
    duration_seconds: int = Field(..., ge=1, le=600)
    eye_contact_pct: float | None = Field(None, ge=0, le=100)
    posture_pct: float | None = Field(None, ge=0, le=100)


class ConfidenceSessionResponse(BaseModel):
    """Analysed session returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    transcript: str | None
    # All scores are 0-100. None means the metric wasn't available
    # (e.g. missing API key, no transcript, etc.).
    eye_contact_score: float | None
    posture_score: float | None
    filler_word_count: int | None
    speaking_pace_wpm: int | None
    clarity_score: float | None
    overall_confidence_score: float | None
    detailed_feedback: dict[str, Any] | None
    recorded_at: datetime


class ConfidenceMetric(BaseModel):
    """Single metric row for the timeline chart."""

    recorded_at: datetime
    overall_confidence_score: float | None
    eye_contact_score: float | None
    posture_score: float | None
    clarity_score: float | None
    speaking_pace_wpm: int | None
    filler_word_count: int | None


class ConfidenceTimelineResponse(BaseModel):
    sessions: list[ConfidenceMetric]
    latest: ConfidenceSessionResponse | None
    # Prompts the UI can suggest for the next recording
    next_prompts: list[str]
