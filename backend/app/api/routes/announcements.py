"""Announcement endpoints (Phase 13)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_role
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.services import announcement as announcement_service

router = APIRouter()


@router.get(
    "/",
    response_model=list[AnnouncementResponse],
    summary="List announcements visible to the current user",
)
def list_announcements(
    db: DbSession,
    current_user: CurrentUser,
    subject_id: uuid.UUID | None = None,
    only_mine: bool = False,
    limit: int = 50,
) -> list[AnnouncementResponse]:
    return announcement_service.list_announcements(
        db,
        current_user,
        subject_id=subject_id,
        only_mine=only_mine,
        limit=limit,
    )


@router.post(
    "/",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Create a new announcement",
)
def create_announcement(
    data: AnnouncementCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> AnnouncementResponse:
    return announcement_service.create_announcement(db, data, current_user)


@router.patch(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Edit an announcement (author only)",
)
def update_announcement(
    announcement_id: uuid.UUID,
    data: AnnouncementUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AnnouncementResponse:
    return announcement_service.update_announcement(
        db, announcement_id, data, current_user
    )


@router.delete(
    "/{announcement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Delete an announcement (author only)",
)
def delete_announcement(
    announcement_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    announcement_service.delete_announcement(db, announcement_id, current_user)
