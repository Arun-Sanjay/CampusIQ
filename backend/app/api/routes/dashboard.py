"""Student dashboard endpoint (Phase 12)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.user import UserRole
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard as dashboard_service

router = APIRouter()


@router.get(
    "/me",
    response_model=DashboardResponse,
    summary="Student: full dashboard payload (XP, score, task feed, activity)",
)
def my_dashboard(db: DbSession, current_user: CurrentUser) -> DashboardResponse:
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students have a dashboard. Teachers and admins use their own views.",
        )
    return dashboard_service.get_student_dashboard(db, current_user)
