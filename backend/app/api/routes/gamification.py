"""Gamification + profile endpoints (Phase 18)."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from sqlalchemy import func as sqlfunc, select

from app.api.deps import CurrentUser, DbSession
from app.models.gamification import CampusIQScore
from app.models.user import User, UserRole
from app.schemas.gamification import (
    DomainProgressResponse,
    LeaderboardResponse,
    LeaderboardRowResponse,
    ProfileUpdateRequest,
    PublicProfileResponse,
    SkillNodeStateResponse,
    SkillTreeResponse,
)
from app.services import campus_iq_score, leaderboard as lb_service
from app.services import profile as profile_service
from app.services import skill_tree

router = APIRouter()


def _row_to_response(row: lb_service.LeaderboardRow) -> LeaderboardRowResponse:
    return LeaderboardRowResponse(**asdict(row))


# ════════════════════════════════════════════════════════════════
# Leaderboard
# ════════════════════════════════════════════════════════════════

@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Top-K leaderboard by CampusIQ score",
)
def get_leaderboard(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 50,
) -> LeaderboardResponse:
    rows = lb_service.get_leaderboard(db, current_user, limit=limit)
    my_row = lb_service.get_my_rank(db, current_user)

    total_students = db.scalar(
        select(sqlfunc.count(User.id)).where(User.role == UserRole.STUDENT)
    ) or 0

    return LeaderboardResponse(
        rows=[_row_to_response(r) for r in rows],
        my_row=_row_to_response(my_row) if my_row else None,
        total_students=int(total_students),
    )


# ════════════════════════════════════════════════════════════════
# Skill Tree
# ════════════════════════════════════════════════════════════════

@router.get(
    "/skill-tree/me",
    response_model=SkillTreeResponse,
    summary="Student's skill tree with per-node unlock state",
)
def get_my_skill_tree(
    db: DbSession, current_user: CurrentUser
) -> SkillTreeResponse:
    tree = skill_tree.build_skill_tree(db, current_user)
    return SkillTreeResponse(
        domains=[
            DomainProgressResponse(
                name=d.name,
                total_skills=d.total_skills,
                mastered_count=d.mastered_count,
                unlocked_count=d.unlocked_count,
                progress_percent=d.progress_percent,
                skills=[SkillNodeStateResponse(**asdict(s)) for s in d.skills],
            )
            for d in tree.domains
        ],
        mastered_count=tree.mastered_count,
        total_count=tree.total_count,
        overall_percent=tree.overall_percent,
    )


# ════════════════════════════════════════════════════════════════
# Score (full 4-pillar recompute on demand)
# ════════════════════════════════════════════════════════════════

@router.post(
    "/score/me/recompute",
    summary="Force-recompute the CampusIQ score from all 4 pillars",
)
def recompute_my_score(db: DbSession, current_user: CurrentUser) -> dict:
    score = campus_iq_score.recompute_score(db, current_user)
    db.commit()
    return {
        "total": score.total,
        "academic": score.academic,
        "skill": score.skill,
        "interview": score.interview,
        "placement": score.placement,
    }


# ════════════════════════════════════════════════════════════════
# Profile
# ════════════════════════════════════════════════════════════════

@router.get(
    "/profile/me",
    response_model=PublicProfileResponse,
    summary="My full profile (4 pillars, badges, skills, tier, rank)",
)
def get_my_profile(
    db: DbSession, current_user: CurrentUser
) -> PublicProfileResponse:
    data = profile_service.get_profile(db, current_user)
    return PublicProfileResponse(**asdict(data))


@router.patch(
    "/profile/me",
    response_model=PublicProfileResponse,
    summary="Update my student profile (skills, targets, links)",
)
def update_my_profile(
    data: ProfileUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> PublicProfileResponse:
    updated = profile_service.update_profile(
        db,
        current_user,
        branch=data.branch,
        semester=data.semester,
        cgpa=data.cgpa,
        github_url=data.github_url,
        linkedin_url=data.linkedin_url,
        skills=data.skills,
        target_companies=data.target_companies,
        target_role=data.target_role,
    )
    return PublicProfileResponse(**asdict(updated))
