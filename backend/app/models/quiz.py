"""Quiz engine models (F3)."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._enum_helper import enum_values


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"


class QuizMode(str, enum.Enum):
    PRACTICE = "practice"  # formative, unlimited attempts, no proctoring
    TEST = "test"  # proctored, single attempt, feeds CIE


class CIEComponent(str, enum.Enum):
    """Which CIE component a test-mode quiz feeds (Handbook §4.2)."""

    QUIZ_1 = "quiz_1"
    QUIZ_2 = "quiz_2"
    TEST_1 = "test_1"
    TEST_2 = "test_2"


# Reused on Quiz + QuizAttempt → declare the Postgres type once.
_quiz_mode = Enum(QuizMode, name="quiz_mode", values_callable=enum_values)


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="quiz_difficulty", values_callable=enum_values),
        default=Difficulty.MEDIUM,
        nullable=False,
    )
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # ── Practice vs proctored-test mode (Phase 4) ──
    mode: Mapped[QuizMode] = mapped_column(_quiz_mode, default=QuizMode.PRACTICE, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = unlimited
    requires_proctoring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cie_component: Mapped[CIEComponent | None] = mapped_column(
        Enum(CIEComponent, name="cie_component", values_callable=enum_values)
    )
    total_marks: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order_index"
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", values_callable=enum_values),
        default=QuestionType.MCQ,
        nullable=False,
    )
    options: Mapped[list | None] = mapped_column(JSON)  # for MCQ: ["A", "B", "C", "D"]
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="question_difficulty", values_callable=enum_values),
        default=Difficulty.MEDIUM,
        nullable=False,
    )
    topic: Mapped[str | None] = mapped_column(String(255))  # for weak area detection
    # ── Marks-based grading + CO/Bloom tagging (Phase 4; default keeps practice
    #    quizzes at 1 mark/question so existing scoring is unchanged) ──
    marks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    co: Mapped[str | None] = mapped_column(String(8))  # "CO3"
    bloom: Mapped[str | None] = mapped_column(String(4))  # "L2"

    quiz: Mapped["Quiz"] = relationship(back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (Index("ix_quiz_attempts_quiz_student", "quiz_id", "student_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer)
    # answers: list of {question_id, student_answer, is_correct}
    answers: Mapped[list | None] = mapped_column(JSON)
    # Weak topic detection bit vector for Hamming distance checker (F23)
    answer_bit_vector: Mapped[str | None] = mapped_column(String(500))
    # ── Marks + proctoring (Phase 4). `score` (%) is kept for adaptive/XP logic. ──
    mode: Mapped[QuizMode] = mapped_column(_quiz_mode, default=QuizMode.PRACTICE, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    marks_obtained: Mapped[float | None] = mapped_column(Numeric(6, 2))
    marks_possible: Mapped[float | None] = mapped_column(Numeric(6, 2))
    is_proctored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tab_switch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fullscreen_exits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    copy_paste_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    face_absent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    face_multiple_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    violations: Mapped[list | None] = mapped_column(JSON)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quiz: Mapped["Quiz"] = relationship(back_populates="attempts")
