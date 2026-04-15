"""Algorithm-driven feature models: skill graph, notifications, schedules, quiz scheduling."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._enum_helper import enum_values


class SkillGraphEdge(Base):
    """Weighted directed edges for the Adaptive Learning Engine (F17 — research core).

    Edge weights = estimated learning hours. Used by Dijkstra's shortest path (DAA IV)
    and Prim's MST (DAA IV). Per-student dynamic edge weights are computed at query time
    by the service layer, using quiz performance to adjust base weights.
    """

    __tablename__ = "skill_graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    from_skill: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    to_skill: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    base_weight_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(100))  # web_dev, ml, dsa, etc.
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SkillNode(Base):
    """Metadata for skill graph nodes (prerequisites, difficulty, description)."""

    __tablename__ = "skill_nodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    difficulty_tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5
    resource_url: Mapped[str | None] = mapped_column(String(500))


class CompanySkillRequirement(Base):
    """Company hiring requirements — what skills each company wants.

    Used by Skill Gap Analyser (F7) and Adaptive Learning Engine (F17).
    """

    __tablename__ = "company_skill_requirements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    required_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preferred_skills: Mapped[list | None] = mapped_column(JSON, default=list)
    difficulty_tier: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1-5
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudyOptimizerResult(Base):
    """Results from the Knapsack study optimizer (F18 — DAA IV DP).

    This table is the DATA COLLECTION for the research paper on adaptive learning paths.
    Every recommendation logs: what we suggested, the budget, predicted vs actual improvement.
    """

    __tablename__ = "study_optimizer_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_company: Mapped[str | None] = mapped_column(String(255))
    target_role: Mapped[str | None] = mapped_column(String(255))
    available_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    # Topics selected by 0/1 Knapsack DP
    included_topics: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Topics excluded with reasoning
    excluded_topics: Mapped[list | None] = mapped_column(JSON, default=list)
    predicted_improvement: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    # Populated after student completes the recommended topics + next quiz
    actual_improvement: Mapped[float | None] = mapped_column(Numeric(5, 2))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationType(str, enum.Enum):
    QUIZ_RESULT = "quiz_result"
    SCORE_UPDATE = "score_update"
    DEADLINE_REMINDER = "deadline_reminder"
    INTERVIEW_FEEDBACK = "interview_feedback"
    BADGE_EARNED = "badge_earned"
    ANNOUNCEMENT = "announcement"
    DOUBT_ANSWERED = "doubt_answered"


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    ACKED = "acked"
    FAILED = "failed"
    PENDING = "pending"


class NotificationDelivery(Base):
    """TCP-style reliable notification delivery (F24 — CN V).

    Implements sequence numbers, client ACKs, exponential backoff retry.
    """

    __tablename__ = "notification_delivery"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=enum_values),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # TCP-style fields
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status", values_callable=enum_values),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class QuizSimilarityFlag(Base):
    """Hamming distance submission similarity checker (F23 — DMS IV)."""

    __tablename__ = "quiz_similarity_flags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_a_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_b_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    hamming_distance: Mapped[int] = mapped_column(Integer, nullable=False)
    similarity_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    review_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, reviewed, dismissed
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WeeklySchedule(Base):
    """Backtracking Study Schedule Generator (F26 — DAA V)."""

    __tablename__ = "weekly_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-6
    time_slot: Mapped[str] = mapped_column(String(20), nullable=False)  # "09:00-10:00"
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE")
    )
    activity_label: Mapped[str | None] = mapped_column(String(100))  # "Lunch", "Break"
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class QuizTimeSlot(Base):
    """Graph coloring for Quiz Scheduling (F21 — DMS V)."""

    __tablename__ = "quiz_time_slots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_color: Mapped[int] = mapped_column(Integer, nullable=False)  # graph coloring output
    time_slot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Adjacency list of subjects sharing students at time of generation
    conflict_graph_data: Mapped[dict | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
