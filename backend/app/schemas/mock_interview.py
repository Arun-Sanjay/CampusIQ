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


class VoiceCapabilitiesResponse(BaseModel):
    """Reports to the UI which voice APIs are currently configured.

    The frontend calls this at setup so we can grey out voice mode when
    the server can't run it, instead of letting the student start and then
    getting a 503 back. `agent_available` gates the live conversational
    voice interview (the primary voice path)."""
    asr_available: bool       # Scribe / Whisper is reachable
    tts_available: bool       # ElevenLabs TTS is reachable
    agent_available: bool     # ElevenLabs Conversational AI agent is configured
    voice_by_round: dict[int, str]  # round number → voice ID


# ── Live voice mode — ElevenLabs Conversational AI (Agents) ──


class LiveRoundStartResponse(BaseModel):
    """Everything the browser needs to open the round's live agent session.

    The signed URL keeps the `xi-api-key` server-side; the override fields are
    passed straight into `conversation.startSession({ signedUrl, overrides })`
    so a single shared agent becomes the right interviewer for this round."""
    round_number: int
    round_name: str
    signed_url: str
    voice_id: str
    language: str = "en"
    system_prompt: str   # → overrides.agent.prompt.prompt
    first_message: str   # → overrides.agent.firstMessage


class LiveRoundFinalizeRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=200)


class LiveRoundFinalizeResponse(BaseModel):
    """Returned immediately after a round ends. Grading runs in the background
    (poll `GET /interviews/{id}` until the round's `avg_score` appears, and
    until `status == "completed"` after the final round)."""
    round_number: int
    grading: bool                       # true → a background grade is in flight
    interview_completing: bool          # true → final round; debrief is being generated
    session: InterviewSessionResponse


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
