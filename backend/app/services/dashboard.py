"""Student dashboard aggregator (Phase 12).

Bundles XP / level / streak, CampusIQ score, basic stats, the heap-based task
feed, and a feed of recent XP events into a single response.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.gamification import XPEvent, XPEventType
from app.models.quiz import QuizAttempt
from app.models.user import User
from app.schemas.dashboard import (
    ActivityItem,
    CampusIQScoreBreakdown,
    DashboardResponse,
    DashboardStats,
    TaskItemResponse,
    XPProgress,
)
from app.services import announcement, campus_iq_score, task_feed, xp


# ── Friendly labels for XP event types ──
EVENT_LABELS: dict[XPEventType, str] = {
    XPEventType.QUIZ_COMPLETED: "Completed a quiz",
    XPEventType.MOCK_INTERVIEW_COMPLETED: "Finished a mock interview",
    XPEventType.DOUBT_ANSWERED: "Answered a community doubt",
    XPEventType.DOUBT_UPVOTED: "Got upvoted",
    XPEventType.RESUME_UPDATED: "Updated resume",
    XPEventType.CONFIDENCE_SESSION: "Confidence Coach session",
    XPEventType.SKILL_UNLOCKED: "Unlocked a skill",
    XPEventType.DAILY_LOGIN: "Daily login bonus",
    XPEventType.BADGE_EARNED: "Earned a badge",
}


def _xp_progress(user: User) -> XPProgress:
    profile = user.student_profile
    xp_total = (profile.xp_total if profile else 0) or 0
    streak_days = (profile.streak_days if profile else 0) or 0

    into_level, _floor, next_threshold = xp.xp_progress_to_next_level(xp_total)
    return XPProgress(
        xp_total=xp_total,
        current_level=xp.level_for_xp(xp_total),
        streak_days=streak_days,
        streak_multiplier=xp.streak_multiplier(streak_days),
        xp_into_level=into_level,
        next_level_threshold=next_threshold,
        xp_to_next_level=max(0, next_threshold - xp_total),
    )


def _quiz_stats(db: Session, user: User) -> DashboardStats:
    attempted = (
        db.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.student_id == user.id))
        or 0
    )
    passed = (
        db.scalar(
            select(func.count(QuizAttempt.id))
            .where(QuizAttempt.student_id == user.id)
            .where(QuizAttempt.score >= 60)
        )
        or 0
    )
    avg = db.scalar(
        select(func.avg(QuizAttempt.score)).where(QuizAttempt.student_id == user.id)
    )
    return DashboardStats(
        quizzes_attempted=int(attempted),
        quizzes_passed=int(passed),
        avg_quiz_score=float(avg) if avg is not None else None,
    )


def _recent_activity(db: Session, user: User, *, limit: int = 8) -> list[ActivityItem]:
    events = xp.recent_xp_events(db, user, limit=limit)
    return [
        ActivityItem(
            id=e.id,
            event_type=e.event_type.value,
            xp_earned=e.xp_earned,
            created_at=e.created_at,
            title=EVENT_LABELS.get(e.event_type, e.event_type.value.replace("_", " ").title()),
        )
        for e in events
    ]


def _to_task_response(task) -> TaskItemResponse:
    return TaskItemResponse(
        title=task.title,
        reason=task.reason,
        priority=task.priority,
        score=round(task.score, 2),
        kind=task.kind,
        action_url=task.action_url,
        quiz_id=task.quiz_id,
        subject_code=task.subject_code,
    )


def get_student_dashboard(db: Session, user: User) -> DashboardResponse:
    profile = user.student_profile
    score = campus_iq_score.get_or_create(db, user)
    db.commit()  # persist any score row created on first call
    db.refresh(user)

    return DashboardResponse(
        student_id=user.id,
        full_name=user.full_name,
        semester=profile.semester if profile else None,
        branch=profile.branch if profile else None,
        xp=_xp_progress(user),
        score=CampusIQScoreBreakdown(
            total=score.total,
            academic=score.academic,
            skill=score.skill,
            interview=score.interview,
            placement=score.placement,
            last_calculated_at=score.last_calculated_at,
        ),
        stats=_quiz_stats(db, user),
        tasks=[_to_task_response(t) for t in task_feed.build_task_feed(db, user)],
        recent_activity=_recent_activity(db, user),
        announcements=announcement.list_announcements(db, user, limit=5),
    )
