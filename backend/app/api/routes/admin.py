"""Admin-only endpoints (Phase 4 wiring) — user management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, require_role
from app.schemas.dashboard import AdminUserListResponse
from app.services import dashboard as dashboard_service

router = APIRouter()


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    dependencies=[Depends(require_role("admin"))],
    summary="Admin: list all platform users (filterable, searchable)",
)
def list_users(
    db: DbSession,
    current_user: CurrentUser,
    role: str | None = Query(None, description="student | teacher | admin | all"),
    search: str | None = Query(None, description="Match against name or email"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AdminUserListResponse:
    return dashboard_service.list_users(
        db,
        current_user,
        role=role,
        search=search,
        limit=limit,
        offset=offset,
    )
