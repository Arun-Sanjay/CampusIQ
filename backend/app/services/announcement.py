"""Announcement service (Phase 13).

Teachers post per-subject announcements; admins post college-wide ones.
Students read whatever is targeted at them — all-broadcast, their college,
or any subject they could see.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.algorithm import NotificationType
from app.models.content import Announcement, AnnouncementTarget
from app.models.user import Subject, User, UserRole
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════

def _to_response(
    announcement: Announcement,
    *,
    author: User | None,
    subject: Subject | None,
) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=announcement.id,
        author_id=announcement.author_id,
        author_name=author.full_name if author else None,
        subject_id=announcement.subject_id,
        subject_code=subject.code if subject else None,
        subject_name=subject.name if subject else None,
        college_id=announcement.college_id,
        title=announcement.title,
        body=announcement.body,
        target=announcement.target.value,
        created_at=announcement.created_at,
    )


def _validate_writer(user: User) -> None:
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers or admins can post announcements.",
        )


def _validate_subject_owner(db: Session, subject_id: uuid.UUID, user: User) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if user.role == UserRole.TEACHER and subject.teacher_id != user.id:
        raise HTTPException(
            status_code=403, detail="You don't own this subject"
        )
    return subject


# ════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════

def list_announcements(
    db: Session,
    user: User,
    *,
    subject_id: uuid.UUID | None = None,
    only_mine: bool = False,
    limit: int = 50,
) -> list[AnnouncementResponse]:
    """Return announcements visible to the current user.

    - Students: ALL-broadcasts, anything targeted at their college, anything
      targeted at any subject (Phase 13 doesn't enforce enrollment yet).
    - Teachers: their own announcements (filtered with `only_mine=True`) or
      every announcement matching the subject filter.
    - Admins: everything.
    """
    stmt = (
        select(Announcement, User, Subject)
        .outerjoin(User, Announcement.author_id == User.id)
        .outerjoin(Subject, Announcement.subject_id == Subject.id)
        .order_by(Announcement.created_at.desc())
        .limit(limit)
    )

    if subject_id is not None:
        stmt = stmt.where(Announcement.subject_id == subject_id)

    if user.role == UserRole.TEACHER:
        if only_mine or subject_id is None:
            stmt = stmt.where(Announcement.author_id == user.id)
    elif user.role == UserRole.STUDENT:
        # Students see all-broadcasts + college + any subject announcement
        clauses = [Announcement.target == AnnouncementTarget.ALL]
        if user.college_id is not None:
            clauses.append(Announcement.college_id == user.college_id)
        clauses.append(Announcement.target == AnnouncementTarget.SUBJECT)
        stmt = stmt.where(or_(*clauses))

    rows = db.execute(stmt).all()
    return [_to_response(a, author=u, subject=s) for a, u, s in rows]


def create_announcement(
    db: Session,
    data: AnnouncementCreate,
    user: User,
) -> AnnouncementResponse:
    _validate_writer(user)

    target = AnnouncementTarget(data.target)
    subject: Subject | None = None
    college_id: uuid.UUID | None = None

    if target == AnnouncementTarget.SUBJECT:
        if data.subject_id is None:
            raise HTTPException(
                status_code=400,
                detail="subject_id is required when target='subject'",
            )
        subject = _validate_subject_owner(db, data.subject_id, user)
    elif target == AnnouncementTarget.COLLEGE:
        college_id = user.college_id

    announcement = Announcement(
        author_id=user.id,
        subject_id=subject.id if subject else None,
        college_id=college_id,
        title=data.title.strip(),
        body=data.body.strip(),
        target=target,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    # Fan out a real-time notification to every student (Phase 9). Failures
    # here must never block the create flow.
    try:
        _notify_students(db, announcement, subject)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fan out notification for announcement %s", announcement.id)

    return _to_response(announcement, author=user, subject=subject)


def _notify_students(
    db: Session, announcement: Announcement, subject: Subject | None
) -> None:
    """Broadcast a NotificationDelivery row + WebSocket push to every student.

    Scope is intentionally simple — every student in the system gets the ping.
    Refining by college / subject enrollment is a v2 problem.
    """
    from app.services import notifications

    student_ids = list(
        db.scalars(select(User.id).where(User.role == UserRole.STUDENT)).all()
    )
    if not student_ids:
        return

    title = announcement.title
    body = announcement.body
    subject_label = subject.code if subject else None
    content = (
        f"[{subject_label}] {body}" if subject_label else body
    )
    extra = {
        "announcement_id": str(announcement.id),
        "subject_code": subject_label,
    }
    for sid in student_ids:
        notifications.publish_sync(
            db,
            user_id=sid,
            notification_type=NotificationType.ANNOUNCEMENT,
            title=title,
            content=content,
            extra=extra,
        )
    db.commit()


def update_announcement(
    db: Session,
    announcement_id: uuid.UUID,
    data: AnnouncementUpdate,
    user: User,
) -> AnnouncementResponse:
    _validate_writer(user)
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if user.role == UserRole.TEACHER and announcement.author_id != user.id:
        raise HTTPException(
            status_code=403, detail="You can only edit your own announcements"
        )

    if data.title is not None:
        announcement.title = data.title.strip()
    if data.body is not None:
        announcement.body = data.body.strip()

    db.commit()
    db.refresh(announcement)

    author = db.get(User, announcement.author_id)
    subject = db.get(Subject, announcement.subject_id) if announcement.subject_id else None
    return _to_response(announcement, author=author, subject=subject)


def delete_announcement(
    db: Session,
    announcement_id: uuid.UUID,
    user: User,
) -> None:
    _validate_writer(user)
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if user.role == UserRole.TEACHER and announcement.author_id != user.id:
        raise HTTPException(
            status_code=403, detail="You can only delete your own announcements"
        )
    db.delete(announcement)
    db.commit()
