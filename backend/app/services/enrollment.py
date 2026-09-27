"""Per-subject enrollment — the teacher's roster.

A teacher adds a student (by username) to one of her subjects. Enrolled students
see that subject's quizzes + announcements; non-enrolled students don't. The
gate helpers at the bottom (`enrolled_subject_ids_for_student`, etc.) are imported
by quiz / announcement / task-feed / dashboard to filter content.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import StudentProfile, Subject, SubjectEnrollment, User, UserRole


# ──────────────────────────────────────────────────────────────────
# Teacher-facing roster operations
# ──────────────────────────────────────────────────────────────────


def _require_owned_subject(db: Session, teacher: User, subject_id: uuid.UUID) -> Subject:
    """Load a public subject the teacher owns (admins may manage any)."""
    subject = db.get(Subject, subject_id)
    if subject is None or subject.owner_student_id is not None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if teacher.role != UserRole.ADMIN and subject.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="You don't own this subject")
    return subject


def _find_student_by_username(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.student_profile))
        .where(User.username == username.strip().lower())
    )


def _student_row(student: User, enrolled_at) -> dict:
    sp = student.student_profile
    return {
        "student_id": student.id,
        "username": student.username,
        "full_name": student.full_name,
        "email": student.email,
        "branch": sp.branch if sp else None,
        "semester": sp.semester if sp else None,
        "enrolled_at": enrolled_at,
    }


def enroll_student(db: Session, teacher: User, subject_id: uuid.UUID, username: str) -> dict:
    """Add a student (by username) to a subject. Idempotent."""
    _require_owned_subject(db, teacher, subject_id)

    student = _find_student_by_username(db, username)
    if student is None:
        raise HTTPException(status_code=404, detail=f"No user with username '{username.strip().lower()}'")
    if student.role != UserRole.STUDENT:
        raise HTTPException(status_code=400, detail="That account is not a student")

    existing = db.scalar(
        select(SubjectEnrollment).where(
            SubjectEnrollment.subject_id == subject_id,
            SubjectEnrollment.student_id == student.id,
        )
    )
    if existing is None:
        enrollment = SubjectEnrollment(subject_id=subject_id, student_id=student.id)
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return _student_row(student, enrollment.enrolled_at)
    return _student_row(student, existing.enrolled_at)


def unenroll_student(db: Session, teacher: User, subject_id: uuid.UUID, student_id: uuid.UUID) -> None:
    """Remove a student from a subject. Idempotent."""
    _require_owned_subject(db, teacher, subject_id)
    enrollment = db.scalar(
        select(SubjectEnrollment).where(
            SubjectEnrollment.subject_id == subject_id,
            SubjectEnrollment.student_id == student_id,
        )
    )
    if enrollment is not None:
        db.delete(enrollment)
        db.commit()


def list_roster(db: Session, teacher: User, subject_id: uuid.UUID) -> dict:
    """The enrolled students for one subject (newest first)."""
    subject = _require_owned_subject(db, teacher, subject_id)
    rows = db.execute(
        select(SubjectEnrollment, User, StudentProfile)
        .join(User, User.id == SubjectEnrollment.student_id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(SubjectEnrollment.subject_id == subject_id)
        .order_by(SubjectEnrollment.enrolled_at.desc())
    ).all()
    students = []
    for enrollment, user, sp in rows:
        students.append(
            {
                "student_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "branch": sp.branch if sp else None,
                "semester": sp.semester if sp else None,
                "enrolled_at": enrollment.enrolled_at,
            }
        )
    return {
        "subject_id": subject.id,
        "subject_code": subject.code,
        "subject_name": subject.name,
        "students": students,
    }


def list_my_subjects_with_counts(db: Session, teacher: User) -> list[dict]:
    """The teacher's public subjects + their enrolled-student counts (for the
    roster page's subject picker)."""
    subjects = list(
        db.scalars(
            select(Subject)
            .where(Subject.teacher_id == teacher.id, Subject.owner_student_id.is_(None))
            .order_by(Subject.created_at.desc())
        ).all()
    )
    count_rows = db.execute(
        select(SubjectEnrollment.subject_id, func.count())
        .group_by(SubjectEnrollment.subject_id)
    ).all()
    counts = {sid: c for sid, c in count_rows}
    return [
        {
            "subject_id": s.id,
            "code": s.code,
            "name": s.name,
            "student_count": counts.get(s.id, 0),
        }
        for s in subjects
    ]


# ──────────────────────────────────────────────────────────────────
# Gate helpers (imported by quiz / announcement / task_feed / dashboard)
# ──────────────────────────────────────────────────────────────────


def enrolled_subject_ids_for_student(db: Session, student_id: uuid.UUID) -> set[uuid.UUID]:
    """The set of subject ids a student is enrolled in."""
    return set(
        db.scalars(
            select(SubjectEnrollment.subject_id).where(
                SubjectEnrollment.student_id == student_id
            )
        ).all()
    )


def enrolled_student_ids_for_subject(db: Session, subject_id: uuid.UUID) -> list[uuid.UUID]:
    """The student ids enrolled in a subject (for announcement fan-out)."""
    return list(
        db.scalars(
            select(SubjectEnrollment.student_id).where(
                SubjectEnrollment.subject_id == subject_id
            )
        ).all()
    )


def enrolled_student_count_for_teacher(db: Session, teacher_id: uuid.UUID) -> int:
    """Distinct students enrolled across all of a teacher's subjects."""
    return (
        db.scalar(
            select(func.count(func.distinct(SubjectEnrollment.student_id)))
            .join(Subject, Subject.id == SubjectEnrollment.subject_id)
            .where(Subject.teacher_id == teacher_id)
        )
        or 0
    )
