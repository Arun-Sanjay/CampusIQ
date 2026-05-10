"""Subject service.

Subjects come in two flavours now:

- **Public teacher subjects** (`owner_student_id IS NULL`) — created by a
  teacher/admin, visible to every student. Current Subject behavior.
- **Private student notebooks** (`owner_student_id = <student>.id`) — created
  by a student, visible only to that student. Used by the NotebookLM-style
  personal-notes flow on the AI Note Assistant.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.user import Document, Subject, User, UserRole
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate


def _to_response(subject: Subject, *, document_count: int = 0, quiz_count: int = 0) -> SubjectResponse:
    return SubjectResponse(
        id=subject.id,
        teacher_id=subject.teacher_id,
        owner_student_id=subject.owner_student_id,
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


def _can_manage_subject(subject: Subject, user: User) -> bool:
    """True iff `user` can edit / delete this subject row.

    - Admins manage anything.
    - Teachers manage their own teacher subjects.
    - Students manage their own private notebooks (owner_student_id == self).
    """
    if user.role == UserRole.ADMIN:
        return True
    if subject.owner_student_id is not None:
        return subject.owner_student_id == user.id
    return subject.teacher_id == user.id


def _generate_personal_subject_code(name: str) -> str:
    """Build a unique-by-construction code for a student-created notebook.

    Format: `note-<8hex>` (e.g. `note-a3f01c92`). We don't try to honour the
    user's preferred course code because students don't have one and the
    column has a global UNIQUE constraint.
    """
    _ = name  # the slug doesn't depend on the name, but we keep it for callers
    return f"note-{uuid.uuid4().hex[:8]}"


def list_subjects_for_user(db: Session, user: User) -> list[SubjectResponse]:
    """Return subjects visible to the current user.

    - Admins: all subjects.
    - Teachers: subjects they own (private student notebooks are hidden).
    - Students: every public teacher subject + their own private notebooks.
    """
    stmt = select(Subject).order_by(Subject.created_at.desc())

    if user.role == UserRole.TEACHER:
        stmt = stmt.where(Subject.teacher_id == user.id)
        stmt = stmt.where(Subject.owner_student_id.is_(None))
    elif user.role == UserRole.STUDENT:
        stmt = stmt.where(
            or_(
                Subject.owner_student_id.is_(None),
                Subject.owner_student_id == user.id,
            )
        )
    # admins: see all

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


# Backwards-compat alias — keep the old name working for any caller still using it
list_subjects_for_teacher = list_subjects_for_user


def get_subject(db: Session, subject_id: uuid.UUID, user: User) -> SubjectResponse:
    """Fetch a single subject. 404s rather than 403s when a student tries to
    peek at someone else's private notebook (so private ids aren't enumerable)."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    if subject.owner_student_id is not None:
        # Private notebook — only the owner and admins can see it.
        if user.role != UserRole.ADMIN and subject.owner_student_id != user.id:
            raise HTTPException(status_code=404, detail="Subject not found")
    elif user.role == UserRole.TEACHER and subject.teacher_id != user.id:
        # Public subject owned by a different teacher — teachers can only
        # read their own teacher subjects.
        raise HTTPException(status_code=403, detail="You don't own this subject")

    counts = _counts_for(db, [subject.id])
    dc, qc = counts.get(subject.id, (0, 0))
    return _to_response(subject, document_count=dc, quiz_count=qc)


def create_subject(db: Session, data: SubjectCreate, user: User) -> SubjectResponse:
    """Create a new subject.

    - Teachers / admins → a public subject. The supplied `code` is required
      and must be unique.
    - Students → a personal notebook scoped to themselves. The `code` is
      optional and auto-generated when missing.
    """
    if user.role not in (UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't create subjects.",
        )

    is_personal = user.role == UserRole.STUDENT

    # Decide the code: required + unique for public subjects; auto for personal.
    if is_personal:
        if data.code and data.code.strip():
            raw = data.code.strip()
            existing = db.scalar(select(Subject).where(Subject.code == raw))
            if existing is not None:
                code = _generate_personal_subject_code(data.name)
            else:
                code = raw
        else:
            code = _generate_personal_subject_code(data.name)
        # Defensive: in the (astronomical) chance the auto-code collides, retry.
        for _ in range(5):
            if db.scalar(select(Subject).where(Subject.code == code)) is None:
                break
            code = _generate_personal_subject_code(data.name)
    else:
        if not data.code or not data.code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teachers must provide a subject code.",
            )
        code = data.code.strip()
        existing = db.scalar(select(Subject).where(Subject.code == code))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subject code '{code}' is already in use.",
            )

    subject = Subject(
        teacher_id=user.id,
        owner_student_id=user.id if is_personal else None,
        college_id=user.college_id,
        code=code,
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
    if not _can_manage_subject(subject, user):
        # Hide existence for private notebooks owned by another student.
        if subject.owner_student_id is not None and user.role != UserRole.ADMIN:
            raise HTTPException(status_code=404, detail="Subject not found")
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
    if not _can_manage_subject(subject, user):
        if subject.owner_student_id is not None and user.role != UserRole.ADMIN:
            raise HTTPException(status_code=404, detail="Subject not found")
        raise HTTPException(status_code=403, detail="You don't own this subject")

    db.delete(subject)
    db.commit()
