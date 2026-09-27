"""Enrollment endpoints — the teacher manages each subject's student roster.

All routes are teacher/admin only. A teacher adds a student to one of her
subjects by username; enrolled students then see that subject's quizzes +
announcements.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_role
from app.schemas.enrollment import (
    EnrolledStudent,
    EnrollRequest,
    SubjectRoster,
    TeacherSubjectCount,
)
from app.services import enrollment as enrollment_service

router = APIRouter(dependencies=[Depends(require_role("teacher", "admin"))])


@router.get(
    "/my-subjects",
    response_model=list[TeacherSubjectCount],
    summary="The teacher's subjects with enrolled-student counts",
)
def my_subjects(db: DbSession, current_user: CurrentUser) -> list[TeacherSubjectCount]:
    return [
        TeacherSubjectCount(**row)
        for row in enrollment_service.list_my_subjects_with_counts(db, current_user)
    ]


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectRoster,
    summary="Enrolled students for one subject",
)
def get_roster(subject_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> SubjectRoster:
    return SubjectRoster(**enrollment_service.list_roster(db, current_user, subject_id))


@router.post(
    "/subjects/{subject_id}",
    response_model=EnrolledStudent,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student in a subject by username",
)
def enroll(
    subject_id: uuid.UUID,
    data: EnrollRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> EnrolledStudent:
    return EnrolledStudent(
        **enrollment_service.enroll_student(db, current_user, subject_id, data.username)
    )


@router.delete(
    "/subjects/{subject_id}/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a student from a subject",
)
def unenroll(
    subject_id: uuid.UUID,
    student_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    enrollment_service.unenroll_student(db, current_user, subject_id, student_id)
