"""CampusIQ Score (F16) — Phase 18 full 4-pillar composition.

Composes four domain pillars into a single 0-100 score:

    total = 0.30 × academic + 0.25 × skill + 0.25 × interview + 0.20 × placement

Each pillar is a pure function of the student's persisted data:
- **Academic** — weighted average of the last 10 quiz scores (easy 0.7, med 1.0,
  hard 1.3). Grows with recent performance.
- **Skill** — average mastery across all skill-graph nodes the student has
  declared or proven via quizzes, weighted by node difficulty tier. Rewards
  breadth + depth.
- **Interview** — best overall score from completed mock interview sessions,
  bumped by the number of sessions completed (diminishing returns after 3).
- **Placement** — combines the latest ATS score, the number of tracked job
  applications, and the count of distinct companies applied to.

DMS Unit III — function composition: the total is literally a weighted
composition of the four per-pillar functions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func as sqlfunc, select
from sqlalchemy.orm import Session

from app.models.algorithm import SkillNode
from app.models.gamification import CampusIQScore
from app.models.placement import (
    InterviewStatus,
    JobApplication,
    MockInterviewSession,
    Resume,
)
from app.models.quiz import Difficulty, Quiz, QuizAttempt
from app.models.user import User

logger = logging.getLogger(__name__)


# ── Config ──

RECENT_ATTEMPTS_WINDOW = 10

DIFFICULTY_WEIGHT: dict[Difficulty, float] = {
    Difficulty.EASY: 0.7,
    Difficulty.MEDIUM: 1.0,
    Difficulty.HARD: 1.3,
}

# Weights must sum to 1.0
PILLAR_WEIGHTS: dict[str, float] = {
    "academic": 0.30,
    "skill": 0.25,
    "interview": 0.25,
    "placement": 0.20,
}


@dataclass
class ScoreBreakdown:
    total: float
    academic: float
    skill: float
    interview: float
    placement: float
    last_calculated_at: datetime


# ════════════════════════════════════════════════════════════════
# Pillar functions
# ════════════════════════════════════════════════════════════════

def compute_academic_pillar(db: Session, user: User) -> float:
    """Weighted average of recent quiz scores (0-100)."""
    rows = db.execute(
        select(QuizAttempt, Quiz)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .where(QuizAttempt.student_id == user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(RECENT_ATTEMPTS_WINDOW)
    ).all()

    if not rows:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0
    for attempt, quiz in rows:
        weight = DIFFICULTY_WEIGHT.get(quiz.difficulty, 1.0)
        weighted_sum += float(attempt.score) * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0
    return round(min(100.0, weighted_sum / total_weight), 2)


def compute_skill_pillar(db: Session, user: User) -> float:
    """Average skill-graph mastery × difficulty-tier weight, scaled 0-100.

    Uses the Phase 15 mastery computation so declared skills + quiz-derived
    mastery both count. A student with deep mastery of hard skills scores
    higher than one who dabbles in easy ones.
    """
    try:
        # Lazy import to avoid circular dependency at module load time
        from app.services import skill_graph
    except ImportError:
        return 0.0

    try:
        _graph, nodes = skill_graph._load_base_graph(db)
    except Exception as e:
        logger.warning("skill pillar: graph load failed: %s", e)
        return 0.0

    if not nodes:
        return 0.0

    node_names = [n.name for n in nodes]
    try:
        snap = skill_graph.compute_mastery(db, user, graph_nodes=node_names)
    except Exception as e:
        logger.warning("skill pillar: mastery compute failed: %s", e)
        return 0.0

    # Weight each node's mastery by its difficulty tier (1-5 → 0.6, 0.8, 1.0, 1.2, 1.4)
    tier_weight: dict[int, float] = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.2, 5: 1.4}
    weighted_sum = 0.0
    total_weight = 0.0
    for n in nodes:
        mastery = float(snap.per_skill.get(n.name, 0.0))
        w = tier_weight.get(n.difficulty_tier, 1.0)
        weighted_sum += mastery * w
        total_weight += w

    if total_weight == 0:
        return 0.0
    # mastery is in [0, 1] so the weighted average is in [0, 1]. Scale to 0-100.
    avg = weighted_sum / total_weight
    return round(min(100.0, avg * 100.0), 2)


def compute_interview_pillar(db: Session, user: User) -> float:
    """Best overall mock-interview score with a diminishing-returns bonus for
    the number of completed sessions.
    """
    best_row = db.scalar(
        select(sqlfunc.max(MockInterviewSession.overall_score)).where(
            MockInterviewSession.student_id == user.id,
            MockInterviewSession.status == InterviewStatus.COMPLETED,
        )
    )
    if best_row is None:
        return 0.0

    best = float(best_row)

    # Count completed sessions — up to 3 gives a +0 to +5 boost
    count = db.scalar(
        select(sqlfunc.count(MockInterviewSession.id)).where(
            MockInterviewSession.student_id == user.id,
            MockInterviewSession.status == InterviewStatus.COMPLETED,
        )
    ) or 0
    count = int(count)
    session_bonus = min(5.0, count * 1.5)

    return round(min(100.0, best + session_bonus), 2)


def compute_placement_pillar(db: Session, user: User) -> float:
    """Blend of the latest ATS score, number of applications, and company
    diversity. Rewards students who have a polished resume AND are actively
    applying to a range of companies.
    """
    score = 0.0

    # ── ATS component (max 50 pts) ──
    resume = db.scalar(select(Resume).where(Resume.student_id == user.id))
    if resume and resume.ats_score is not None:
        score += float(resume.ats_score) * 0.5  # ats 0-100 → 0-50

    # ── Application-count component (max 25 pts) ──
    app_count = db.scalar(
        select(sqlfunc.count(JobApplication.id)).where(
            JobApplication.student_id == user.id
        )
    ) or 0
    score += min(25.0, int(app_count) * 5.0)  # 5 apps maxes this component

    # ── Company-diversity component (max 25 pts) ──
    distinct_companies = db.scalar(
        select(
            sqlfunc.count(sqlfunc.distinct(JobApplication.job_listing_id))
        ).where(JobApplication.student_id == user.id)
    ) or 0
    score += min(25.0, int(distinct_companies) * 5.0)

    return round(min(100.0, score), 2)


# ════════════════════════════════════════════════════════════════
# Composition + persistence
# ════════════════════════════════════════════════════════════════

def recompute_score(db: Session, user: User) -> ScoreBreakdown:
    """Recalculate all four pillars, compose them, and persist."""
    academic = compute_academic_pillar(db, user)
    skill = compute_skill_pillar(db, user)
    interview = compute_interview_pillar(db, user)
    placement = compute_placement_pillar(db, user)

    total = round(
        PILLAR_WEIGHTS["academic"] * academic
        + PILLAR_WEIGHTS["skill"] * skill
        + PILLAR_WEIGHTS["interview"] * interview
        + PILLAR_WEIGHTS["placement"] * placement,
        2,
    )

    record = db.scalar(select(CampusIQScore).where(CampusIQScore.student_id == user.id))
    if record is None:
        record = CampusIQScore(student_id=user.id)
        db.add(record)

    record.total_score = Decimal(f"{total:.2f}")
    record.academic_pillar = Decimal(f"{academic:.2f}")
    record.skill_pillar = Decimal(f"{skill:.2f}")
    record.interview_pillar = Decimal(f"{interview:.2f}")
    record.placement_pillar = Decimal(f"{placement:.2f}")
    db.flush()

    return ScoreBreakdown(
        total=total,
        academic=academic,
        skill=skill,
        interview=interview,
        placement=placement,
        last_calculated_at=record.calculated_at or datetime.utcnow(),
    )


def get_or_create(db: Session, user: User) -> ScoreBreakdown:
    """Return the cached score, recomputing if the row is missing.

    Unlike Phase 12, we now always return all 4 pillars — other services can
    rely on the cached row having fresh values as long as they trigger
    `recompute_score()` at the right moments (quiz submit, interview complete,
    application change, etc.).
    """
    record = db.scalar(select(CampusIQScore).where(CampusIQScore.student_id == user.id))
    if record is None:
        return recompute_score(db, user)
    return ScoreBreakdown(
        total=float(record.total_score),
        academic=float(record.academic_pillar),
        skill=float(record.skill_pillar),
        interview=float(record.interview_pillar),
        placement=float(record.placement_pillar),
        last_calculated_at=record.calculated_at,
    )
