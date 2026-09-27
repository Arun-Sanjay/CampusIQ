"""Mock Interview Text Mode state machine (Phase 16, F9).

Pure Python state machine — no LangGraph. Each interview session walks
through 5 rounds with 3 questions per round, driven by one of 4 personas.
Every user answer is scored 0-10 by the same Claude call that generates
the interviewer's next turn, so we get scoring + next-question in a single
round-trip. Once all 5 rounds complete, a dedicated debrief generator runs
to produce the overall score + improvement suggestions.

State layout (stored in `mock_interview_sessions.state` JSON):
    {
        "questions_per_round": 3,
        "round_question_counts": {1: 2, 2: 0, ...},   # how many ?'s asked per round
        "round_scores_sum":     {1: 14.5, ...},
        "round_scores_count":   {1: 2, ...},
        "awaiting_answer": true                       # true iff last turn was assistant question
    }

Transcript layout (stored in `mock_interview_sessions.transcript` JSON):
    list of {
        "role": "assistant" | "user",
        "content": "...",
        "round_number": int,
        "score": float | null,
        "score_reason": string | null,
        "is_round_transition": bool
    }
"""
from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.gamification import XPEventType
from app.models.placement import (
    InterviewMode,
    InterviewPersona,
    InterviewStatus,
    MockInterviewSession,
)
from app.models.user import User, UserRole
from app.schemas.mock_interview import (
    InterviewSessionResponse,
    InterviewTranscriptTurn,
    RoundSummary,
    ROUND_NAMES,
)
from app.services import claude_client, speech, xp

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Config
# ════════════════════════════════════════════════════════════════

QUESTIONS_PER_ROUND = 2  # keeps the full 5-round run to ~10 turns
TOTAL_ROUNDS = 5

# Weighted blend for the final overall score (matches the job-market
# importance of each round — technical weighs most for SWE).
ROUND_WEIGHTS: dict[int, float] = {
    1: 0.15,   # HR
    2: 0.30,   # Technical
    3: 0.25,   # System Design
    4: 0.15,   # Managerial
    5: 0.15,   # Negotiation
}


# ════════════════════════════════════════════════════════════════
# Persona + round system prompts
# ════════════════════════════════════════════════════════════════

PERSONA_VOICES: dict[InterviewPersona, str] = {
    InterviewPersona.FRIENDLY: (
        "You are a friendly, encouraging interviewer. You're warm, patient, and "
        "celebrate small wins. You rephrase hard questions kindly and reassure "
        "the candidate when they stumble, but still probe for depth."
    ),
    InterviewPersona.TOUGH: (
        "You are a tough, no-nonsense interviewer. You probe for exact details, "
        "poke at weak spots, and don't let sloppy answers slide. You are not "
        "rude — just rigorous. Push the candidate to be precise."
    ),
    InterviewPersona.RAPID_FIRE: (
        "You are a rapid-fire interviewer. Ask short, punchy questions. Keep "
        "follow-ups brief. Don't let the candidate meander — cut them off "
        "politely and move on to the next micro-question if they take too long."
    ),
    InterviewPersona.UNPREDICTABLE: (
        "You are an unpredictable interviewer. Switch tone and question style "
        "mid-interview — sometimes warm, sometimes skeptical, sometimes quirky. "
        "Your goal is to test how the candidate adapts to changing interviewers."
    ),
}

ROUND_DESCRIPTIONS: dict[int, str] = {
    1: (
        "Round 1 — HR / Behavioural. Ask about the candidate's background, "
        "motivation, teamwork, conflict resolution, and 'tell me about yourself'. "
        "Look for clear communication and self-awareness."
    ),
    2: (
        "Round 2 — Technical. Ask DSA / coding questions grounded in the target "
        "company and role. Prefer verbal walkthroughs over code — ask for time/"
        "space complexity, edge cases, and alternative approaches."
    ),
    3: (
        "Round 3 — System Design. Ask a high-level design question suited to "
        "a new-grad (URL shortener, rate limiter, file-sharing, simple Twitter "
        "feed). Probe trade-offs, scaling, and data models."
    ),
    4: (
        "Round 4 — Managerial. Ask about leadership, decision making under "
        "uncertainty, disagreeing with a manager, prioritisation and failure "
        "stories. Look for STAR-style structured responses."
    ),
    5: (
        "Round 5 — Negotiation. Simulate a salary / offer conversation. Ask "
        "the candidate to justify their expected compensation and handle a "
        "lowball offer. Look for professionalism and market awareness."
    ),
}


# ════════════════════════════════════════════════════════════════
# JSON protocol for Claude turns
# ════════════════════════════════════════════════════════════════

INTERVIEWER_SYSTEM_TEMPLATE = """{persona_voice}

You are interviewing a candidate for **{company} — {role}**.

Current round: **{current_round_name}** (round {current_round}/5, question {q_num}/{q_max}).

{round_description}

=== PROTOCOL — VALID JSON ONLY ===
Respond with a JSON object (no markdown fences, no commentary):
{{
  "score": <number 0-10, REQUIRED>,
  "score_reason": "<1 short sentence rationale, REQUIRED>",
  "next_message": "<what you say next to the candidate — their next question or follow-up, in 1-3 short sentences>",
  "advance_round": <true if you want to move to the next round after this turn, false otherwise>
}}

Rules:
- You MUST include a numeric `score` (0-10) for every user message, even the first. If the candidate's answer was weak, score it low. If it was just a greeting, still give it ~5.
- `score_reason` is a short neutral rationale; never reveal it inside next_message.
- `next_message` is ALWAYS required — it's what the candidate sees next.
- Ask exactly ONE question at a time. Keep follow-ups tight.
- Set `advance_round` to true ONLY after {q_max} meaningful exchanges in the current round OR when the candidate clearly can't continue.
- Never reveal scores inside `next_message`. The score goes to the `score` field only.
- When a round opens, acknowledge the transition naturally ("Great, let's move on to...") then ask your first question."""


DEBRIEF_SYSTEM = """You are an interview coach writing a debrief report for a candidate who just finished a 5-round mock interview.

You will be given:
- The company + role
- The interviewer persona
- Per-round average scores (0-10)
- An overall weighted score (0-100)
- The full transcript

Respond with VALID JSON ONLY (no markdown fences):
{
  "hire_verdict": "strong_hire" | "hire" | "leaning_no" | "no_hire",
  "headline": "<1-sentence verdict shown at the top of the debrief>",
  "strengths": [<up to 3 strings — concrete things the candidate did well>],
  "improvements": [<up to 3 strings — prioritized, actionable suggestions>],
  "standout_answer": "<the candidate's single best answer or line, paraphrased in 1 sentence>",
  "biggest_gap": "<the candidate's single weakest area in 1 sentence>"
}

Scoring guide for hire_verdict:
- overall ≥ 75 → "strong_hire"
- 60 ≤ overall < 75 → "hire"
- 45 ≤ overall < 60 → "leaning_no"
- overall < 45 → "no_hire"
"""


# ════════════════════════════════════════════════════════════════
# Live voice mode (ElevenLabs Conversational AI) prompts
# ════════════════════════════════════════════════════════════════
#
# In live mode the round is a real-time voice conversation handled by the
# ElevenLabs agent — so this prompt drives ONLY the conversation, never the
# scoring. Grading happens afterward from the finished transcript
# (ROUND_GRADER_SYSTEM below), which is what keeps per-turn latency low.

LIVE_INTERVIEWER_SYSTEM_TEMPLATE = """{persona_voice}

You are conducting a live SPOKEN interview for **{company} — {role}**.
This is the **{round_name}** round (round {current_round} of 5).

{round_description}

You are talking out loud, so:
- Keep every turn SHORT — 1 to 3 sentences. No markdown, no lists, no code, no spelled-out symbols.
- Ask exactly ONE question at a time, then wait for the candidate's full spoken answer.
- Cover about {q_max} substantive questions this round, with brief, natural follow-ups.
- React briefly and naturally to each answer, then continue. Stay fully in character.
- NEVER mention scores, ratings, or evaluation — you only run the conversation; grading is done separately afterward.
- After roughly {q_max} questions, wrap up in one short sentence (e.g. "Thanks, that's everything for this round.") and stop asking new questions."""


ROUND_GRADER_SYSTEM = """You are a rigorous but fair technical interview assessor. You are given the transcript of ONE round of a mock interview.

Score EACH candidate answer from 0 to 10:
- 0-3: missing, evasive, or wrong.
- 4-6: partially correct or vague; lacks structure or specifics.
- 7-8: solid, correct, well-structured.
- 9-10: excellent — precise, complete, with trade-offs/edge-cases.
A bare greeting or "I don't know" is ~3-5.

Respond with VALID JSON ONLY (no markdown fences):
{
  "answers": [
    { "index": <0-based index of the candidate answer within this round, as labelled>, "score": <number 0-10>, "reason": "<one short neutral sentence>" }
  ]
}

Score every candidate answer labelled in the transcript, in order. If there are no candidate answers, return {"answers": []}."""


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text).strip()


def _parse_first_json_object(text: str) -> dict:
    cleaned = _strip_fences(text)
    start = cleaned.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object", cleaned, 0)
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(cleaned[start:])
    if not isinstance(obj, dict):
        raise json.JSONDecodeError("Top-level value is not an object", cleaned, 0)
    return obj


def _require_student(user: User) -> None:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock interviews are only available to students.",
        )


def _empty_state() -> dict:
    return {
        "questions_per_round": QUESTIONS_PER_ROUND,
        "round_question_counts": {str(i): 0 for i in range(1, TOTAL_ROUNDS + 1)},
        "round_scores_sum": {str(i): 0.0 for i in range(1, TOTAL_ROUNDS + 1)},
        "round_scores_count": {str(i): 0 for i in range(1, TOTAL_ROUNDS + 1)},
        "awaiting_answer": False,
    }


def _load_state(session: MockInterviewSession) -> dict:
    state = session.state or {}
    if "questions_per_round" not in state:
        state = _empty_state()
    return state


def _load_transcript(session: MockInterviewSession) -> list[dict]:
    return list(session.transcript or [])


def _round_summaries(state: dict, current_round: int, status_str: str) -> list[RoundSummary]:
    rounds: list[RoundSummary] = []
    for r in range(1, TOTAL_ROUNDS + 1):
        count = int(state.get("round_scores_count", {}).get(str(r), 0) or 0)
        total = float(state.get("round_scores_sum", {}).get(str(r), 0.0) or 0.0)
        q_asked = int(state.get("round_question_counts", {}).get(str(r), 0) or 0)
        avg = round(total / count, 2) if count > 0 else None
        # A round is "completed" once it's actually been graded (rounds can be
        # run in any order), "active" when it's the one in progress, else
        # "locked" (= not done yet — any round may still be started).
        graded = state.get("round_status", {}).get(str(r)) == "done" or count > 0
        if status_str == InterviewStatus.COMPLETED.value or graded:
            r_status: str = "completed"
        elif r == current_round:
            r_status = "active"
        else:
            r_status = "locked"
        rounds.append(
            RoundSummary(
                round_number=r,
                name=ROUND_NAMES[r],
                questions_asked=q_asked,
                avg_score=avg,
                status=r_status,  # type: ignore[arg-type]
            )
        )
    return rounds


def _to_transcript_turns(transcript: list[dict]) -> list[InterviewTranscriptTurn]:
    return [
        InterviewTranscriptTurn(
            role=t.get("role", "assistant"),  # type: ignore[arg-type]
            content=t.get("content", ""),
            round_number=int(t.get("round_number", 1)),
            score=t.get("score"),
            score_reason=t.get("score_reason"),
            is_round_transition=bool(t.get("is_round_transition", False)),
        )
        for t in transcript
    ]


def _to_session_response(session: MockInterviewSession) -> InterviewSessionResponse:
    state = _load_state(session)
    transcript = _load_transcript(session)
    return InterviewSessionResponse(
        id=session.id,
        company_target=session.company_target,
        role_target=session.role_target,
        interviewer_persona=session.interviewer_persona.value,  # type: ignore[arg-type]
        mode=session.mode.value,  # type: ignore[arg-type]
        current_round=session.current_round,
        is_full_simulator=session.is_full_simulator,
        status=session.status.value,  # type: ignore[arg-type]
        overall_score=float(session.overall_score) if session.overall_score is not None else None,
        started_at=session.started_at,
        completed_at=session.completed_at,
        transcript=_to_transcript_turns(transcript),
        round_summaries=_round_summaries(state, session.current_round, session.status.value),
        feedback_report=session.feedback_report,
    )


# ════════════════════════════════════════════════════════════════
# Session CRUD
# ════════════════════════════════════════════════════════════════

def create_session(
    db: Session,
    user: User,
    *,
    company_target: str,
    role_target: str,
    interviewer_persona: InterviewPersona,
    mode: InterviewMode,
) -> MockInterviewSession:
    _require_student(user)
    session = MockInterviewSession(
        student_id=user.id,
        company_target=company_target,
        role_target=role_target,
        interviewer_persona=interviewer_persona,
        mode=mode,
        current_round=1,
        is_full_simulator=True,
        state=_empty_state(),
        transcript=[],
        status=InterviewStatus.IN_PROGRESS,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Live voice mode: the ElevenLabs agent speaks the opener itself (per-round
    # `first_message`), and each round's transcript is appended only after it's
    # graded — so the persisted transcript starts empty.
    if mode == InterviewMode.VOICE:
        return session

    # Text mode: seed the opening assistant message with a synthetic persona
    # intro + first question so the chat has content instantly.
    opening = _synthetic_opening(session)
    transcript = _load_transcript(session)
    transcript.append(
        {
            "role": "assistant",
            "content": opening,
            "round_number": 1,
            "score": None,
            "score_reason": None,
            "is_round_transition": True,
        }
    )
    state = _load_state(session)
    state["awaiting_answer"] = True
    state["round_question_counts"]["1"] = 1
    session.transcript = transcript
    session.state = state
    flag_modified(session, "transcript")
    flag_modified(session, "state")
    db.commit()
    db.refresh(session)
    return session


def _synthetic_opening(session: MockInterviewSession) -> str:
    """Build a fast, deterministic opening so the UI has content instantly
    even if Claude is slow. Overridden by the next real turn."""
    persona = session.interviewer_persona
    company = session.company_target or "the company"
    greetings: dict[InterviewPersona, str] = {
        InterviewPersona.FRIENDLY: (
            f"Hi! Welcome to your mock interview for {company}. I'm your HR coach today. "
            "Let's start easy — tell me a bit about yourself and why you're interested in this role."
        ),
        InterviewPersona.TOUGH: (
            f"Okay, let's get straight to it. We're interviewing for {company}. "
            "In 60 seconds or less: who are you, and why should we even consider you?"
        ),
        InterviewPersona.RAPID_FIRE: (
            f"{company} mock interview — rapid fire mode. Name, year, top 2 skills, and "
            "one line on why you want this role. Go."
        ),
        InterviewPersona.UNPREDICTABLE: (
            f"Welcome to the {company} interview. Before we start, tell me something interesting "
            "about yourself that's NOT on your resume, then walk me through your background."
        ),
    }
    return greetings.get(persona, greetings[InterviewPersona.FRIENDLY])


def get_session(
    db: Session, session_id: uuid.UUID, user: User
) -> MockInterviewSession:
    session = db.get(MockInterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if session.student_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this interview")
    return session


def fetch_session(
    db: Session, session_id: uuid.UUID, user: User
) -> InterviewSessionResponse:
    return _to_session_response(get_session(db, session_id, user))


def list_sessions_for_student(
    db: Session, user: User, *, limit: int = 20
) -> list[MockInterviewSession]:
    _require_student(user)
    from sqlalchemy import select
    return list(
        db.scalars(
            select(MockInterviewSession)
            .where(MockInterviewSession.student_id == user.id)
            .order_by(MockInterviewSession.started_at.desc())
            .limit(limit)
        ).all()
    )


# ════════════════════════════════════════════════════════════════
# Main turn: student answers → interviewer scores + next question
# ════════════════════════════════════════════════════════════════

@dataclass
class TurnResult:
    session: MockInterviewSession
    assistant_message: str
    round_transitioned: bool
    interview_completed: bool


def student_turn(
    db: Session,
    user: User,
    session_id: uuid.UUID,
    user_message: str,
) -> TurnResult:
    session = get_session(db, session_id, user)
    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400, detail="Interview is already completed or abandoned"
        )
    if not claude_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Mock interviewer unavailable: ANTHROPIC_API_KEY is not configured.",
        )

    state = _load_state(session)
    transcript = _load_transcript(session)
    current_round = session.current_round
    q_num = int(state["round_question_counts"].get(str(current_round), 0))
    q_max = int(state.get("questions_per_round", QUESTIONS_PER_ROUND))

    # Append the user's answer to the transcript before we call Claude
    transcript.append(
        {
            "role": "user",
            "content": user_message,
            "round_number": current_round,
            "score": None,
            "score_reason": None,
            "is_round_transition": False,
        }
    )

    # Build the system prompt
    persona_voice = PERSONA_VOICES.get(
        session.interviewer_persona, PERSONA_VOICES[InterviewPersona.FRIENDLY]
    )
    round_name = ROUND_NAMES.get(current_round, "Unknown")
    round_description = ROUND_DESCRIPTIONS.get(current_round, "")
    system_prompt = INTERVIEWER_SYSTEM_TEMPLATE.format(
        persona_voice=persona_voice,
        company=session.company_target or "the company",
        role=session.role_target or "the role",
        current_round_name=round_name,
        current_round=current_round,
        q_num=q_num,
        q_max=q_max,
        round_description=round_description,
    )

    # Pack the last ~12 transcript turns as the conversation history
    history: list[dict] = []
    for t in transcript[-12:]:
        role = "assistant" if t["role"] == "assistant" else "user"
        history.append({"role": role, "content": t["content"]})

    # Single-turn call
    raw = claude_client.generate_completion(
        system=system_prompt,
        user_message=history[-1]["content"] if history else user_message,
        max_tokens=600,
        temperature=0.5,
    )
    if not raw:
        # Roll back the user turn from the transcript so they can retry
        transcript.pop()
        session.transcript = transcript
        db.commit()
        raise HTTPException(status_code=502, detail="Interviewer returned an empty response")

    try:
        data = _parse_first_json_object(raw)
    except json.JSONDecodeError:
        # Fallback: treat the raw text as a plain next_message, skip scoring
        data = {"next_message": raw.strip(), "score": None, "score_reason": None, "advance_round": False}

    score = data.get("score")
    try:
        score_val = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_val = None
    if score_val is not None:
        score_val = max(0.0, min(10.0, round(score_val, 2)))

    score_reason = str(data.get("score_reason") or "").strip() or None
    next_message = str(data.get("next_message") or "").strip()
    if not next_message:
        next_message = "Hmm, let me think about that for a moment. Can you walk me through your reasoning one more time?"
    advance_round = bool(data.get("advance_round") or False)

    # Attach the score to the just-added user turn
    if score_val is not None:
        transcript[-1]["score"] = score_val
        transcript[-1]["score_reason"] = score_reason
        state["round_scores_sum"][str(current_round)] = float(
            state["round_scores_sum"].get(str(current_round), 0.0)
        ) + score_val
        state["round_scores_count"][str(current_round)] = int(
            state["round_scores_count"].get(str(current_round), 0)
        ) + 1

    round_transitioned = False
    interview_completed = False

    # Decide whether to transition rounds — either the model said so OR we've
    # hit the per-round question cap.
    new_q_count = int(state["round_question_counts"].get(str(current_round), 0))
    scored_count = int(state["round_scores_count"].get(str(current_round), 0))
    should_advance = advance_round or scored_count >= q_max

    if should_advance and current_round < TOTAL_ROUNDS:
        # Advance to the next round — the assistant's next_message kicks it off
        current_round += 1
        session.current_round = current_round
        round_transitioned = True
        state["round_question_counts"][str(current_round)] = (
            int(state["round_question_counts"].get(str(current_round), 0)) + 1
        )
        transcript.append(
            {
                "role": "assistant",
                "content": next_message,
                "round_number": current_round,
                "score": None,
                "score_reason": None,
                "is_round_transition": True,
            }
        )
    elif should_advance and current_round >= TOTAL_ROUNDS:
        # Final turn — interview done. Append the closing message, run debrief.
        transcript.append(
            {
                "role": "assistant",
                "content": next_message,
                "round_number": current_round,
                "score": None,
                "score_reason": None,
                "is_round_transition": False,
            }
        )
        interview_completed = True
    else:
        # Normal in-round follow-up
        state["round_question_counts"][str(current_round)] = new_q_count + 1
        transcript.append(
            {
                "role": "assistant",
                "content": next_message,
                "round_number": current_round,
                "score": None,
                "score_reason": None,
                "is_round_transition": False,
            }
        )

    session.transcript = transcript
    session.state = state
    flag_modified(session, "transcript")
    flag_modified(session, "state")
    db.commit()
    db.refresh(session)

    if interview_completed:
        complete_and_debrief(db, session)

    return TurnResult(
        session=session,
        assistant_message=next_message,
        round_transitioned=round_transitioned,
        interview_completed=interview_completed,
    )


# ════════════════════════════════════════════════════════════════
# Debrief / completion
# ════════════════════════════════════════════════════════════════

def _compute_overall_score(state: dict) -> float:
    total = 0.0
    weight_used = 0.0
    for r in range(1, TOTAL_ROUNDS + 1):
        count = int(state["round_scores_count"].get(str(r), 0) or 0)
        if count == 0:
            continue
        avg = float(state["round_scores_sum"].get(str(r), 0.0)) / count
        total += avg * ROUND_WEIGHTS[r]
        weight_used += ROUND_WEIGHTS[r]
    if weight_used == 0:
        return 0.0
    # Scale 0-10 avg to 0-100 and normalise by the weight actually used
    return round((total / weight_used) * 10.0, 2)


def complete_and_debrief(
    db: Session, session: MockInterviewSession
) -> MockInterviewSession:
    # Idempotent: the live-mode background grader may call this once the final
    # round is scored, and /end can race it. Only debrief once.
    if session.status == InterviewStatus.COMPLETED:
        return session
    state = _load_state(session)
    overall = _compute_overall_score(state)
    session.overall_score = Decimal(f"{overall:.2f}")
    session.status = InterviewStatus.COMPLETED
    session.completed_at = datetime.now(timezone.utc)

    # Round averages for the report
    round_averages: dict[int, float] = {}
    for r in range(1, TOTAL_ROUNDS + 1):
        count = int(state["round_scores_count"].get(str(r), 0) or 0)
        if count == 0:
            continue
        round_averages[r] = round(
            float(state["round_scores_sum"].get(str(r), 0.0)) / count, 2
        )

    feedback_report = _generate_debrief_report(session, round_averages, overall)
    session.feedback_report = feedback_report
    db.commit()
    db.refresh(session)

    # XP reward for finishing a full interview + interview-pillar recompute
    try:
        # Resolve the student user
        from app.models.user import User as UserModel
        student = db.get(UserModel, session.student_id)
        if student is not None:
            bonus_factor = 1.0 + overall / 100.0
            xp.award_xp(
                db,
                student,
                XPEventType.MOCK_INTERVIEW_COMPLETED,
                reference_id=session.id,
                bonus_multiplier=bonus_factor,
            )
            # Refresh the CampusIQ score so the interview pillar reflects this run.
            from app.services import campus_iq_score
            campus_iq_score.recompute_score(db, student)
            db.commit()
    except Exception as e:
        logger.warning("XP award / score recompute (mock interview) failed: %s", e)

    # Phase 9 — push the debrief notification so the student sees a toast
    # the moment the WebSocket relays it.
    try:
        from app.models.algorithm import NotificationType
        from app.services import notifications as notifications_service

        verdict = (session.feedback_report or {}).get("hire_verdict") or "complete"
        notifications_service.publish_sync(
            db,
            user_id=session.student_id,
            notification_type=NotificationType.INTERVIEW_FEEDBACK,
            title=f"Interview complete: {session.company_target or 'Mock interview'}",
            content=f"Overall {overall:.1f}/100 — verdict: {verdict.replace('_', ' ')}.",
            extra={
                "session_id": str(session.id),
                "overall_score": overall,
                "hire_verdict": verdict,
            },
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("Mock interview notification failed: %s", e)

    return session


def _generate_debrief_report(
    session: MockInterviewSession, round_averages: dict[int, float], overall: float
) -> dict:
    """Call Claude once to produce the final debrief JSON. Falls back to a
    deterministic skeleton if the model call fails."""
    if not claude_client.is_available():
        return _fallback_debrief(round_averages, overall)

    transcript_lines = []
    for t in (session.transcript or [])[-40:]:
        role = "Interviewer" if t.get("role") == "assistant" else "Candidate"
        transcript_lines.append(f"[R{t.get('round_number')}] {role}: {t.get('content', '')[:240]}")

    user_message = (
        f"Company: {session.company_target}\n"
        f"Role: {session.role_target}\n"
        f"Persona: {session.interviewer_persona.value}\n"
        f"Per-round averages (0-10): {round_averages}\n"
        f"Overall weighted score (0-100): {overall}\n\n"
        "=== TRANSCRIPT EXCERPT ===\n"
        + "\n".join(transcript_lines)
    )

    raw = claude_client.generate_completion(
        system=DEBRIEF_SYSTEM,
        user_message=user_message,
        max_tokens=900,
        temperature=0.4,
    )
    if not raw:
        return _fallback_debrief(round_averages, overall)

    try:
        data = _parse_first_json_object(raw)
    except json.JSONDecodeError:
        return _fallback_debrief(round_averages, overall)

    return {
        "hire_verdict": str(data.get("hire_verdict") or _verdict_from_score(overall)),
        "headline": str(data.get("headline") or "Interview complete."),
        "strengths": [str(s) for s in (data.get("strengths") or [])][:3],
        "improvements": [str(s) for s in (data.get("improvements") or [])][:3],
        "standout_answer": str(data.get("standout_answer") or ""),
        "biggest_gap": str(data.get("biggest_gap") or ""),
        "round_averages": {str(k): v for k, v in round_averages.items()},
        "overall_score": overall,
    }


def _verdict_from_score(overall: float) -> str:
    if overall >= 75:
        return "strong_hire"
    if overall >= 60:
        return "hire"
    if overall >= 45:
        return "leaning_no"
    return "no_hire"


def _fallback_debrief(round_averages: dict[int, float], overall: float) -> dict:
    return {
        "hire_verdict": _verdict_from_score(overall),
        "headline": f"Scored {overall:.0f}/100 across 5 rounds.",
        "strengths": [
            f"Completed all 5 rounds with an overall score of {overall:.0f}.",
        ],
        "improvements": [
            "Retake the interview and focus on your lowest-scoring round.",
        ],
        "standout_answer": "",
        "biggest_gap": "",
        "round_averages": {str(k): v for k, v in round_averages.items()},
        "overall_score": overall,
    }


# ════════════════════════════════════════════════════════════════
# Live voice mode — ElevenLabs Conversational AI (Agents)
# ════════════════════════════════════════════════════════════════
#
# Each round is a real-time spoken conversation with one shared ElevenLabs
# agent, customized per round via startSession overrides. The browser holds the
# live audio link; the server only (1) mints the signed URL and (2) grades the
# finished transcript with Claude. Per-round conversation ids + status live in
# the session `state` JSON, so there's no schema change.


def _live_first_message(session: MockInterviewSession, round_number: int) -> str:
    """The agent's spoken opener for a round. Round 1 greets in-persona; later
    rounds transition in and pose the round's first question so the candidate
    always knows what to answer."""
    company = session.company_target or "the company"
    if round_number == 1:
        return _synthetic_opening(session)
    openers = {
        2: (
            "Let's move into the technical round. To start: walk me through how "
            "you'd reverse a linked list, and tell me its time and space complexity."
        ),
        3: (
            "Now the system design round. At a high level, how would you design a "
            "URL shortener like bit.ly? Walk me through the main components."
        ),
        4: (
            "Let's talk about working with people. Tell me about a time you "
            "disagreed with a teammate or manager, and how you handled it."
        ),
        5: (
            f"Final round — the offer conversation for {company}. We'd like to "
            "extend an offer at the lower end of our band. How do you respond?"
        ),
    }
    return openers.get(round_number, "Let's continue with the next round.")


def _live_round_overrides(session: MockInterviewSession, round_number: int) -> dict:
    """Build the per-round agent override payload + display fields."""
    persona_voice = PERSONA_VOICES.get(
        session.interviewer_persona, PERSONA_VOICES[InterviewPersona.FRIENDLY]
    )
    round_name = ROUND_NAMES.get(round_number, "Interview")
    system_prompt = LIVE_INTERVIEWER_SYSTEM_TEMPLATE.format(
        persona_voice=persona_voice,
        company=session.company_target or "the company",
        role=session.role_target or "the role",
        round_name=round_name,
        current_round=round_number,
        q_max=QUESTIONS_PER_ROUND,
        round_description=ROUND_DESCRIPTIONS.get(round_number, ""),
    )
    return {
        "round_number": round_number,
        "round_name": round_name,
        "voice_id": speech.VOICE_BY_ROUND.get(round_number, speech.DEFAULT_VOICE_ID),
        "language": "en",
        "system_prompt": system_prompt,
        "first_message": _live_first_message(session, round_number),
    }


def _validate_round(round_number: int) -> None:
    if round_number < 1 or round_number > TOTAL_ROUNDS:
        raise HTTPException(status_code=400, detail=f"Invalid round: {round_number}")


def _all_rounds_done(session: MockInterviewSession) -> bool:
    """True once every round has been graded (round_status == 'done')."""
    rs = _load_state(session).get("round_status", {})
    return all(rs.get(str(r)) == "done" for r in range(1, TOTAL_ROUNDS + 1))


def start_live_round(
    db: Session, user: User, session_id: uuid.UUID, round_number: int
) -> dict:
    """Mint a signed agent URL for a round and return its override payload."""
    from app.services import elevenlabs_agent

    session = get_session(db, session_id, user)
    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400, detail="Interview is already completed or abandoned"
        )
    _validate_round(round_number)
    if not elevenlabs_agent.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Live voice interview is not configured on the server "
                "(ELEVENLABS_AGENT_ID is unset). Use Text mode instead."
            ),
        )
    signed_url = elevenlabs_agent.get_signed_url()
    if not signed_url:
        raise HTTPException(
            status_code=503,
            detail="Could not start the voice agent. Please try again or use Text mode.",
        )

    # Advance the session to this round and mark it live.
    state = _load_state(session)
    state.setdefault("round_status", {})[str(round_number)] = "live"
    session.current_round = round_number
    session.state = state
    flag_modified(session, "state")
    db.commit()

    payload = _live_round_overrides(session, round_number)
    payload["signed_url"] = signed_url
    return payload


def finalize_live_round(
    db: Session,
    user: User,
    session_id: uuid.UUID,
    round_number: int,
    conversation_id: str,
    background_tasks,
) -> tuple[MockInterviewSession, bool, bool]:
    """Record a finished round's conversation id and schedule its grading.

    Returns (session, grading_scheduled, interview_completing). Grading runs in
    the background; the final round's grade triggers the debrief.
    """
    session = get_session(db, session_id, user)
    if session.status != InterviewStatus.IN_PROGRESS:
        # Already finalized / ended — nothing to do.
        return session, False, False
    _validate_round(round_number)

    state = _load_state(session)
    state.setdefault("round_conversations", {})[str(round_number)] = conversation_id
    state.setdefault("round_status", {})[str(round_number)] = "grading"
    session.state = state
    flag_modified(session, "state")
    db.commit()
    db.refresh(session)

    background_tasks.add_task(
        _grade_round_bg, session_id, round_number, conversation_id
    )
    # "Completing" when this is the last of the 5 distinct rounds to be run (in
    # any order) — i.e. every round is now finalized (grading or done).
    round_status = state.get("round_status", {})
    finalized = sum(
        1
        for r in range(1, TOTAL_ROUNDS + 1)
        if round_status.get(str(r)) in ("grading", "done")
    )
    interview_completing = finalized >= TOTAL_ROUNDS
    return session, True, interview_completing


# Serialize grading per session so two rounds finalized close together can't
# race on the same session row (lost update on transcript/state). The slow
# transcript poll happens *outside* the lock; only the read-modify-write is
# serialized. Mirrors the per-exam lock in answersheet_grader.
_session_grade_locks: dict[str, threading.Lock] = {}
_session_grade_locks_guard = threading.Lock()


def _session_grade_lock(session_id: uuid.UUID) -> threading.Lock:
    key = str(session_id)
    with _session_grade_locks_guard:
        lock = _session_grade_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _session_grade_locks[key] = lock
        return lock


def _grade_round_bg(
    session_id: uuid.UUID, round_number: int, conversation_id: str
) -> None:
    """Background task: pull the round transcript from ElevenLabs and score it.

    Opens its own DB session (the test suite repoints SessionLocal, so import it
    inside the function). Writes the round's turns + per-answer scores into the
    session, then triggers the debrief after the final round.
    """
    from app.core.database import SessionLocal
    from app.services import elevenlabs_agent

    try:
        # Slow, DB-free work first — fetch the finished transcript.
        convo = elevenlabs_agent.poll_conversation_until_done(conversation_id)
        turns = elevenlabs_agent.extract_transcript_turns(convo)

        # Serialize the grade + write per session (reload inside the lock so we
        # see any sibling round that committed while we were polling).
        with _session_grade_lock(session_id):
            db = SessionLocal()
            try:
                session = db.get(MockInterviewSession, session_id)
                if session is None:
                    return
                scores = _grade_round_transcript(session, round_number, turns)
                _apply_round_result(
                    db, session, round_number, turns, scores, conversation_id
                )
                # Auto-finish once every round has been graded (any order). A
                # partial interview is finished explicitly via /end instead.
                if _all_rounds_done(session):
                    complete_and_debrief(db, session)
            finally:
                db.close()
    except Exception:  # noqa: BLE001 - a grading failure must not crash the worker
        logger.exception("Live round grading failed (round %s)", round_number)


def _grade_round_transcript(
    session: MockInterviewSession, round_number: int, turns: list[dict]
) -> dict[int, dict]:
    """Score each candidate answer in a round via Claude. Returns
    {candidate_answer_index: {"score": float, "reason": str|None}}; empty on
    failure (the round then records unscored turns)."""
    candidate_answers = [t for t in turns if t["role"] == "user"]
    if not candidate_answers or not claude_client.is_available():
        return {}

    lines: list[str] = []
    answer_idx = 0
    for t in turns:
        if t["role"] == "assistant":
            lines.append(f"Interviewer: {t['content'][:500]}")
        else:
            lines.append(f"Candidate answer [{answer_idx}]: {t['content'][:800]}")
            answer_idx += 1

    user_message = (
        f"Company: {session.company_target}\n"
        f"Role: {session.role_target}\n"
        f"Persona: {session.interviewer_persona.value}\n"
        f"Round: {ROUND_NAMES.get(round_number, round_number)}\n\n"
        "=== ROUND TRANSCRIPT ===\n" + "\n".join(lines)
    )

    raw = claude_client.generate_completion(
        system=ROUND_GRADER_SYSTEM,
        user_message=user_message,
        max_tokens=700,
        temperature=0.3,
    )
    if not raw:
        return {}
    try:
        data = _parse_first_json_object(raw)
    except json.JSONDecodeError:
        return {}

    out: dict[int, dict] = {}
    for item in data.get("answers") or []:
        try:
            idx = int(item.get("index"))
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        out[idx] = {
            "score": max(0.0, min(10.0, round(score, 2))),
            "reason": str(item.get("reason") or "").strip() or None,
        }
    return out


def _apply_round_result(
    db: Session,
    session: MockInterviewSession,
    round_number: int,
    turns: list[dict],
    scores: dict[int, dict],
    conversation_id: str,
) -> None:
    """Write a graded round's turns into the transcript and update round state.

    Rounds may be run in any order and re-run, so this **replaces** the round:
    any prior turns/scores for `round_number` are dropped first, the aggregates
    are set (not accumulated), and the transcript is kept grouped by round."""
    state = _load_state(session)
    # Drop any previous attempt of this round.
    transcript = [
        t for t in _load_transcript(session)
        if int(t.get("round_number", 0)) != round_number
    ]

    score_sum = 0.0
    score_count = 0
    question_count = 0
    answer_idx = 0
    new_turns: list[dict] = []
    for t in turns:
        if t["role"] == "assistant":
            question_count += 1
            new_turns.append(
                {
                    "role": "assistant",
                    "content": t["content"],
                    "round_number": round_number,
                    "score": None,
                    "score_reason": None,
                    "is_round_transition": question_count == 1,
                }
            )
        else:
            graded = scores.get(answer_idx)
            score_val = graded["score"] if graded else None
            reason = graded["reason"] if graded else None
            new_turns.append(
                {
                    "role": "user",
                    "content": t["content"],
                    "round_number": round_number,
                    "score": score_val,
                    "score_reason": reason,
                    "is_round_transition": False,
                }
            )
            if score_val is not None:
                score_sum += score_val
                score_count += 1
            answer_idx += 1

    transcript.extend(new_turns)
    # Keep the transcript grouped by round ascending (stable sort preserves the
    # within-round order) so it reads 1→5 regardless of completion order.
    transcript.sort(key=lambda t: int(t.get("round_number", 0)))

    r = str(round_number)
    state.setdefault("round_scores_sum", {})[r] = score_sum
    state.setdefault("round_scores_count", {})[r] = score_count
    state.setdefault("round_question_counts", {})[r] = question_count
    state.setdefault("round_status", {})[r] = "done"
    state.setdefault("round_conversations", {})[r] = conversation_id

    session.transcript = transcript
    session.state = state
    flag_modified(session, "transcript")
    flag_modified(session, "state")
    db.commit()
    db.refresh(session)


def end_session(
    db: Session, session_id: uuid.UUID, user: User
) -> MockInterviewSession:
    """Force-complete the session early (user clicked End Interview)."""
    session = get_session(db, session_id, user)
    if session.status != InterviewStatus.IN_PROGRESS:
        return session
    complete_and_debrief(db, session)
    return session


def abandon_session(
    db: Session, session_id: uuid.UUID, user: User
) -> MockInterviewSession:
    session = get_session(db, session_id, user)
    session.status = InterviewStatus.ABANDONED
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session
