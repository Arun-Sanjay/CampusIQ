"""Grades read API: student transcript (own) + teacher class overview."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.user import User
from app.schemas.grades import ClassGradeOverview, TranscriptResponse
from app.services import grading as svc

router = APIRouter()


@router.get("/me", response_model=TranscriptResponse)
def my_transcript(db: DbSession, user: CurrentUser):
    """A student's own transcript: per-subject CIE/SEE + grade + per-CO, SGPA, CGPA."""
    return svc.student_transcript(db, user.id)


@router.get("/class", response_model=ClassGradeOverview)
def class_overview(
    subject_id: uuid.UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_role("teacher", "admin"))],
):
    """Teacher view: every enrolled student's grade + class CO attainment."""
    return svc.class_grade_overview(db, user, subject_id)
