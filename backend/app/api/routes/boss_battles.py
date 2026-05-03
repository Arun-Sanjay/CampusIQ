"""Boss Battles endpoints (Phase 10)."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.services import boss_battles as boss_battles_service

router = APIRouter()


class BattleSubmitRequest(BaseModel):
    answers: dict[str, str]
    elapsed_seconds: int


@router.get("/", summary="List boss battles bucketed by status")
def list_battles(db: DbSession, current_user: CurrentUser) -> dict[str, Any]:
    return boss_battles_service.list_battles(db, current_user)


@router.get("/{battle_id}", summary="Get a boss battle with leaderboard")
def get_battle(
    db: DbSession, current_user: CurrentUser, battle_id: uuid.UUID
) -> dict[str, Any]:
    return boss_battles_service.get_battle_with_leaderboard(db, battle_id, current_user)


@router.post("/{battle_id}/submit", summary="Submit answers for a boss battle")
def submit_battle(
    db: DbSession,
    current_user: CurrentUser,
    battle_id: uuid.UUID,
    payload: BattleSubmitRequest,
) -> dict[str, Any]:
    return boss_battles_service.submit_battle(
        db,
        current_user,
        battle_id=battle_id,
        answers=payload.answers,
        elapsed_seconds=payload.elapsed_seconds,
    )
