"""Teacher analytics endpoints (Phase 13) + per-student detail (Phase 4 wiring)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_role
from app.schemas.analytics import ClassAnalytics
from app.schemas.dashboard import StudentDetailResponse
from app.services import analytics as analytics_service
from app.services import dashboard as dashboard_service

router = APIRouter()


@router.get(
    "/class",
    response_model=ClassAnalytics,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Class analytics — averages, weak topics, score distribution, per-student rows",
)
def get_class_analytics(
    db: DbSession,
    current_user: CurrentUser,
    subject_id: uuid.UUID | None = None,
) -> ClassAnalytics:
    return analytics_service.get_class_analytics(
        db, current_user, subject_id=subject_id
    )


@router.get(
    "/students/{student_id}",
    response_model=StudentDetailResponse,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Per-student detail: recent quiz scores, weak areas, engagement",
)
def get_student_detail(
    db: DbSession,
    current_user: CurrentUser,
    student_id: uuid.UUID,
) -> StudentDetailResponse:
    return dashboard_service.get_student_detail(db, current_user, student_id)
