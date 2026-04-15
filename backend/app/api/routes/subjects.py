"""Subject endpoints: CRUD for teacher-owned subjects."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_role
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.services import subject as subject_service

router = APIRouter()


@router.get(
    "/",
    response_model=list[SubjectResponse],
    summary="List subjects visible to the current user",
)
def list_subjects(db: DbSession, current_user: CurrentUser) -> list[SubjectResponse]:
    return subject_service.list_subjects_for_user(db, current_user)


@router.post(
    "/",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Create a new subject",
)
def create_subject(
    data: SubjectCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> SubjectResponse:
    return subject_service.create_subject(db, data, current_user)


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Get a single subject by ID",
)
def get_subject(
    subject_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> SubjectResponse:
    return subject_service.get_subject(db, subject_id, current_user)


@router.patch(
    "/{subject_id}",
    response_model=SubjectResponse,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Update a subject",
)
def update_subject(
    subject_id: uuid.UUID,
    data: SubjectUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SubjectResponse:
    return subject_service.update_subject(db, subject_id, data, current_user)


@router.delete(
    "/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("teacher", "admin"))],
    summary="Delete a subject (and cascade its documents + quizzes)",
)
def delete_subject(
    subject_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    subject_service.delete_subject(db, subject_id, current_user)
