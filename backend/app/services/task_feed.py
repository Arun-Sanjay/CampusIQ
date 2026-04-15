"""Smart Task Feed (F20) — Phase 12.

DAA Unit III concept: max-heap priority queue. Each candidate task gets a
score = urgency × impact, and we pop the top-K to render the dashboard
"What should I do next?" feed.

Sources of candidate tasks (Phase 12):
- Published quizzes the student has never attempted        → IMPACT high, URGENCY medium
- Quizzes the student attempted but scored < 60%           → URGENCY high (retake)
- Weak topics (≥ 2 attempts, < 60% correct on the topic)  → URGENCY medium
- Daily-login bonus available today                        → URGENCY low, IMPACT low

We use Python's heapq (min-heap) by negating the score so the highest-scored
task pops first.
"""
from __future__ import annotations

import heapq
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.gamification import XPEvent, XPEventType
from app.models.quiz import Difficulty, Quiz, QuizAttempt
from app.models.user import StudentProfile, Subject, User

logger = logging.getLogger(__name__)


TaskPriority = Literal["urgent", "high", "medium", "low"]
TaskKind = Literal["quiz", "retake", "weak_area", "daily_login"]


@dataclass
class TaskItem:
    title: str
    reason: str
    priority: TaskPriority
    score: float
    kind: TaskKind
    action_url: str | None = None
    quiz_id: uuid.UUID | None = None
    subject_code: str | None = None


# ── Tunables ──
TOP_K = 6                  # how many tasks the dashboard should render
WEAK_TOPIC_THRESHOLD = 60.0
RETAKE_THRESHOLD = 60.0


def _score_to_priority(score: float) -> TaskPriority:
    if score >= 80:
        return "urgent"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _push(heap: list, task: TaskItem) -> None:
    """Push onto a min-heap by negating score so the largest pops first."""
    heapq.heappush(heap, (-task.score, len(heap), task))


def _pop_top_k(heap: list, k: int) -> list[TaskItem]:
    out: list[TaskItem] = []
    while heap and len(out) < k:
        _neg, _, task = heapq.heappop(heap)
        out.append(task)
    return out


def build_task_feed(db: Session, user: User) -> list[TaskItem]:
    """Compute the top-K tasks for the dashboard."""
    heap: list = []

    # ── 1. Unattempted published quizzes ──────────────────────────────
    attempted_quiz_ids = set(
        db.scalars(
            select(QuizAttempt.quiz_id).where(QuizAttempt.student_id == user.id)
        ).all()
    )

    unattempted_rows = db.execute(
        select(Quiz, Subject)
        .join(Subject, Quiz.subject_id == Subject.id)
        .where(Quiz.is_published.is_(True))
        .where(Quiz.id.notin_(attempted_quiz_ids) if attempted_quiz_ids else Quiz.is_published.is_(True))
        .order_by(Quiz.created_at.desc())
        .limit(20)
    ).all()

    for quiz, subject in unattempted_rows:
        # Newer quizzes get a slight boost; harder quizzes more impactful
        difficulty_bonus = {"easy": 5, "medium": 12, "hard": 20}.get(quiz.difficulty.value, 10)
        urgency = 55 + difficulty_bonus
        impact = 25  # baseline impact for trying something new
        score = urgency + impact
        _push(
            heap,
            TaskItem(
                title=f"Take quiz: {quiz.title}",
                reason=f"New {quiz.difficulty.value} quiz in {subject.code} — earn XP and improve your academic score",
                priority=_score_to_priority(score),
                score=score,
                kind="quiz",
                action_url=f"/student/quizzes/{quiz.id}/take",
                quiz_id=quiz.id,
                subject_code=subject.code,
            ),
        )

    # ── 2. Failed quizzes (retake) ────────────────────────────────────
    # Best score per quiz the student already attempted
    best_scores = dict(
        db.execute(
            select(QuizAttempt.quiz_id, func.max(QuizAttempt.score))
            .where(QuizAttempt.student_id == user.id)
            .group_by(QuizAttempt.quiz_id)
        ).all()
    )

    failed_quiz_ids = [qid for qid, sc in best_scores.items() if float(sc) < RETAKE_THRESHOLD]
    if failed_quiz_ids:
        retake_rows = db.execute(
            select(Quiz, Subject)
            .join(Subject, Quiz.subject_id == Subject.id)
            .where(Quiz.id.in_(failed_quiz_ids))
            .where(Quiz.is_published.is_(True))
        ).all()
        for quiz, subject in retake_rows:
            best = float(best_scores[quiz.id])
            urgency = 70 + (RETAKE_THRESHOLD - best) * 0.5  # the worse you scored, the more urgent
            impact = 15
            score = urgency + impact
            _push(
                heap,
                TaskItem(
                    title=f"Retake: {quiz.title}",
                    reason=f"Your best score was {best:.0f}% — bring it above {int(RETAKE_THRESHOLD)}%",
                    priority=_score_to_priority(score),
                    score=score,
                    kind="retake",
                    action_url=f"/student/quizzes/{quiz.id}/take",
                    quiz_id=quiz.id,
                    subject_code=subject.code,
                ),
            )

    # ── 3. Weak topics ────────────────────────────────────────────────
    # Compute topic-level correctness from quiz_attempt.answers
    topic_bucket: dict[str, dict] = defaultdict(
        lambda: {"correct": 0, "total": 0, "subject": None}
    )
    rows = db.execute(
        select(QuizAttempt, Quiz, Subject)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Subject, Quiz.subject_id == Subject.id)
        .where(QuizAttempt.student_id == user.id)
    ).all()
    for attempt, _quiz, subject in rows:
        if not attempt.answers:
            continue
        for ans in attempt.answers:
            topic = (ans.get("topic") or "").strip()
            if not topic:
                continue
            b = topic_bucket[topic]
            b["total"] += 1
            if ans.get("is_correct"):
                b["correct"] += 1
            b["subject"] = subject.code

    for topic, b in topic_bucket.items():
        if b["total"] < 2:
            continue
        pct = (b["correct"] / b["total"]) * 100
        if pct >= WEAK_TOPIC_THRESHOLD:
            continue
        urgency = 50 + (WEAK_TOPIC_THRESHOLD - pct) * 0.4
        impact = 20
        score = urgency + impact
        _push(
            heap,
            TaskItem(
                title=f"Review weak area: {topic}",
                reason=f"You're at {pct:.0f}% on this topic — try a focused practice quiz",
                priority=_score_to_priority(score),
                score=score,
                kind="weak_area",
                action_url="/student/quizzes",
                subject_code=b["subject"],
            ),
        )

    # ── 4. Daily login bonus ──────────────────────────────────────────
    profile: StudentProfile | None = user.student_profile
    if profile is not None:
        today = datetime.now(timezone.utc).date()
        already_today = db.scalar(
            select(func.count(XPEvent.id))
            .where(XPEvent.student_id == user.id)
            .where(XPEvent.event_type == XPEventType.DAILY_LOGIN)
            .where(func.date(XPEvent.created_at) == today)
        )
        if not already_today:
            score = 30
            _push(
                heap,
                TaskItem(
                    title="Claim your daily login XP",
                    reason="Keep your streak alive — pop in once today for a free 10 XP",
                    priority=_score_to_priority(score),
                    score=score,
                    kind="daily_login",
                    action_url="/student",
                ),
            )

    return _pop_top_k(heap, TOP_K)
