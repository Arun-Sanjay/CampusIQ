"""Subject endpoints: CRUD for teacher-owned subjects + student notebooks."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
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
    summary=(
        "Create a new subject. Teachers/admins create public subjects "
        "(must supply `code`); students create personal notebooks (code "
        "auto-generated, visibility scoped to themselves)."
    ),
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
    summary="Update a subject (students can patch their own notebooks)",
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
    summary=(
        "Delete a subject. Students can delete their own notebooks; "
        "teachers/admins handle the public corpus."
    ),
)
def delete_subject(
    subject_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    subject_service.delete_subject(db, subject_id, current_user)
