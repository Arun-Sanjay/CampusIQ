"""Pydantic schemas for Mock Interview Text Mode (Phase 16, F9)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InterviewModeLiteral = Literal["text", "voice"]
InterviewPersonaLiteral = Literal["friendly", "tough", "rapid_fire", "unpredictable"]
InterviewStatusLiteral = Literal["in_progress", "completed", "abandoned"]

# Round numbers map to:
#   1 = HR / Behavioural
#   2 = Technical
#   3 = System Design
#   4 = Managerial
#   5 = Negotiation
ROUND_NAMES: dict[int, str] = {
    1: "HR / Behavioural",
    2: "Technical",
    3: "System Design",
    4: "Managerial",
    5: "Negotiation",
}


class InterviewStartRequest(BaseModel):
    company_target: str = Field(..., min_length=1, max_length=100)
    role_target: str = Field("SWE", max_length=100)
    interviewer_persona: InterviewPersonaLiteral = "friendly"
    mode: InterviewModeLiteral = "text"


class InterviewMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class InterviewTranscriptTurn(BaseModel):
    role: Literal["assistant", "user"]
    content: str
    round_number: int
    score: float | None = None          # per-answer score (user turns only)
    score_reason: str | None = None     # short rationale from the interviewer
    is_round_transition: bool = False   # assistant turn that opens a new round


class RoundSummary(BaseModel):
    round_number: int
    name: str
    questions_asked: int
    avg_score: float | None
    status: Literal["locked", "active", "completed"]


class InterviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_target: str | None
    role_target: str | None
    interviewer_persona: InterviewPersonaLiteral
    mode: InterviewModeLiteral
    current_round: int
    is_full_simulator: bool
    status: InterviewStatusLiteral
    overall_score: float | None
    started_at: datetime
    completed_at: datetime | None
    transcript: list[InterviewTranscriptTurn]
    round_summaries: list[RoundSummary]
    feedback_report: dict | None = None


class InterviewTurnResponse(BaseModel):
    session: InterviewSessionResponse
    assistant_message: str
    round_transitioned: bool
    interview_completed: bool


class InterviewVoiceTurnResponse(BaseModel):
    """Voice-mode response — adds the Whisper transcription and (optional)
    ElevenLabs audio URL for the assistant's reply."""
    session: InterviewSessionResponse
    assistant_message: str
    round_transitioned: bool
    interview_completed: bool
    transcribed_text: str
    assistant_audio_url: str | None = None
    assistant_voice_id: str | None = None


class VoiceCapabilitiesResponse(BaseModel):
    """Reports to the UI which voice APIs are currently configured.

    The frontend calls this at setup so we can grey out voice mode when
    the server doesn't have the necessary keys, instead of letting the
    student record audio and then getting a 503 back."""
    asr_available: bool       # Whisper is reachable
    tts_available: bool       # ElevenLabs is reachable
    voice_by_round: dict[int, str]  # round number → voice ID


class InterviewSessionListRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_target: str | None
    role_target: str | None
    interviewer_persona: InterviewPersonaLiteral
    status: InterviewStatusLiteral
    overall_score: float | None
    started_at: datetime
    completed_at: datetime | None
