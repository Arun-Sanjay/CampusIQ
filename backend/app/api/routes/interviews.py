"""Mock Interview endpoints (Phase 16 text mode, Phase 20 voice mode)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.deps import ClaudeRateLimited, CurrentUser, DbSession
from app.models.placement import InterviewMode, InterviewPersona
from app.schemas.mock_interview import (
    InterviewMessageRequest,
    InterviewSessionListRow,
    InterviewSessionResponse,
    InterviewStartRequest,
    InterviewTurnResponse,
    LiveRoundFinalizeRequest,
    LiveRoundFinalizeResponse,
    LiveRoundStartResponse,
    VoiceCapabilitiesResponse,
)
from app.services import elevenlabs_agent, mock_interview, speech

router = APIRouter()


def _parse_persona(value: str) -> InterviewPersona:
    try:
        return InterviewPersona(value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid persona: {value}") from e


def _parse_mode(value: str) -> InterviewMode:
    try:
        return InterviewMode(value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {value}") from e


@router.post(
    "/",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new 5-round mock interview session",
)
def start_interview(
    data: InterviewStartRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> InterviewSessionResponse:
    session = mock_interview.create_session(
        db,
        current_user,
        company_target=data.company_target,
        role_target=data.role_target,
        interviewer_persona=_parse_persona(data.interviewer_persona),
        mode=_parse_mode(data.mode),
    )
    return mock_interview._to_session_response(session)


@router.get(
    "/me",
    response_model=list[InterviewSessionListRow],
    summary="Student: list my mock interview sessions",
)
def list_my_sessions(
    db: DbSession, current_user: CurrentUser
) -> list[InterviewSessionListRow]:
    sessions = mock_interview.list_sessions_for_student(db, current_user)
    return [
        InterviewSessionListRow.model_validate(s, from_attributes=True)
        for s in sessions
    ]


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
    summary="Get a single interview session (transcript + scores)",
)
def get_interview(
    session_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> InterviewSessionResponse:
    return mock_interview.fetch_session(db, session_id, current_user)


@router.post(
    "/{session_id}/messages",
    response_model=InterviewTurnResponse,
    summary="Submit a candidate answer and get the interviewer's next turn",
)
def submit_message(
    session_id: uuid.UUID,
    data: InterviewMessageRequest,
    db: DbSession,
    current_user: ClaudeRateLimited,
) -> InterviewTurnResponse:
    result = mock_interview.student_turn(db, current_user, session_id, data.content)
    return InterviewTurnResponse(
        session=mock_interview._to_session_response(result.session),
        assistant_message=result.assistant_message,
        round_transitioned=result.round_transitioned,
        interview_completed=result.interview_completed,
    )


@router.post(
    "/{session_id}/end",
    response_model=InterviewSessionResponse,
    summary="Force-end the interview early and generate the debrief",
)
def end_interview(
    session_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> InterviewSessionResponse:
    session = mock_interview.end_session(db, session_id, current_user)
    return mock_interview._to_session_response(session)


# ═══════════════════════════════════════════════════════════════════
# Live voice mode — ElevenLabs Conversational AI (Agents)
# ═══════════════════════════════════════════════════════════════════
#
# Each round runs as a real-time spoken conversation handled by ElevenLabs in
# the browser (no per-turn server round-trip). The server only mints the signed
# URL to start a round and grades the finished transcript with Claude.


@router.get(
    "/voice/capabilities",
    response_model=VoiceCapabilitiesResponse,
    summary="Report which voice paths are available (live agent / ASR / TTS)",
)
def voice_capabilities() -> VoiceCapabilitiesResponse:
    return VoiceCapabilitiesResponse(
        asr_available=speech.is_asr_available(),
        tts_available=speech.is_tts_available(),
        agent_available=elevenlabs_agent.is_configured(),
        voice_by_round=speech.VOICE_BY_ROUND,
    )


@router.post(
    "/{session_id}/live/rounds/{round_number}/start",
    response_model=LiveRoundStartResponse,
    summary="Mint a signed ElevenLabs agent URL + per-round overrides for a live round",
)
def start_live_round(
    session_id: uuid.UUID,
    round_number: int,
    db: DbSession,
    current_user: CurrentUser,
) -> LiveRoundStartResponse:
    payload = mock_interview.start_live_round(
        db, current_user, session_id, round_number
    )
    return LiveRoundStartResponse(**payload)


@router.post(
    "/{session_id}/live/rounds/{round_number}/finalize",
    response_model=LiveRoundFinalizeResponse,
    summary="End a live round and grade its transcript in the background",
)
def finalize_live_round(
    session_id: uuid.UUID,
    round_number: int,
    data: LiveRoundFinalizeRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: ClaudeRateLimited,
) -> LiveRoundFinalizeResponse:
    session, grading, completing = mock_interview.finalize_live_round(
        db,
        current_user,
        session_id,
        round_number,
        data.conversation_id,
        background_tasks,
    )
    return LiveRoundFinalizeResponse(
        round_number=round_number,
        grading=grading,
        interview_completing=completing,
        session=mock_interview._to_session_response(session),
    )
