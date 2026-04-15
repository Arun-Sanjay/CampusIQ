"""Subject service: CRUD scoped to the owning teacher."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.user import Document, Subject, User, UserRole
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate


def _require_teacher_or_admin(user: User) -> None:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can manage subjects.",
        )


def _to_response(subject: Subject, *, document_count: int = 0, quiz_count: int = 0) -> SubjectResponse:
    return SubjectResponse(
        id=subject.id,
        teacher_id=subject.teacher_id,
        college_id=subject.college_id,
        code=subject.code,
        name=subject.name,
        description=subject.description,
        semester=subject.semester,
        branch=subject.branch,
        created_at=subject.created_at,
        document_count=document_count,
        quiz_count=quiz_count,
        student_count=0,  # enrollment tracking comes later
    )


def _counts_for(db: Session, subject_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    """Return {subject_id: (document_count, quiz_count)} for a list of ids."""
    if not subject_ids:
        return {}
    doc_counts = dict(
        db.execute(
            select(Document.subject_id, func.count(Document.id))
            .where(Document.subject_id.in_(subject_ids))
            .group_by(Document.subject_id)
        ).all()
    )
    quiz_counts = dict(
        db.execute(
            select(Quiz.subject_id, func.count(Quiz.id))
            .where(Quiz.subject_id.in_(subject_ids))
            .group_by(Quiz.subject_id)
        ).all()
    )
    return {
        sid: (doc_counts.get(sid, 0), quiz_counts.get(sid, 0))
        for sid in subject_ids
    }


def list_subjects_for_user(db: Session, user: User) -> list[SubjectResponse]:
    """Return subjects visible to the current user.

    - Teachers: only subjects they own
    - Admins: all subjects
    - Students: all subjects (read-only) so they can pick one in the Note Assistant
    """
    stmt = select(Subject).order_by(Subject.created_at.desc())

    if user.role == UserRole.TEACHER:
        stmt = stmt.where(Subject.teacher_id == user.id)
    # admins + students see everything

    subjects = db.scalars(stmt).all()
    counts = _counts_for(db, [s.id for s in subjects])
    return [
        _to_response(
            s,
            document_count=counts.get(s.id, (0, 0))[0],
            quiz_count=counts.get(s.id, (0, 0))[1],
        )
        for s in subjects
    ]


# Backwards-compat alias — keep the old name working for any route still using it
list_subjects_for_teacher = list_subjects_for_user


def get_subject(db: Session, subject_id: uuid.UUID, user: User) -> SubjectResponse:
    """Fetch a single subject — must be owned by the requesting teacher."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    if user.role == UserRole.TEACHER and subject.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this subject")

    counts = _counts_for(db, [subject.id])
    dc, qc = counts.get(subject.id, (0, 0))
    return _to_response(subject, document_count=dc, quiz_count=qc)


def create_subject(db: Session, data: SubjectCreate, teacher: User) -> SubjectResponse:
    """Create a new subject owned by the current teacher."""
    _require_teacher_or_admin(teacher)

    # Uniqueness check on code
    existing = db.scalar(select(Subject).where(Subject.code == data.code))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subject code '{data.code}' is already in use.",
        )

    subject = Subject(
        teacher_id=teacher.id,
        college_id=teacher.college_id,
        code=data.code.strip(),
        name=data.name.strip(),
        description=data.description,
        semester=data.semester,
        branch=data.branch,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _to_response(subject)


def update_subject(
    db: Session,
    subject_id: uuid.UUID,
    data: SubjectUpdate,
    user: User,
) -> SubjectResponse:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if user.role == UserRole.TEACHER and subject.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this subject")

    patch = data.model_dump(exclude_unset=True)
    for field, value in patch.items():
        setattr(subject, field, value)

    db.commit()
    db.refresh(subject)
    counts = _counts_for(db, [subject.id])
    dc, qc = counts.get(subject.id, (0, 0))
    return _to_response(subject, document_count=dc, quiz_count=qc)


def delete_subject(db: Session, subject_id: uuid.UUID, user: User) -> None:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if user.role == UserRole.TEACHER and subject.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this subject")

    db.delete(subject)
    db.commit()
