"""Teacher analytics endpoints (Phase 13)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_role
from app.schemas.analytics import ClassAnalytics
from app.services import analytics as analytics_service

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
