"""Set operations + inclusion-exclusion counting (Phase 19, F25).

DMS Unit I — inclusion-exclusion principle. Powers the admin Skill Analytics
view: filter students by combinations like "(Python AND React) NOT Docker"
and report how many students fall in each region of the resulting Venn
diagram.

The full inclusion-exclusion formula for the union of sets A₁, A₂, …, Aₙ:

    |A₁ ∪ A₂ ∪ … ∪ Aₙ| = Σ|Aᵢ| − Σ|Aᵢ ∩ Aⱼ| + Σ|Aᵢ ∩ Aⱼ ∩ Aₖ| − …

For n = 2 we get the textbook |A ∪ B| = |A| + |B| − |A ∩ B|.
For n = 3: |A ∪ B ∪ C| = |A| + |B| + |C| − |A ∩ B| − |A ∩ C| − |B ∩ C| + |A ∩ B ∩ C|.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import StudentProfile, User, UserRole

logger = logging.getLogger(__name__)


@dataclass
class SkillSetResult:
    skill: str
    student_ids: set[str]


@dataclass
class InclusionExclusionResult:
    skills: list[str]
    per_skill: list[dict]                  # [{skill, count, sample_names}]
    intersections: list[dict]              # [{skills: [...], count}]
    union_count_naive: int                 # Σ|Aᵢ| (over-counted)
    union_count_actual: int                # |A₁ ∪ A₂ ∪ …| via the formula
    overlap_correction: int                # difference of the two
    total_students: int
    matching_student_names: list[str]      # students in the union (sample of 20)


def _normalize(s: str) -> str:
    return s.strip().lower()


def _load_student_skills(db: Session) -> dict[str, dict]:
    """Return {student_id: {name, skills_set}} for every student."""
    rows = db.execute(
        select(User, StudentProfile)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.role == UserRole.STUDENT)
    ).all()

    out: dict[str, dict] = {}
    for user, profile in rows:
        skills = set()
        if profile and profile.skills:
            skills = {_normalize(s) for s in profile.skills if s}
        out[str(user.id)] = {"name": user.full_name, "skills": skills}
    return out


def analyze_skills(
    db: Session,
    *,
    skills: list[str],
) -> InclusionExclusionResult:
    """Run the inclusion-exclusion analysis over up to 4 skills.

    Returns per-skill counts, every k-way intersection (k ≥ 2), the naive
    union (which over-counts), the actual union via the formula, and a
    sample of student names that match the union.
    """
    cleaned = [s.strip() for s in skills if s.strip()][:4]
    if not cleaned:
        return InclusionExclusionResult(
            skills=[],
            per_skill=[],
            intersections=[],
            union_count_naive=0,
            union_count_actual=0,
            overlap_correction=0,
            total_students=0,
            matching_student_names=[],
        )

    student_data = _load_student_skills(db)
    total_students = len(student_data)

    # Build the per-skill sets — students whose declared skills contain skill_name
    skill_sets: list[SkillSetResult] = []
    for skill in cleaned:
        target = _normalize(skill)
        matching = {
            sid
            for sid, data in student_data.items()
            if any(target == s or target in s or s in target for s in data["skills"])
        }
        skill_sets.append(SkillSetResult(skill=skill, student_ids=matching))

    per_skill_resp: list[dict] = []
    naive_sum = 0
    for s in skill_sets:
        naive_sum += len(s.student_ids)
        sample_names = [
            student_data[sid]["name"] for sid in list(s.student_ids)[:5]
        ]
        per_skill_resp.append(
            {
                "skill": s.skill,
                "count": len(s.student_ids),
                "sample_names": sample_names,
            }
        )

    # Compute every k-way intersection (k = 2, 3, 4) and apply ±1 sign
    intersections_resp: list[dict] = []
    union_actual = 0
    for k in range(1, len(skill_sets) + 1):
        sign = 1 if (k % 2 == 1) else -1
        for combo in combinations(range(len(skill_sets)), k):
            intersect_set = set.intersection(
                *(skill_sets[i].student_ids for i in combo)
            )
            count = len(intersect_set)
            if k >= 2:
                intersections_resp.append(
                    {
                        "skills": [skill_sets[i].skill for i in combo],
                        "count": count,
                    }
                )
            union_actual += sign * count

    union_actual = max(0, union_actual)
    overlap_correction = naive_sum - union_actual

    # Sample of matching student names from the union
    union_set: set[str] = set()
    for s in skill_sets:
        union_set |= s.student_ids
    matching_names = sorted(
        student_data[sid]["name"] for sid in list(union_set)[:20]
    )

    return InclusionExclusionResult(
        skills=cleaned,
        per_skill=per_skill_resp,
        intersections=intersections_resp,
        union_count_naive=naive_sum,
        union_count_actual=union_actual,
        overlap_correction=overlap_correction,
        total_students=total_students,
        matching_student_names=matching_names,
    )
