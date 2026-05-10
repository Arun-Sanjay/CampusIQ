"""Public recruiter-facing profile endpoint (F15 — Phase 21).

Exposes a read-only view at GET /profile/public/{student_id}. No auth
dependency: anyone with the share link can open it. Only the
PublicProfileResponse fields are returned (no email, no phone, no
application history).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.gamification import PublicProfileResponse
from app.services import profile as profile_service

router = APIRouter()


@router.get("/{student_id}", response_model=PublicProfileResponse)
def get_public_profile(student_id: uuid.UUID, db: DbSession) -> PublicProfileResponse:
    """Read-only public profile view — used by the /p/:studentId share page."""
    snap = profile_service.get_public_profile_by_id(db, student_id)
    return PublicProfileResponse(
        user_id=snap.user_id,
        name=snap.name,
        role=snap.role,
        branch=snap.branch,
        semester=snap.semester,
        cgpa=snap.cgpa,
        github_url=snap.github_url,
        linkedin_url=snap.linkedin_url,
        skills=snap.skills,
        target_companies=snap.target_companies,
        target_role=snap.target_role,
        xp_total=snap.xp_total,
        current_level=snap.current_level,
        streak_days=snap.streak_days,
        campus_iq_score=snap.campus_iq_score,
        rank=snap.rank,
        tier=snap.tier,  # type: ignore[arg-type]
        academic_pillar=snap.academic_pillar,
        skill_pillar=snap.skill_pillar,
        interview_pillar=snap.interview_pillar,
        placement_pillar=snap.placement_pillar,
        badges=[b for b in snap.badges],  # type: ignore[arg-type]
        member_since=snap.member_since,
    )
