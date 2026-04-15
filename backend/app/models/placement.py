"""Placement models: resumes, interviews, jobs, confidence sessions."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._enum_helper import enum_values
from app.models.content import EMBEDDING_DIM


class Resume(Base):
    """Smart Resume Builder (F6)."""

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    # Structured resume data: {contact, education, experience, projects, skills, ...}
    content: Mapped[dict | None] = mapped_column(JSON)
    template: Mapped[str] = mapped_column(String(50), default="technical", nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(500))
    ats_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    last_job_description: Mapped[str | None] = mapped_column(Text)  # for ATS scoring
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InterviewMode(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"


class InterviewPersona(str, enum.Enum):
    FRIENDLY = "friendly"
    TOUGH = "tough"
    RAPID_FIRE = "rapid_fire"
    UNPREDICTABLE = "unpredictable"


class InterviewStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MockInterviewSession(Base):
    """Mock Interview Engine (F9, F10)."""

    __tablename__ = "mock_interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_target: Mapped[str | None] = mapped_column(String(100))  # Google, TCS, etc.
    role_target: Mapped[str | None] = mapped_column(String(100))  # SWE, PM, etc.
    interviewer_persona: Mapped[InterviewPersona] = mapped_column(
        Enum(InterviewPersona, name="interview_persona", values_callable=enum_values),
        default=InterviewPersona.FRIENDLY,
        nullable=False,
    )
    mode: Mapped[InterviewMode] = mapped_column(
        Enum(InterviewMode, name="interview_mode", values_callable=enum_values),
        default=InterviewMode.TEXT,
        nullable=False,
    )
    # For the 5-round Interview Day Simulator (F10)
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_full_simulator: Mapped[bool] = mapped_column(default=False, nullable=False)
    # State machine snapshot: {questions_asked, scores_per_round, transcript, ...}
    state: Mapped[dict | None] = mapped_column(JSON)
    transcript: Mapped[list | None] = mapped_column(JSON)  # list of {role, text, round, score}
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    feedback_report: Mapped[dict | None] = mapped_column(JSON)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status", values_callable=enum_values),
        default=InterviewStatus.IN_PROGRESS,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConfidenceSession(Base):
    """Confidence Coach (F11)."""

    __tablename__ = "confidence_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(500))
    transcript: Mapped[str | None] = mapped_column(Text)
    eye_contact_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    posture_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    filler_word_count: Mapped[int | None] = mapped_column(Integer)
    speaking_pace_wpm: Mapped[int | None] = mapped_column(Integer)
    clarity_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    overall_confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    detailed_feedback: Mapped[dict | None] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class JobType(str, enum.Enum):
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    CONTRACT = "contract"
    PART_TIME = "part_time"


class ApplicationStatus(str, enum.Enum):
    SAVED = "saved"
    APPLIED = "applied"
    OA_RECEIVED = "oa_received"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    OFFER_RECEIVED = "offer_received"
    REJECTED = "rejected"


class JobListingSource(str, enum.Enum):
    ADMIN_ADDED = "admin_added"
    STUDENT_ADDED = "student_added"


class JobListing(Base):
    """Job and Internship Tracker (F12)."""

    __tablename__ = "job_listings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="SET NULL"), index=True
    )
    added_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_type", values_callable=enum_values),
        default=JobType.FULL_TIME,
        nullable=False,
    )
    application_deadline: Mapped[date | None] = mapped_column(Date)
    source: Mapped[JobListingSource] = mapped_column(
        Enum(JobListingSource, name="job_listing_source", values_callable=enum_values),
        default=JobListingSource.ADMIN_ADDED,
        nullable=False,
    )
    # Embedding for fit score matching (Phase 17 — added via migration; JSON fallback)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class JobApplication(Base):
    """Student's tracked applications."""

    __tablename__ = "job_applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", values_callable=enum_values),
        default=ApplicationStatus.SAVED,
        nullable=False,
    )
    fit_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
