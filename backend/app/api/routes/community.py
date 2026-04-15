"""Peer Doubt Community endpoints (Phase 17, F4)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.community import (
    DoubtAnswerCreate,
    DoubtAnswerResponse,
    DoubtCreate,
    DoubtDetailResponse,
    DoubtResponse,
)
from app.services import community

router = APIRouter()


# ── Doubts ──

@router.get(
    "/",
    response_model=list[DoubtResponse],
    summary="List doubts (newest first) — filterable by tag or search",
)
def list_doubts(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    tag: str | None = None,
    only_mine: bool = False,
    limit: int = 50,
) -> list[DoubtResponse]:
    return community.list_doubts(
        db,
        current_user,
        search=search,
        tag=tag,
        only_mine=only_mine,
        limit=limit,
    )


@router.post(
    "/",
    response_model=DoubtResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ask a new doubt",
)
def create_doubt(
    data: DoubtCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> DoubtResponse:
    return community.create_doubt(db, current_user, data)


@router.get(
    "/{doubt_id}",
    response_model=DoubtDetailResponse,
    summary="Get a doubt with all its answers (may trigger AI fallback)",
)
def get_doubt(
    doubt_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DoubtDetailResponse:
    return community.get_doubt(db, current_user, doubt_id)


@router.post(
    "/{doubt_id}/upvote",
    response_model=DoubtResponse,
    summary="Upvote a doubt",
)
def upvote_doubt(
    doubt_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DoubtResponse:
    return community.upvote_doubt(db, current_user, doubt_id)


@router.delete(
    "/{doubt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a doubt (author only)",
)
def delete_doubt(
    doubt_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    community.delete_doubt(db, current_user, doubt_id)


# ── Answers ──

@router.post(
    "/{doubt_id}/answers",
    response_model=DoubtAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a peer answer to a doubt",
)
def create_answer(
    doubt_id: uuid.UUID,
    data: DoubtAnswerCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> DoubtAnswerResponse:
    return community.create_answer(db, current_user, doubt_id, data)


@router.post(
    "/answers/{answer_id}/upvote",
    response_model=DoubtAnswerResponse,
    summary="Upvote an answer",
)
def upvote_answer(
    answer_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DoubtAnswerResponse:
    return community.upvote_answer(db, current_user, answer_id)


@router.post(
    "/answers/{answer_id}/accept",
    response_model=DoubtAnswerResponse,
    summary="Mark an answer as accepted (only the doubt's author can)",
)
def accept_answer(
    answer_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> DoubtAnswerResponse:
    return community.accept_answer(db, current_user, answer_id)
