"""Resume Builder service (Phase 14, F6).

Three responsibilities:
1. **Conversational AI builder** — Claude-driven multi-turn chat that
   incrementally fills out a structured resume. Each user reply is paired
   with a JSON patch that gets deep-merged into the stored resume content.
2. **ATS scoring** — score the resume against a pasted job description and
   return matched / missing keywords + actionable suggestions.
3. **GitHub import** — pull the user's top public repos and merge them into
   the projects section.

The chat history is stored on `chat_messages` with `chat_type='resume_builder'`
and a single auto-created session per student.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession, ChatType, MessageRole
from app.models.gamification import XPEventType
from app.models.placement import Resume
from app.models.user import User, UserRole
from app.schemas.resume import (
    ATSScoreResponse,
    GitHubProjectImport,
    ResumeChatHistory,
    ResumeChatHistoryItem,
    ResumeContent,
    ResumeProject,
    ResumeResponse,
)
from app.services import chat as chat_service
from app.services import claude_client, xp
from app.services.github_import import GitHubRepo, fetch_top_repos

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Constants / system prompts
# ════════════════════════════════════════════════════════════════

RESUME_COACH_SYSTEM = """You are CampusIQ Resume Coach — a friendly career mentor helping an engineering student build a one-page technical resume one section at a time.

You will be given:
1. The resume's CURRENT JSON state (what's already filled)
2. A FILLED / MISSING summary (quick reference of which sections have data)
3. The full conversation history
4. The student's latest message

Your job each turn:
1. Parse whatever NEW information the student just shared.
2. Update the resume by emitting a JSON patch with ONLY the fields they just provided.
3. Ask ONE focused follow-up question about a MISSING section.

Always respond with VALID JSON ONLY (no markdown fences, no commentary outside the JSON), in this exact shape:
{
  "ai_reply": "Your conversational reply + the next question, in 1-3 short sentences. Encouraging and concrete.",
  "patch": { "any subset of the resume schema below" }
}

Resume schema (fields the patch can write to):
- "personal":     { name, email, phone, location, linkedin, github, portfolio }
- "summary":      string (2-3 sentence professional summary)
- "education":    array of { institution, degree, branch, start_year, end_year, cgpa, highlights[] }
- "experience":   array of { company, role, location, start_date, end_date, bullets[] }
- "projects":     array of { name, description, tech[], url, highlights[] }
- "skills":       array of strings
- "certifications": array of strings
- "achievements": array of strings

CRITICAL rules:
- NEVER ask about a field that's already filled in the CURRENT state. Check the FILLED list before asking.
- If the student's message contains MULTIPLE pieces of info (name + email + phone all at once), capture ALL of them in the patch, not just one.
- For LIST fields (education, experience, projects, skills, certifications, achievements), the patch REPLACES that list. So when adding a new entry, include all the existing items PLUS the new one. You'll see the existing items in the CURRENT state.
- Only include TOP-LEVEL keys the student actually provided info about this turn. Leave other keys OUT of the patch.
- Never invent facts the student didn't share.
- Polish rough bullets into action-verb-led phrasing.
- Skills must be concrete tools/languages/frameworks (e.g. "Python", "React", "PostgreSQL"), never vague phrases.

Suggested fill order (only ask about the NEXT missing section):
personal.name → personal.email → personal.phone → personal.location → personal.github → personal.linkedin → education[0] → experience[0] or projects[0] → skills → certifications → achievements → summary → target role
"""


ATS_SCORER_SYSTEM = """You are an ATS (Applicant Tracking System) scoring engine. You will be given a structured resume JSON and a job description. Score how well the resume matches the JD on a 0-100 scale.

Respond with VALID JSON ONLY (no markdown fences) in this exact shape:
{
  "score": number 0-100,
  "matched_keywords": [up to 12 strings — important JD keywords found in the resume],
  "missing_keywords": [up to 10 strings — important JD keywords NOT in the resume],
  "suggestions":     [up to 5 short, actionable suggestions to raise the score]
}

Scoring rubric (apply roughly):
- 0-39   = poor match (most keywords missing, role mismatch)
- 40-59  = partial match (some skills overlap, gaps in core requirements)
- 60-79  = strong match (most core skills present, minor gaps)
- 80-100 = excellent match (nearly all keywords present, role aligned)

Be honest. Most student resumes for senior roles will score 40-65."""


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text).strip()


def _parse_first_json_object(text: str) -> dict:
    """Tolerant JSON parser. Extracts the first complete `{...}` object from the
    string, ignoring any preamble or trailing commentary that Claude sometimes
    leaks despite our instructions."""
    cleaned = _strip_fences(text)
    decoder = json.JSONDecoder()
    # Find the first '{' and try raw_decode from there
    start = cleaned.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", cleaned, 0)
    obj, _end = decoder.raw_decode(cleaned[start:])
    if not isinstance(obj, dict):
        raise json.JSONDecodeError("Top-level value is not a JSON object", cleaned, 0)
    return obj


def _require_student(user: User) -> None:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resume Builder is only available to students.",
        )


def _empty_content() -> ResumeContent:
    return ResumeContent()


def _to_response(resume: Resume) -> ResumeResponse:
    return ResumeResponse(
        id=resume.id,
        student_id=resume.student_id,
        template=resume.template,  # type: ignore[arg-type]
        content=ResumeContent(**(resume.content or {})),
        ats_score=float(resume.ats_score) if resume.ats_score is not None else None,
        last_job_description=resume.last_job_description,
        last_updated=resume.last_updated,
        created_at=resume.created_at,
    )


def get_or_create_resume(db: Session, user: User) -> Resume:
    """Single resume row per student — created on first read."""
    _require_student(user)
    resume = db.scalar(select(Resume).where(Resume.student_id == user.id))
    if resume is None:
        resume = Resume(
            student_id=user.id,
            template="technical",
            content=_empty_content().model_dump(),
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
    return resume


def fetch_resume(db: Session, user: User) -> ResumeResponse:
    return _to_response(get_or_create_resume(db, user))


def replace_content(
    db: Session,
    user: User,
    *,
    new_content: ResumeContent,
    new_template: str | None = None,
) -> ResumeResponse:
    resume = get_or_create_resume(db, user)
    resume.content = new_content.model_dump()
    if new_template:
        resume.template = new_template

    db.commit()
    db.refresh(resume)
    return _to_response(resume)


# ════════════════════════════════════════════════════════════════
# Chat history (reuses chat_sessions / chat_messages)
# ════════════════════════════════════════════════════════════════

def _get_or_create_chat_session(db: Session, user: User) -> ChatSession:
    existing = db.scalar(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .where(ChatSession.chat_type == ChatType.RESUME_BUILDER)
        .order_by(ChatSession.created_at.desc())
    )
    if existing:
        return existing
    return chat_service.create_session(
        db, user, ChatType.RESUME_BUILDER, title="Resume Builder Session"
    )


def get_chat_history(db: Session, user: User) -> ResumeChatHistory:
    _require_student(user)
    session = _get_or_create_chat_session(db, user)
    msgs = chat_service.list_messages(db, session)
    return ResumeChatHistory(
        messages=[
            ResumeChatHistoryItem(
                id=m.id,
                role="assistant" if m.role == MessageRole.ASSISTANT else "user",
                content=m.content,
                created_at=m.created_at,
            )
            for m in msgs
            if m.role != MessageRole.SYSTEM
        ]
    )


def reset_chat_history(db: Session, user: User) -> None:
    _require_student(user)
    session = _get_or_create_chat_session(db, user)
    db.delete(session)
    db.commit()


# ════════════════════════════════════════════════════════════════
# Conversational chat step
# ════════════════════════════════════════════════════════════════

@dataclass
class ChatStepResult:
    ai_message: str
    content: ResumeContent
    patch_applied: bool


def _deep_merge_patch(current: dict, patch: dict) -> dict:
    """For the resume content shape: lists are REPLACED, dicts are merged.

    Strings/numbers in `patch` overwrite the corresponding key in `current`.
    """
    out = dict(current)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_patch(out[k], v)
        else:
            out[k] = v
    return out


def _summarize_filled_missing(content: dict) -> str:
    """Build a short human-readable FILLED / MISSING summary Claude can reference.

    This goes into the system prompt right before the raw JSON so Claude
    can't accidentally ask about a field that's already present.
    """
    personal = content.get("personal") or {}
    filled: list[str] = []
    missing: list[str] = []

    def check(label: str, value) -> None:
        has_data = False
        if isinstance(value, str):
            has_data = bool(value.strip())
        elif isinstance(value, list):
            has_data = len(value) > 0
        elif value is not None:
            has_data = True
        (filled if has_data else missing).append(label)

    check("personal.name", personal.get("name"))
    check("personal.email", personal.get("email"))
    check("personal.phone", personal.get("phone"))
    check("personal.location", personal.get("location"))
    check("personal.github", personal.get("github"))
    check("personal.linkedin", personal.get("linkedin"))
    check("summary", content.get("summary"))
    check("education", content.get("education"))
    check("experience", content.get("experience"))
    check("projects", content.get("projects"))
    check("skills", content.get("skills"))
    check("certifications", content.get("certifications"))
    check("achievements", content.get("achievements"))

    return (
        f"FILLED ({len(filled)}): {', '.join(filled) if filled else '(none)'}\n"
        f"MISSING ({len(missing)}): {', '.join(missing) if missing else '(none — resume is complete)'}"
    )


def chat_step(db: Session, user: User, user_message: str) -> ChatStepResult:
    """One turn of the AI resume coach.

    Persists the user message + assistant reply to chat_messages, applies the
    JSON patch to `resume.content`, and returns the new content + AI reply.
    Uses **multi-turn** Claude calls so the coach actually remembers past
    questions and answers and doesn't ask the same thing twice.
    """
    _require_student(user)
    if not claude_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Resume Coach unavailable: ANTHROPIC_API_KEY is not configured.",
        )

    resume = get_or_create_resume(db, user)
    session = _get_or_create_chat_session(db, user)

    # Persist the user message first so chat history reflects intent even if
    # Claude fails downstream.
    chat_service.add_message(db, session, MessageRole.USER, user_message)

    # Load recent conversation — keep the last 20 turns so Claude has real memory.
    history = chat_service.list_messages(db, session)
    history = [m for m in history if m.role != MessageRole.SYSTEM]
    history = history[-20:]

    messages_for_claude: list[dict] = [
        {"role": m.role.value, "content": m.content} for m in history
    ]

    # Build the system prompt: fixed instructions + FILLED/MISSING summary + raw JSON snapshot
    current = resume.content or {}
    fill_summary = _summarize_filled_missing(current)
    snapshot = json.dumps(current, ensure_ascii=False, indent=2)
    system_prompt = (
        f"{RESUME_COACH_SYSTEM}\n\n"
        f"=== FILLED / MISSING SUMMARY ===\n{fill_summary}\n\n"
        f"=== CURRENT RESUME STATE (JSON) ===\n{snapshot}\n"
        f"=== END OF STATE ==="
    )

    # Use the multi-turn helper so Claude sees the full conversation history
    raw = claude_client.generate_completion_multiturn(
        system=system_prompt,
        messages=messages_for_claude,
        max_tokens=900,
        temperature=0.5,
    )

    if not raw:
        raise HTTPException(
            status_code=502,
            detail="Resume Coach returned an empty response. Try again.",
        )

    try:
        data = _parse_first_json_object(raw)
    except json.JSONDecodeError:
        # Best-effort fallback: persist the raw text as the assistant reply,
        # don't apply any patch.
        chat_service.add_message(db, session, MessageRole.ASSISTANT, raw)
        return ChatStepResult(
            ai_message=raw,
            content=ResumeContent(**(resume.content or {})),
            patch_applied=False,
        )

    ai_reply = (data.get("ai_reply") or "").strip() or "Got it. What's next?"
    patch = data.get("patch") or {}
    if not isinstance(patch, dict):
        patch = {}

    patch_applied = False
    if patch:
        merged = _deep_merge_patch(resume.content or {}, patch)
        try:
            validated = ResumeContent(**merged)
            resume.content = validated.model_dump()
            patch_applied = True
        except Exception as e:
            # Log the full failing patch so we can see what Claude returned
            logger.warning(
                "Resume patch validation failed (full patch): %s\nPatch keys: %s",
                e,
                list(patch.keys()),
            )
            # ── Partial recovery ──
            # Try each top-level key in isolation. Valid sub-sections still
            # land even if one key has bad data — no more losing projects
            # because education malformed a year as an int.
            any_applied = False
            current = dict(resume.content or {})
            for key, value in patch.items():
                attempt = _deep_merge_patch(current, {key: value})
                try:
                    validated = ResumeContent(**attempt)
                    current = validated.model_dump()
                    any_applied = True
                except Exception as sub_e:
                    logger.warning(
                        "Dropping invalid patch subkey %s: %s",
                        key,
                        str(sub_e)[:300],
                    )
            if any_applied:
                resume.content = current
                patch_applied = True

    db.flush()

    # Persist assistant reply
    chat_service.add_message(db, session, MessageRole.ASSISTANT, ai_reply)

    # Award XP for keeping the resume warm — small drip per turn so it adds up
    if patch_applied:
        try:
            xp.award_xp(
                db,
                user,
                XPEventType.RESUME_UPDATED,
                reference_id=resume.id,
                base_override=8,
            )
        except Exception as e:
            logger.warning("XP award (resume) failed: %s", e)

    db.commit()
    db.refresh(resume)

    return ChatStepResult(
        ai_message=ai_reply,
        content=ResumeContent(**(resume.content or {})),
        patch_applied=patch_applied,
    )


# ════════════════════════════════════════════════════════════════
# ATS scoring
# ════════════════════════════════════════════════════════════════

def score_against_jd(
    db: Session,
    user: User,
    *,
    job_description: str,
) -> ATSScoreResponse:
    _require_student(user)
    if not claude_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="ATS scorer unavailable: ANTHROPIC_API_KEY is not configured.",
        )

    resume = get_or_create_resume(db, user)
    snapshot = json.dumps(resume.content or {}, ensure_ascii=False, indent=2)

    user_message = (
        f"=== RESUME JSON ===\n{snapshot}\n\n"
        f"=== JOB DESCRIPTION ===\n{job_description}\n"
    )

    raw = claude_client.generate_completion(
        system=ATS_SCORER_SYSTEM,
        user_message=user_message,
        max_tokens=900,
        temperature=0.2,
    )
    if not raw:
        raise HTTPException(status_code=502, detail="ATS scorer returned an empty response")

    try:
        data = _parse_first_json_object(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=502, detail=f"ATS scorer returned invalid JSON: {e}"
        ) from e

    score = float(data.get("score") or 0)
    score = max(0.0, min(100.0, round(score, 1)))
    matched = [str(s) for s in (data.get("matched_keywords") or [])][:12]
    missing = [str(s) for s in (data.get("missing_keywords") or [])][:10]
    suggestions = [str(s) for s in (data.get("suggestions") or [])][:5]

    # Persist the latest score on the resume row
    from decimal import Decimal

    resume.ats_score = Decimal(f"{score:.2f}")
    resume.last_job_description = job_description[:8000]
    db.commit()

    return ATSScoreResponse(
        score=score,
        matched_keywords=matched,
        missing_keywords=missing,
        suggestions=suggestions,
    )


# ════════════════════════════════════════════════════════════════
# GitHub import
# ════════════════════════════════════════════════════════════════

def import_github_projects(
    db: Session,
    user: User,
    *,
    username: str,
    top_n: int = 5,
) -> tuple[list[GitHubProjectImport], ResumeContent]:
    _require_student(user)

    repos: list[GitHubRepo] = fetch_top_repos(username, top_n=top_n)
    if not repos:
        return [], ResumeContent(**(get_or_create_resume(db, user).content or {}))

    resume = get_or_create_resume(db, user)
    content = ResumeContent(**(resume.content or {}))

    # Skip duplicates by URL
    existing_urls = {p.url for p in content.projects if p.url}
    new_projects: list[ResumeProject] = []
    imported: list[GitHubProjectImport] = []

    for repo in repos:
        if repo.url in existing_urls:
            continue
        new_projects.append(
            ResumeProject(
                name=repo.name,
                description=repo.description or f"Public GitHub project — {repo.stars}★",
                tech=repo.tech,
                url=repo.url,
                highlights=[
                    f"{repo.stars} GitHub stars" if repo.stars else "Open source on GitHub",
                ],
            )
        )
        imported.append(
            GitHubProjectImport(
                name=repo.name,
                description=repo.description,
                tech=repo.tech,
                url=repo.url,
                stars=repo.stars,
            )
        )

    if not imported:
        return [], content

    content.projects = list(content.projects) + new_projects
    resume.content = content.model_dump()
    if not (content.personal.github):
        content.personal.github = f"https://github.com/{username}"
        resume.content = content.model_dump()

    db.commit()
    db.refresh(resume)

    # Tiny XP nudge
    try:
        xp.award_xp(
            db,
            user,
            XPEventType.RESUME_UPDATED,
            reference_id=resume.id,
            base_override=15,
        )
        db.commit()
    except Exception as e:
        logger.warning("XP award (github import) failed: %s", e)

    return imported, ResumeContent(**(resume.content or {}))
