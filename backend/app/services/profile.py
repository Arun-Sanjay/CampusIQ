"""Student profile service (Phase 18).

Provides the public profile view (shareable by URL) + self-service profile
updates + badge detection after XP events.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gamification import Badge
from app.models.placement import MockInterviewSession
from app.models.quiz import QuizAttempt
from app.models.user import StudentProfile, User, UserRole
from app.services import campus_iq_score, leaderboard

logger = logging.getLogger(__name__)


# ── Badge definitions ──
# Each badge has a `check` function that decides whether the student has
# earned it, plus static metadata. Lazy-evaluated after XP-earning events.

@dataclass
class BadgeDef:
    badge_type: str
    name: str
    description: str
    icon: str            # lucide icon name


BADGE_CATALOG: list[BadgeDef] = [
    BadgeDef(
        badge_type="first_quiz",
        name="First Quiz",
        description="Completed your first quiz",
        icon="CheckCircle2",
    ),
    BadgeDef(
        badge_type="quiz_streak_5",
        name="Quiz Streak ×5",
        description="Completed 5 quizzes",
        icon="Flame",
    ),
    BadgeDef(
        badge_type="quiz_streak_10",
        name="Quiz Streak ×10",
        description="Completed 10 quizzes",
        icon="Flame",
    ),
    BadgeDef(
        badge_type="first_interview",
        name="First Mock Interview",
        description="Finished your first mock interview",
        icon="MessageCircle",
    ),
    BadgeDef(
        badge_type="interview_pro",
        name="Interview Pro",
        description="Scored 75+ on a mock interview",
        icon="Swords",
    ),
    BadgeDef(
        badge_type="placement_ready",
        name="Placement Ready",
        description="Reached a CampusIQ score of 75+",
        icon="Award",
    ),
    BadgeDef(
        badge_type="level_10",
        name="Level 10 Achieved",
        description="Hit level 10 in the XP system",
        icon="Zap",
    ),
]


def _has_badge(db: Session, user_id: uuid.UUID, badge_type: str) -> bool:
    return db.scalar(
        select(Badge.id)
        .where(Badge.student_id == user_id)
        .where(Badge.badge_type == badge_type)
    ) is not None


def _award_badge(db: Session, user: User, defn: BadgeDef) -> Badge:
    badge = Badge(
        student_id=user.id,
        badge_type=defn.badge_type,
        badge_name=defn.name,
        description=defn.description,
        icon=defn.icon,
    )
    db.add(badge)
    return badge


def check_and_award_badges(db: Session, user: User) -> list[Badge]:
    """Scan all known badge thresholds for this student. Safe to call any time.

    Returns the list of NEWLY awarded badges so the caller can display them.
    """
    if user.role != UserRole.STUDENT:
        return []

    awarded: list[Badge] = []

    quiz_count = db.scalar(
        select(
            __import__("sqlalchemy", fromlist=["func"]).func.count(QuizAttempt.id)
        ).where(QuizAttempt.student_id == user.id)
    ) or 0
    quiz_count = int(quiz_count)

    def earn(bt: str) -> None:
        defn = next((b for b in BADGE_CATALOG if b.badge_type == bt), None)
        if defn is None:
            return
        if _has_badge(db, user.id, bt):
            return
        awarded.append(_award_badge(db, user, defn))

    if quiz_count >= 1:
        earn("first_quiz")
    if quiz_count >= 5:
        earn("quiz_streak_5")
    if quiz_count >= 10:
        earn("quiz_streak_10")

    # Interview badges
    from sqlalchemy import func as sqlfunc
    completed_interviews = db.scalar(
        select(sqlfunc.count(MockInterviewSession.id))
        .where(MockInterviewSession.student_id == user.id)
        .where(MockInterviewSession.overall_score.isnot(None))
    ) or 0
    if int(completed_interviews) >= 1:
        earn("first_interview")

    best_interview = db.scalar(
        select(sqlfunc.max(MockInterviewSession.overall_score))
        .where(MockInterviewSession.student_id == user.id)
    )
    if best_interview is not None and float(best_interview) >= 75:
        earn("interview_pro")

    # CampusIQ score threshold
    score = campus_iq_score.get_or_create(db, user)
    if score.total >= 75:
        earn("placement_ready")

    # Level threshold
    profile = user.student_profile
    if profile and profile.current_level >= 10:
        earn("level_10")

    if awarded:
        db.commit()
    return awarded


# ════════════════════════════════════════════════════════════════
# Profile read + update
# ════════════════════════════════════════════════════════════════

@dataclass
class PublicProfileResponse:
    user_id: uuid.UUID
    name: str
    role: str
    branch: str | None
    semester: int | None
    cgpa: float | None
    github_url: str | None
    linkedin_url: str | None
    skills: list[str]
    target_companies: list[str]
    target_role: str | None
    xp_total: int
    current_level: int
    streak_days: int
    campus_iq_score: float
    rank: int | None
    tier: str
    academic_pillar: float
    skill_pillar: float
    interview_pillar: float
    placement_pillar: float
    badges: list[dict]
    member_since: datetime


def get_profile(db: Session, user: User) -> PublicProfileResponse:
    """Full profile view for the current user."""
    # Ensure the score + badges are fresh
    campus_iq_score.recompute_score(db, user)
    check_and_award_badges(db, user)
    db.commit()
    db.refresh(user)

    score = campus_iq_score.get_or_create(db, user)
    my_row = leaderboard.get_my_rank(db, user)
    profile = user.student_profile

    badges = db.scalars(
        select(Badge).where(Badge.student_id == user.id).order_by(Badge.earned_at.desc())
    ).all()

    return PublicProfileResponse(
        user_id=user.id,
        name=user.full_name,
        role=user.role.value,
        branch=profile.branch if profile else None,
        semester=profile.semester if profile else None,
        cgpa=float(profile.cgpa) if profile and profile.cgpa is not None else None,
        github_url=profile.github_url if profile else None,
        linkedin_url=profile.linkedin_url if profile else None,
        skills=list(profile.skills or []) if profile else [],
        target_companies=list(profile.target_companies or []) if profile else [],
        target_role=profile.target_role if profile else None,
        xp_total=int(profile.xp_total if profile else 0),
        current_level=int(profile.current_level if profile else 1),
        streak_days=int(profile.streak_days if profile else 0),
        campus_iq_score=score.total,
        rank=my_row.rank if my_row else None,
        tier=my_row.tier if my_row else "bronze",
        academic_pillar=score.academic,
        skill_pillar=score.skill,
        interview_pillar=score.interview,
        placement_pillar=score.placement,
        badges=[
            {
                "id": str(b.id),
                "badge_type": b.badge_type,
                "name": b.badge_name,
                "description": b.description,
                "icon": b.icon,
                "earned_at": b.earned_at.isoformat(),
            }
            for b in badges
        ],
        member_since=user.created_at,
    )


def update_profile(
    db: Session,
    user: User,
    *,
    branch: str | None = None,
    semester: int | None = None,
    cgpa: float | None = None,
    github_url: str | None = None,
    linkedin_url: str | None = None,
    skills: list[str] | None = None,
    target_companies: list[str] | None = None,
    target_role: str | None = None,
) -> PublicProfileResponse:
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students have editable profiles.",
        )

    profile = user.student_profile
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.flush()
        user.student_profile = profile

    if branch is not None:
        profile.branch = branch
    if semester is not None:
        profile.semester = semester
    if cgpa is not None:
        from decimal import Decimal

        profile.cgpa = Decimal(f"{cgpa:.2f}")
    if github_url is not None:
        profile.github_url = github_url
    if linkedin_url is not None:
        profile.linkedin_url = linkedin_url
    if skills is not None:
        profile.skills = list(skills)
    if target_companies is not None:
        profile.target_companies = list(target_companies)
    if target_role is not None:
        profile.target_role = target_role

    # Profile changes can shift the skill pillar via declared skills
    campus_iq_score.recompute_score(db, user)
    db.commit()
    db.refresh(profile)
    db.refresh(user)

    return get_profile(db, user)
