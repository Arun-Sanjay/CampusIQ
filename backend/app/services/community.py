"""Peer Doubt Community service (Phase 17, F4).

Students post doubts → peers answer → upvotes + accepted answers.

**AI fallback**: when a doubt has zero human answers and has been sitting
for ≥ `AI_FALLBACK_DELAY_MINUTES` minutes, the next time anyone opens the
doubt via `get_doubt()` we generate a Claude-backed answer and persist it
as an AI-authored answer. This keeps the fallback lazy (no background
scheduler needed) and only costs Claude calls for doubts that are actually
being read.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func as sqlfunc, select
from sqlalchemy.orm import Session, selectinload

from app.models.community import Doubt, DoubtAnswer
from app.models.gamification import XPEventType
from app.models.user import Subject, User, UserRole
from app.schemas.community import (
    DoubtAnswerCreate,
    DoubtAnswerResponse,
    DoubtCreate,
    DoubtDetailResponse,
    DoubtResponse,
)
from app.services import claude_client, xp

logger = logging.getLogger(__name__)


AI_FALLBACK_DELAY_MINUTES = 10


COMMUNITY_AI_SYSTEM = """You are CampusIQ Doubt Assistant — you step in to help when no classmate has answered a peer's doubt within 10 minutes.

You will be given the doubt's title, body, and tags. Write a clear, concise answer a strong senior student would give. 3-6 short paragraphs. If the doubt is about a concept, explain it step by step with a concrete example. If it's about an exam strategy or debugging tip, be practical.

Do not use markdown headings. Do not sign the post. Do not mention that you're an AI — the "AI Answered" badge on the frontend already makes that clear."""


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════

def _require_student(user: User) -> None:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The peer community is only available to students.",
        )


def _to_answer_response(
    answer: DoubtAnswer, author: User | None
) -> DoubtAnswerResponse:
    return DoubtAnswerResponse(
        id=answer.id,
        doubt_id=answer.doubt_id,
        answered_by_id=answer.answered_by_id,
        answered_by_name=(author.full_name if author else None),
        answer_text=answer.answer_text,
        is_ai_generated=answer.is_ai_generated,
        is_accepted=answer.is_accepted,
        upvote_count=answer.upvote_count,
        created_at=answer.created_at,
    )


def _to_doubt_response(
    doubt: Doubt,
    *,
    author: User | None,
    subject: Subject | None,
    answer_count: int,
    has_ai_answer: bool,
) -> DoubtResponse:
    return DoubtResponse(
        id=doubt.id,
        student_id=doubt.student_id,
        student_name=(author.full_name if author else None),
        subject_id=doubt.subject_id,
        subject_code=(subject.code if subject else None),
        title=doubt.title,
        body=doubt.body,
        tags=list(doubt.tags or []),
        is_resolved=doubt.is_resolved,
        upvote_count=doubt.upvote_count,
        view_count=doubt.view_count,
        answer_count=answer_count,
        has_ai_answer=has_ai_answer,
        created_at=doubt.created_at,
    )


# ════════════════════════════════════════════════════════════════
# CRUD — doubts
# ════════════════════════════════════════════════════════════════

def create_doubt(
    db: Session, user: User, data: DoubtCreate
) -> DoubtResponse:
    _require_student(user)
    doubt = Doubt(
        student_id=user.id,
        subject_id=data.subject_id,
        title=data.title.strip(),
        body=data.body.strip(),
        tags=list(data.tags or []),
    )
    db.add(doubt)
    db.commit()
    db.refresh(doubt)

    author = db.get(User, doubt.student_id)
    subject = db.get(Subject, doubt.subject_id) if doubt.subject_id else None
    return _to_doubt_response(
        doubt,
        author=author,
        subject=subject,
        answer_count=0,
        has_ai_answer=False,
    )


def list_doubts(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    tag: str | None = None,
    only_mine: bool = False,
    limit: int = 50,
) -> list[DoubtResponse]:
    stmt = (
        select(Doubt, User, Subject)
        .outerjoin(User, Doubt.student_id == User.id)
        .outerjoin(Subject, Doubt.subject_id == Subject.id)
        .order_by(Doubt.created_at.desc())
        .limit(limit)
    )
    if only_mine:
        stmt = stmt.where(Doubt.student_id == user.id)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(sqlfunc.lower(Doubt.title).like(like))
    rows = db.execute(stmt).all()
    doubts = [r[0] for r in rows]

    # Batch answer counts
    doubt_ids = [d.id for d in doubts]
    answer_counts: dict[uuid.UUID, int] = {}
    ai_flags: dict[uuid.UUID, bool] = {}
    if doubt_ids:
        count_rows = db.execute(
            select(DoubtAnswer.doubt_id, sqlfunc.count(DoubtAnswer.id))
            .where(DoubtAnswer.doubt_id.in_(doubt_ids))
            .group_by(DoubtAnswer.doubt_id)
        ).all()
        answer_counts = {row[0]: int(row[1]) for row in count_rows}

        ai_rows = db.execute(
            select(DoubtAnswer.doubt_id)
            .where(DoubtAnswer.doubt_id.in_(doubt_ids))
            .where(DoubtAnswer.is_ai_generated.is_(True))
        ).all()
        ai_flags = {row[0]: True for row in ai_rows}

    # Post-filter by tag (JSON list, hard to do server-side cleanly)
    if tag:
        rows = [r for r in rows if tag in (r[0].tags or [])]

    return [
        _to_doubt_response(
            d,
            author=u,
            subject=s,
            answer_count=answer_counts.get(d.id, 0),
            has_ai_answer=ai_flags.get(d.id, False),
        )
        for (d, u, s) in rows
    ]


def get_doubt(
    db: Session, user: User, doubt_id: uuid.UUID
) -> DoubtDetailResponse:
    """Fetch a doubt with all its answers. Triggers the AI fallback if the
    doubt is older than 10 minutes and still has zero human answers."""
    doubt = db.scalar(
        select(Doubt)
        .where(Doubt.id == doubt_id)
        .options(selectinload(Doubt.answers))
    )
    if doubt is None:
        raise HTTPException(status_code=404, detail="Doubt not found")

    # Bump view count
    doubt.view_count = (doubt.view_count or 0) + 1
    db.commit()

    # AI fallback — only if no human answer AND no existing AI answer AND old enough
    _maybe_generate_ai_fallback(db, doubt)
    db.refresh(doubt)

    author = db.get(User, doubt.student_id)
    subject = db.get(Subject, doubt.subject_id) if doubt.subject_id else None

    answers_sorted = sorted(
        doubt.answers or [],
        key=lambda a: (not a.is_accepted, -a.upvote_count, a.created_at),
    )

    answer_responses: list[DoubtAnswerResponse] = []
    for ans in answers_sorted:
        ans_author = db.get(User, ans.answered_by_id) if ans.answered_by_id else None
        answer_responses.append(_to_answer_response(ans, ans_author))

    base = _to_doubt_response(
        doubt,
        author=author,
        subject=subject,
        answer_count=len(doubt.answers or []),
        has_ai_answer=any(a.is_ai_generated for a in (doubt.answers or [])),
    )
    return DoubtDetailResponse(
        **base.model_dump(),
        answers=answer_responses,
    )


def upvote_doubt(
    db: Session, user: User, doubt_id: uuid.UUID
) -> DoubtResponse:
    doubt = db.get(Doubt, doubt_id)
    if doubt is None:
        raise HTTPException(status_code=404, detail="Doubt not found")
    doubt.upvote_count = (doubt.upvote_count or 0) + 1
    db.commit()
    db.refresh(doubt)
    author = db.get(User, doubt.student_id)
    subject = db.get(Subject, doubt.subject_id) if doubt.subject_id else None
    return _to_doubt_response(
        doubt,
        author=author,
        subject=subject,
        answer_count=len(doubt.answers or []),
        has_ai_answer=any(a.is_ai_generated for a in (doubt.answers or [])),
    )


def delete_doubt(db: Session, user: User, doubt_id: uuid.UUID) -> None:
    doubt = db.get(Doubt, doubt_id)
    if doubt is None:
        raise HTTPException(status_code=404, detail="Doubt not found")
    if doubt.student_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this doubt")
    db.delete(doubt)
    db.commit()


# ════════════════════════════════════════════════════════════════
# Answers
# ════════════════════════════════════════════════════════════════

def create_answer(
    db: Session, user: User, doubt_id: uuid.UUID, data: DoubtAnswerCreate
) -> DoubtAnswerResponse:
    _require_student(user)
    doubt = db.get(Doubt, doubt_id)
    if doubt is None:
        raise HTTPException(status_code=404, detail="Doubt not found")
    answer = DoubtAnswer(
        doubt_id=doubt.id,
        answered_by_id=user.id,
        answer_text=data.answer_text.strip(),
        is_ai_generated=False,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    # XP drip for answering a peer's doubt
    try:
        xp.award_xp(db, user, XPEventType.DOUBT_ANSWERED, reference_id=doubt.id)
        db.commit()
    except Exception as e:
        logger.warning("XP award (doubt answered) failed: %s", e)

    return _to_answer_response(answer, user)


def upvote_answer(
    db: Session, user: User, answer_id: uuid.UUID
) -> DoubtAnswerResponse:
    answer = db.get(DoubtAnswer, answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    answer.upvote_count = (answer.upvote_count or 0) + 1
    db.commit()
    db.refresh(answer)

    if answer.answered_by_id and answer.answered_by_id != user.id:
        author = db.get(User, answer.answered_by_id)
        if author is not None:
            try:
                xp.award_xp(
                    db, author, XPEventType.DOUBT_UPVOTED, reference_id=answer.id
                )
                db.commit()
            except Exception as e:
                logger.warning("XP award (doubt upvoted) failed: %s", e)

    ans_author = db.get(User, answer.answered_by_id) if answer.answered_by_id else None
    return _to_answer_response(answer, ans_author)


def accept_answer(
    db: Session, user: User, answer_id: uuid.UUID
) -> DoubtAnswerResponse:
    answer = db.get(DoubtAnswer, answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    doubt = db.get(Doubt, answer.doubt_id)
    if doubt is None:
        raise HTTPException(status_code=404, detail="Doubt not found")
    if doubt.student_id != user.id:
        raise HTTPException(
            status_code=403, detail="Only the doubt's author can accept an answer"
        )

    # Unaccept any previously accepted answers on this doubt
    db.execute(
        DoubtAnswer.__table__.update()
        .where(DoubtAnswer.doubt_id == doubt.id)
        .values(is_accepted=False)
    )
    answer.is_accepted = True
    doubt.is_resolved = True
    db.commit()
    db.refresh(answer)

    ans_author = db.get(User, answer.answered_by_id) if answer.answered_by_id else None
    return _to_answer_response(answer, ans_author)


# ════════════════════════════════════════════════════════════════
# AI fallback
# ════════════════════════════════════════════════════════════════

def _maybe_generate_ai_fallback(db: Session, doubt: Doubt) -> None:
    """Generate a Claude answer if the doubt has zero answers and is ≥ 10 min old."""
    if any(a.is_ai_generated for a in (doubt.answers or [])):
        return
    if any(not a.is_ai_generated for a in (doubt.answers or [])):
        return  # a human already replied
    age = datetime.now(timezone.utc) - _ensure_tz(doubt.created_at)
    if age < timedelta(minutes=AI_FALLBACK_DELAY_MINUTES):
        return
    if not claude_client.is_available():
        return

    tags = ", ".join(doubt.tags or []) if doubt.tags else "(none)"
    user_message = (
        f"Title: {doubt.title}\n"
        f"Tags: {tags}\n\n"
        f"Question:\n{doubt.body}\n"
    )
    answer_text = claude_client.generate_completion(
        system=COMMUNITY_AI_SYSTEM,
        user_message=user_message,
        max_tokens=600,
        temperature=0.5,
    )
    if not answer_text:
        return
    ai_answer = DoubtAnswer(
        doubt_id=doubt.id,
        answered_by_id=None,
        answer_text=answer_text,
        is_ai_generated=True,
    )
    db.add(ai_answer)
    db.commit()


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
