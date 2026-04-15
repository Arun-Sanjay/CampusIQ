"""Leaderboard + tier assignment (Phase 18).

The leaderboard is simply the CampusIQ score sorted descending. Tier
assignment is a classic DMS Unit III partial order — we partition students
into equivalence classes by score band.

Tiers:
    Diamond:  90 ≤ score ≤ 100
    Platinum: 80 ≤ score < 90
    Gold:     60 ≤ score < 80
    Silver:   40 ≤ score < 60
    Bronze:        score < 40
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func as sqlfunc, select
from sqlalchemy.orm import Session

from app.models.gamification import CampusIQScore
from app.models.user import StudentProfile, User, UserRole


TierLiteral = Literal["diamond", "platinum", "gold", "silver", "bronze"]


TIER_THRESHOLDS: list[tuple[TierLiteral, float]] = [
    ("diamond", 90.0),
    ("platinum", 80.0),
    ("gold", 60.0),
    ("silver", 40.0),
    ("bronze", 0.0),
]


def tier_for_score(score: float) -> TierLiteral:
    for tier, threshold in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "bronze"


@dataclass
class LeaderboardRow:
    rank: int
    student_id: str
    name: str
    total_score: float
    academic: float
    skill: float
    interview: float
    placement: float
    tier: TierLiteral
    xp_total: int
    current_level: int
    is_current_user: bool = False


def get_leaderboard(
    db: Session,
    user: User,
    *,
    limit: int = 50,
) -> list[LeaderboardRow]:
    """Top-K students by CampusIQ total score. Highlights the current user."""
    rows = db.execute(
        select(CampusIQScore, User, StudentProfile)
        .join(User, CampusIQScore.student_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.role == UserRole.STUDENT)
        .order_by(CampusIQScore.total_score.desc())
        .limit(limit)
    ).all()

    out: list[LeaderboardRow] = []
    for rank, (score, student, profile) in enumerate(rows, start=1):
        total = float(score.total_score or 0)
        out.append(
            LeaderboardRow(
                rank=rank,
                student_id=str(student.id),
                name=student.full_name,
                total_score=round(total, 2),
                academic=float(score.academic_pillar or 0),
                skill=float(score.skill_pillar or 0),
                interview=float(score.interview_pillar or 0),
                placement=float(score.placement_pillar or 0),
                tier=tier_for_score(total),
                xp_total=int(profile.xp_total if profile else 0),
                current_level=int(profile.current_level if profile else 1),
                is_current_user=(student.id == user.id),
            )
        )
    return out


def get_my_rank(db: Session, user: User) -> LeaderboardRow | None:
    """Return the current user's row even if they're outside the top-K."""
    my_score = db.scalar(
        select(CampusIQScore).where(CampusIQScore.student_id == user.id)
    )
    if my_score is None:
        return None

    # Count students strictly better than me
    better = db.scalar(
        select(sqlfunc.count(CampusIQScore.id))
        .join(User, CampusIQScore.student_id == User.id)
        .where(User.role == UserRole.STUDENT)
        .where(CampusIQScore.total_score > my_score.total_score)
    ) or 0

    profile = user.student_profile
    total = float(my_score.total_score or 0)
    return LeaderboardRow(
        rank=int(better) + 1,
        student_id=str(user.id),
        name=user.full_name,
        total_score=round(total, 2),
        academic=float(my_score.academic_pillar or 0),
        skill=float(my_score.skill_pillar or 0),
        interview=float(my_score.interview_pillar or 0),
        placement=float(my_score.placement_pillar or 0),
        tier=tier_for_score(total),
        xp_total=int(profile.xp_total if profile else 0),
        current_level=int(profile.current_level if profile else 1),
        is_current_user=True,
    )
