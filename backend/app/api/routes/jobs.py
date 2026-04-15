"""Job Tracker endpoints (Phase 17, F12)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.jobs import (
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    JobBoardResponse,
    JobListingCreate,
    JobListingResponse,
)
from app.services import job_tracker

router = APIRouter()


# ── Listings ──

@router.get(
    "/",
    response_model=list[JobListingResponse],
    summary="List job postings (with fit scores for students)",
)
def list_jobs(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    limit: int = 100,
) -> list[JobListingResponse]:
    return job_tracker.list_listings(db, current_user, search=search, limit=limit)


@router.post(
    "/",
    response_model=JobListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job listing",
)
def create_job(
    data: JobListingCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> JobListingResponse:
    return job_tracker.create_listing(db, current_user, data)


@router.delete(
    "/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job listing (author only)",
)
def delete_job(
    listing_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    job_tracker.delete_listing(db, current_user, listing_id)


@router.post(
    "/seed",
    response_model=dict,
    summary="Seed the listings table with sample data (admin/teacher helper)",
)
def seed_sample_listings(
    db: DbSession, current_user: CurrentUser
) -> dict:
    added = job_tracker.seed_sample_listings_if_empty(db, current_user)
    return {"seeded": added}


# ── Applications ──

@router.get(
    "/me/board",
    response_model=JobBoardResponse,
    summary="Kanban view of my tracked applications",
)
def get_my_board(
    db: DbSession, current_user: CurrentUser
) -> JobBoardResponse:
    return job_tracker.list_my_board(db, current_user)


@router.post(
    "/me/applications",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save or update an application for a job listing",
)
def save_application(
    data: JobApplicationCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> JobApplicationResponse:
    return job_tracker.save_or_update_application(db, current_user, data)


@router.patch(
    "/me/applications/{application_id}",
    response_model=JobApplicationResponse,
    summary="Move an application to a new status or update notes",
)
def update_application(
    application_id: uuid.UUID,
    data: JobApplicationUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> JobApplicationResponse:
    return job_tracker.update_application(db, current_user, application_id, data)


@router.delete(
    "/me/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an application from my board",
)
def delete_application(
    application_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    job_tracker.delete_application(db, current_user, application_id)
