"""Academic grading models — AI auto-grader + CIE/SEE grade engine.

The seam: every grading path (AI auto-grader, test-mode quizzes, manual entry)
writes ``exam_results``; the grade engine only *reads* ``exam_results`` to produce
``subject_grades`` → ``semester_results`` → CGPA. See ``grading_feature_spec.md``
and Handbook §4 for the authoritative rules this models.

Enums are stored as VALUES (not Python member names) via ``enum_values`` +
``values_callable`` — the project-wide convention.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._enum_helper import enum_values


# ── Enums ──────────────────────────────────────────────────────────────────
class ExamKind(str, enum.Enum):
    QUIZ = "quiz"
    TEST = "test"
    EXPERIENTIAL = "experiential"
    LAB = "lab"
    SEE = "see"


class ExamPart(str, enum.Enum):
    THEORY = "theory"
    LAB = "lab"


class Leniency(str, enum.Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class SchemeStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    REVIEW = "review"
    READY = "ready"
    FAILED = "failed"


class AnswerSheetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    OCR = "ocr"
    GRADED = "graded"
    REVIEW = "review"
    FINALIZED = "finalized"
    FAILED = "failed"


class ResultSource(str, enum.Enum):
    AI = "ai"
    MANUAL = "manual"
    QUIZ = "quiz"


class LetterGrade(str, enum.Enum):
    O = "O"
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C = "C"
    P = "P"
    F = "F"
    # Transitional grades (Handbook §4.3) — excluded from SGPA/CGPA.
    I = "I"
    W = "W"
    X = "X"
    MP = "MP"


class GateFailure(str, enum.Enum):
    NONE = "none"
    CIE = "cie"
    SEE = "see"
    AGGREGATE = "aggregate"
    CIE_THEORY = "cie_theory"
    SEE_THEORY = "see_theory"
    CIE_LAB = "cie_lab"
    SEE_LAB = "see_lab"


# Shared Enum type instances (reused across multiple columns/tables so the
# Postgres type is declared once).
_exam_kind = Enum(ExamKind, name="exam_kind", values_callable=enum_values)
_exam_part = Enum(ExamPart, name="exam_part", values_callable=enum_values)
_leniency = Enum(Leniency, name="exam_leniency", values_callable=enum_values)
_scheme_status = Enum(SchemeStatus, name="scheme_status", values_callable=enum_values)
_answer_sheet_status = Enum(AnswerSheetStatus, name="answer_sheet_status", values_callable=enum_values)
_result_source = Enum(ResultSource, name="result_source", values_callable=enum_values)
_letter_grade = Enum(LetterGrade, name="letter_grade", values_callable=enum_values)
_gate_failure = Enum(GateFailure, name="gate_failure", values_callable=enum_values)


# ── Per-subject academic config ──────────────────────────────────────────────
class CourseOutcome(Base):
    """A course outcome (CO1..CO5) defined for a subject."""

    __tablename__ = "course_outcomes"
    __table_args__ = (UniqueConstraint("subject_id", "code", name="uq_course_outcome"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(8), nullable=False)  # "CO1"
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SubjectGradeConfig(Base):
    """Per-subject grade-math knobs: CIE component split + pass-gate thresholds.

    The fixed totals (CIE/SEE max, category, credits) live on ``Subject``; this
    row holds the *editable* breakdown + gates so the grading UI edits one row.
    ``components`` is a list of ``{key,label,part,max,kind}``.
    """

    __tablename__ = "subject_grade_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    components: Mapped[list | None] = mapped_column(JSON, default=list)
    # Pass gates (defaults = Handbook §4.4: CIE 40, SEE 35, aggregate 40).
    cie_min_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=40, nullable=False)
    see_min_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=35, nullable=False)
    aggregate_min_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=40, nullable=False)
    # Lab-specific overrides (null → fall back to the non-lab values).
    cie_lab_min_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    see_lab_min_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    gate_lab_separately: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Optional override of the 10-point band table; null → engine default.
    grade_bands: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── Exams (assessment instances) ─────────────────────────────────────────────
class Exam(Base):
    """One graded assessment (a CIE-2 test, a quiz, the SEE, a lab exam).

    Carries both the scheme (questions + CO/Bloom/marks) and the AI grading
    knobs (leniency, custom rules, review thresholds).
    """

    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[ExamKind] = mapped_column(_exam_kind, default=ExamKind.TEST, nullable=False)
    part: Mapped[ExamPart] = mapped_column(_exam_part, default=ExamPart.THEORY, nullable=False)
    # Which CIE component this exam feeds (e.g. "tests", "quizzes"); null for SEE.
    component_key: Mapped[str | None] = mapped_column(String(50))
    sequence: Mapped[int | None] = mapped_column(Integer)  # Test-1 vs Test-2
    max_marks: Mapped[float] = mapped_column(Numeric(7, 2), default=0, nullable=False)
    # Authoritative per-CO max denominators: {"CO1": 10, "CO2": 25, ...}
    co_mark_grid: Mapped[dict | None] = mapped_column(JSON)

    # Scheme ingestion
    scheme_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    scheme_status: Mapped[SchemeStatus] = mapped_column(
        _scheme_status, default=SchemeStatus.PENDING, nullable=False
    )
    # Bridge to a test-mode quiz (null for AI-graded / manual exams).
    quiz_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quizzes.id", ondelete="SET NULL"), index=True
    )

    # AI grading knobs (per exam → reproducible re-grades)
    leniency: Mapped[Leniency] = mapped_column(_leniency, default=Leniency.MODERATE, nullable=False)
    custom_rules: Mapped[str | None] = mapped_column(Text)
    ignore_spelling: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    award_partial_method: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence_review_threshold: Mapped[float] = mapped_column(Numeric(4, 3), default=0.65, nullable=False)
    ocr_review_threshold: Mapped[float] = mapped_column(Numeric(4, 3), default=0.55, nullable=False)

    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    questions: Mapped[list["ExamQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.order_index"
    )
    answer_sheets: Mapped[list["AnswerSheet"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    results: Mapped[list["ExamResult"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )


class ExamQuestion(Base):
    """A scheme question (or sub-part like "1a") with model answer + CO/Bloom."""

    __tablename__ = "exam_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    part: Mapped[ExamPart] = mapped_column(_exam_part, default=ExamPart.THEORY, nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)  # "1", "1a"
    parent_label: Mapped[str | None] = mapped_column(String(20))  # groups "1a"/"1b" under "1"
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_answer: Mapped[str | None] = mapped_column(Text)
    max_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    co: Mapped[str | None] = mapped_column(String(8))  # "CO3"
    bloom: Mapped[str | None] = mapped_column(String(4))  # "L2"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    exam: Mapped["Exam"] = relationship(back_populates="questions")


# ── Answer sheets + per-question grades (the AI auto-grader) ──────────────────
class AnswerSheet(Base):
    """One student's bundle of answer pages for one exam."""

    __tablename__ = "answer_sheets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Null until the teacher confirms the roster match.
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[AnswerSheetStatus] = mapped_column(
        _answer_sheet_status, default=AnswerSheetStatus.UPLOADED, nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    storage_dir: Mapped[str | None] = mapped_column(String(500))
    page_files: Mapped[list | None] = mapped_column(JSON, default=list)

    # USN/name OCR + roster match
    detected_usn: Mapped[str | None] = mapped_column(String(32))
    detected_name: Mapped[str | None] = mapped_column(String(255))
    match_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    match_source: Mapped[str | None] = mapped_column(String(20))  # usn|name|manual|unmatched
    is_match_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rollups (denormalized for the class-list view)
    total_awarded: Mapped[float | None] = mapped_column(Numeric(7, 2))
    total_max: Mapped[float | None] = mapped_column(Numeric(7, 2))
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    exam: Mapped["Exam"] = relationship(back_populates="answer_sheets")
    question_grades: Mapped[list["QuestionGrade"]] = relationship(
        back_populates="answer_sheet", cascade="all, delete-orphan"
    )


class QuestionGrade(Base):
    """Atomic grade for one question on one student's sheet (review unit)."""

    __tablename__ = "question_grades"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    answer_sheet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extracted_answer: Mapped[str | None] = mapped_column(Text)
    awarded_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    max_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    co: Mapped[str | None] = mapped_column(String(8))
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    rationale: Mapped[str | None] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Teacher override
    is_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    teacher_marks: Mapped[float | None] = mapped_column(Numeric(6, 2))
    teacher_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    answer_sheet: Mapped["AnswerSheet"] = relationship(back_populates="question_grades")

    @property
    def effective_marks(self) -> float:
        """Teacher override if present, else the AI award."""
        return float(self.teacher_marks if self.is_overridden and self.teacher_marks is not None else self.awarded_marks)


# ── The seam: per-student per-exam result (written by all paths) ──────────────
class ExamResult(Base):
    """Per-student per-exam result. Written by the AI grader, test quizzes, and
    manual entry; read by the grade engine. ``per_co`` = {"CO1": {obtained,max,pct}}.
    """

    __tablename__ = "exam_results"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_result"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_obtained: Mapped[float] = mapped_column(Numeric(7, 2), default=0, nullable=False)
    total_max: Mapped[float] = mapped_column(Numeric(7, 2), default=0, nullable=False)
    percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    per_co: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[ResultSource] = mapped_column(_result_source, default=ResultSource.AI, nullable=False)
    answer_sheet_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("answer_sheets.id", ondelete="SET NULL")
    )
    quiz_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="SET NULL")
    )
    is_teacher_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    exam: Mapped["Exam"] = relationship(back_populates="results")


# ── Grade rollup (grade engine output) ───────────────────────────────────────
class SubjectGrade(Base):
    """Per-student per-subject final grade (condensation → letter + grade point)."""

    __tablename__ = "subject_grades"
    __table_args__ = (UniqueConstraint("subject_id", "student_id", name="uq_subject_grade"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Condensation inputs (denormalized for transparency)
    cie_obtained: Mapped[float | None] = mapped_column(Numeric(7, 2))
    cie_max: Mapped[float | None] = mapped_column(Numeric(7, 2))
    see_obtained: Mapped[float | None] = mapped_column(Numeric(7, 2))
    see_max: Mapped[float | None] = mapped_column(Numeric(7, 2))
    cie_theory_obtained: Mapped[float | None] = mapped_column(Numeric(7, 2))
    cie_lab_obtained: Mapped[float | None] = mapped_column(Numeric(7, 2))
    see_theory_obtained: Mapped[float | None] = mapped_column(Numeric(7, 2))
    see_lab_obtained: Mapped[float | None] = mapped_column(Numeric(7, 2))
    # Computed
    cie_50: Mapped[float | None] = mapped_column(Numeric(5, 2))
    see_50: Mapped[float | None] = mapped_column(Numeric(5, 2))
    final_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    final_rounded: Mapped[int | None] = mapped_column(Integer)
    letter_grade: Mapped[LetterGrade | None] = mapped_column(_letter_grade)
    grade_point: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gate_failed: Mapped[GateFailure] = mapped_column(_gate_failure, default=GateFailure.NONE, nullable=False)
    is_transitional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transitional_grade: Mapped[LetterGrade | None] = mapped_column(_letter_grade)
    credits_snapshot: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer, index=True)
    finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SemesterResult(Base):
    """Per-student per-semester SGPA (CGPA is written to student_profiles.cgpa)."""

    __tablename__ = "semester_results"
    __table_args__ = (UniqueConstraint("student_id", "semester", name="uq_semester_result"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    sgpa: Mapped[float] = mapped_column(Numeric(4, 2), default=0, nullable=False)
    total_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_grade_points: Mapped[float] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
