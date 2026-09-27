"""add academic grading: AI auto-grader + CIE/SEE grade engine + quiz modes

Adds:
- Subject grading config columns (category, credits, CIE/SEE maxima + lab split).
- StudentProfile.usn (unique) + section.
- Quiz/Question/QuizAttempt columns for practice/test modes + proctoring + marks/CO.
- 9 grading tables: course_outcomes, subject_grade_configs, exams, exam_questions,
  answer_sheets, question_grades, exam_results, subject_grades, semester_results.

Only CREATE/ADD/INDEX (no column alters), so SQLite needs no table rebuild. New
Postgres enum types are created once up-front with checkfirst; columns reference
them with create_type=False so multi-use types aren't created twice.

Revision ID: 000000000008
Revises: 000000000007
Create Date: 2026-06-13 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000008"
down_revision: Union[str, Sequence[str], None] = "000000000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GRADING_ENUMS: dict[str, list[str]] = {
    "subject_category": ["theory", "theory_practice", "practical", "project", "audit"],
    "quiz_mode": ["practice", "test"],
    "cie_component": ["quiz_1", "quiz_2", "test_1", "test_2"],
    "exam_kind": ["quiz", "test", "experiential", "lab", "see"],
    "exam_part": ["theory", "lab"],
    "exam_leniency": ["strict", "moderate", "lenient"],
    "scheme_status": ["pending", "parsing", "review", "ready", "failed"],
    "answer_sheet_status": ["uploaded", "ocr", "graded", "review", "finalized", "failed"],
    "result_source": ["ai", "manual", "quiz"],
    "letter_grade": ["O", "A+", "A", "B+", "B", "C", "P", "F", "I", "W", "X", "MP"],
    "gate_failure": ["none", "cie", "see", "aggregate", "cie_theory", "see_theory", "cie_lab", "see_lab"],
}


def _enum(name: str) -> sa.Enum:
    """Reference a (pre-created) enum type without re-creating it."""
    return sa.Enum(*GRADING_ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name, values in GRADING_ENUMS.items():
            sa.Enum(*values, name=name).create(bind, checkfirst=True)

    # ── 1. subjects: grading config ──────────────────────────────────────────
    op.add_column("subjects", sa.Column("category", _enum("subject_category"), nullable=False, server_default="theory"))
    op.add_column("subjects", sa.Column("credits", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("subjects", sa.Column("cie_max", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("subjects", sa.Column("see_max", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("subjects", sa.Column("has_lab_split", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("subjects", sa.Column("cie_theory_max", sa.Integer(), nullable=True))
    op.add_column("subjects", sa.Column("cie_lab_max", sa.Integer(), nullable=True))
    op.add_column("subjects", sa.Column("see_theory_max", sa.Integer(), nullable=True))
    op.add_column("subjects", sa.Column("see_lab_max", sa.Integer(), nullable=True))

    # ── 2. student_profiles: usn + section ───────────────────────────────────
    op.add_column("student_profiles", sa.Column("usn", sa.String(length=32), nullable=True))
    op.add_column("student_profiles", sa.Column("section", sa.String(length=10), nullable=True))
    op.create_index("ix_student_profiles_usn", "student_profiles", ["usn"], unique=True)

    # ── 3. quizzes: mode + proctoring + CIE component ────────────────────────
    op.add_column("quizzes", sa.Column("mode", _enum("quiz_mode"), nullable=False, server_default="practice"))
    op.add_column("quizzes", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quizzes", sa.Column("requires_proctoring", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("quizzes", sa.Column("available_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quizzes", sa.Column("available_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quizzes", sa.Column("cie_component", _enum("cie_component"), nullable=True))
    op.add_column("quizzes", sa.Column("total_marks", sa.Integer(), nullable=True))

    # ── 4. questions: marks + CO/Bloom ───────────────────────────────────────
    op.add_column("questions", sa.Column("marks", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("questions", sa.Column("co", sa.String(length=8), nullable=True))
    op.add_column("questions", sa.Column("bloom", sa.String(length=4), nullable=True))

    # ── 5. quiz_attempts: marks + proctoring metadata ────────────────────────
    op.add_column("quiz_attempts", sa.Column("mode", _enum("quiz_mode"), nullable=False, server_default="practice"))
    op.add_column("quiz_attempts", sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("quiz_attempts", sa.Column("marks_obtained", sa.Numeric(6, 2), nullable=True))
    op.add_column("quiz_attempts", sa.Column("marks_possible", sa.Numeric(6, 2), nullable=True))
    op.add_column("quiz_attempts", sa.Column("is_proctored", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("quiz_attempts", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quiz_attempts", sa.Column("tab_switch_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quiz_attempts", sa.Column("fullscreen_exits", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quiz_attempts", sa.Column("copy_paste_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quiz_attempts", sa.Column("face_absent_seconds", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quiz_attempts", sa.Column("face_multiple_seconds", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quiz_attempts", sa.Column("auto_submitted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("quiz_attempts", sa.Column("violations", sa.JSON(), nullable=True))
    op.create_index("ix_quiz_attempts_quiz_student", "quiz_attempts", ["quiz_id", "student_id"])

    # ── 6. course_outcomes ───────────────────────────────────────────────────
    op.create_table(
        "course_outcomes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("subject_id", "code", name="uq_course_outcome"),
    )
    op.create_index("ix_course_outcomes_subject_id", "course_outcomes", ["subject_id"])

    # ── 7. subject_grade_configs ─────────────────────────────────────────────
    op.create_table(
        "subject_grade_configs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("components", sa.JSON(), nullable=True),
        sa.Column("cie_min_pct", sa.Numeric(5, 2), nullable=False, server_default="40"),
        sa.Column("see_min_pct", sa.Numeric(5, 2), nullable=False, server_default="35"),
        sa.Column("aggregate_min_pct", sa.Numeric(5, 2), nullable=False, server_default="40"),
        sa.Column("cie_lab_min_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("see_lab_min_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("gate_lab_separately", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("grade_bands", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── 8. exams ─────────────────────────────────────────────────────────────
    op.create_table(
        "exams",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("kind", _enum("exam_kind"), nullable=False, server_default="test"),
        sa.Column("part", _enum("exam_part"), nullable=False, server_default="theory"),
        sa.Column("component_key", sa.String(length=50), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("max_marks", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("co_mark_grid", sa.JSON(), nullable=True),
        sa.Column("scheme_document_id", sa.UUID(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheme_status", _enum("scheme_status"), nullable=False, server_default="pending"),
        sa.Column("quiz_id", sa.UUID(), sa.ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("leniency", _enum("exam_leniency"), nullable=False, server_default="moderate"),
        sa.Column("custom_rules", sa.Text(), nullable=True),
        sa.Column("ignore_spelling", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("award_partial_method", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("confidence_review_threshold", sa.Numeric(4, 3), nullable=False, server_default="0.65"),
        sa.Column("ocr_review_threshold", sa.Numeric(4, 3), nullable=False, server_default="0.55"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exams_subject_id", "exams", ["subject_id"])
    op.create_index("ix_exams_created_by_id", "exams", ["created_by_id"])
    op.create_index("ix_exams_scheme_document_id", "exams", ["scheme_document_id"])
    op.create_index("ix_exams_quiz_id", "exams", ["quiz_id"])

    # ── 9. exam_questions ────────────────────────────────────────────────────
    op.create_table(
        "exam_questions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("exam_id", sa.UUID(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("part", _enum("exam_part"), nullable=False, server_default="theory"),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("parent_label", sa.String(length=20), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("model_answer", sa.Text(), nullable=True),
        sa.Column("max_marks", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("co", sa.String(length=8), nullable=True),
        sa.Column("bloom", sa.String(length=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exam_questions_exam_id", "exam_questions", ["exam_id"])

    # ── 10. answer_sheets ────────────────────────────────────────────────────
    op.create_table(
        "answer_sheets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("exam_id", sa.UUID(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", _enum("answer_sheet_status"), nullable=False, server_default="uploaded"),
        sa.Column("batch_id", sa.UUID(), nullable=True),
        sa.Column("storage_dir", sa.String(length=500), nullable=True),
        sa.Column("page_files", sa.JSON(), nullable=True),
        sa.Column("detected_usn", sa.String(length=32), nullable=True),
        sa.Column("detected_name", sa.String(length=255), nullable=True),
        sa.Column("match_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("match_source", sa.String(length=20), nullable=True),
        sa.Column("is_match_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("total_awarded", sa.Numeric(7, 2), nullable=True),
        sa.Column("total_max", sa.Numeric(7, 2), nullable=True),
        sa.Column("needs_review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_answer_sheets_exam_id", "answer_sheets", ["exam_id"])
    op.create_index("ix_answer_sheets_student_id", "answer_sheets", ["student_id"])
    op.create_index("ix_answer_sheets_batch_id", "answer_sheets", ["batch_id"])

    # ── 11. question_grades ──────────────────────────────────────────────────
    op.create_table(
        "question_grades",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("answer_sheet_id", sa.UUID(), sa.ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_question_id", sa.UUID(), sa.ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extracted_answer", sa.Text(), nullable=True),
        sa.Column("awarded_marks", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("max_marks", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("co", sa.String(length=8), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("ocr_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("teacher_marks", sa.Numeric(6, 2), nullable=True),
        sa.Column("teacher_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_question_grades_answer_sheet_id", "question_grades", ["answer_sheet_id"])
    op.create_index("ix_question_grades_exam_question_id", "question_grades", ["exam_question_id"])

    # ── 12. exam_results (the seam) ──────────────────────────────────────────
    op.create_table(
        "exam_results",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("exam_id", sa.UUID(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_obtained", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("total_max", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("per_co", sa.JSON(), nullable=True),
        sa.Column("source", _enum("result_source"), nullable=False, server_default="ai"),
        sa.Column("answer_sheet_id", sa.UUID(), sa.ForeignKey("answer_sheets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quiz_attempt_id", sa.UUID(), sa.ForeignKey("quiz_attempts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_teacher_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("exam_id", "student_id", name="uq_exam_result"),
    )
    op.create_index("ix_exam_results_exam_id", "exam_results", ["exam_id"])
    op.create_index("ix_exam_results_student_id", "exam_results", ["student_id"])

    # ── 13. subject_grades ───────────────────────────────────────────────────
    op.create_table(
        "subject_grades",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("subject_id", sa.UUID(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cie_obtained", sa.Numeric(7, 2), nullable=True),
        sa.Column("cie_max", sa.Numeric(7, 2), nullable=True),
        sa.Column("see_obtained", sa.Numeric(7, 2), nullable=True),
        sa.Column("see_max", sa.Numeric(7, 2), nullable=True),
        sa.Column("cie_theory_obtained", sa.Numeric(7, 2), nullable=True),
        sa.Column("cie_lab_obtained", sa.Numeric(7, 2), nullable=True),
        sa.Column("see_theory_obtained", sa.Numeric(7, 2), nullable=True),
        sa.Column("see_lab_obtained", sa.Numeric(7, 2), nullable=True),
        sa.Column("cie_50", sa.Numeric(5, 2), nullable=True),
        sa.Column("see_50", sa.Numeric(5, 2), nullable=True),
        sa.Column("final_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("final_rounded", sa.Integer(), nullable=True),
        sa.Column("letter_grade", _enum("letter_grade"), nullable=True),
        sa.Column("grade_point", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gate_failed", _enum("gate_failure"), nullable=False, server_default="none"),
        sa.Column("is_transitional", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transitional_grade", _enum("letter_grade"), nullable=True),
        sa.Column("credits_snapshot", sa.Integer(), nullable=True),
        sa.Column("semester", sa.Integer(), nullable=True),
        sa.Column("finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("subject_id", "student_id", name="uq_subject_grade"),
    )
    op.create_index("ix_subject_grades_subject_id", "subject_grades", ["subject_id"])
    op.create_index("ix_subject_grades_student_id", "subject_grades", ["student_id"])
    op.create_index("ix_subject_grades_semester", "subject_grades", ["semester"])

    # ── 14. semester_results ─────────────────────────────────────────────────
    op.create_table(
        "semester_results",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("student_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("sgpa", sa.Numeric(4, 2), nullable=False, server_default="0"),
        sa.Column("total_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_grade_points", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "semester", name="uq_semester_result"),
    )
    op.create_index("ix_semester_results_student_id", "semester_results", ["student_id"])


def downgrade() -> None:
    op.drop_table("semester_results")
    op.drop_table("subject_grades")
    op.drop_table("exam_results")
    op.drop_table("question_grades")
    op.drop_table("answer_sheets")
    op.drop_table("exam_questions")
    op.drop_table("exams")
    op.drop_table("subject_grade_configs")
    op.drop_table("course_outcomes")

    op.drop_index("ix_quiz_attempts_quiz_student", table_name="quiz_attempts")
    for col in (
        "violations", "auto_submitted", "face_multiple_seconds", "face_absent_seconds",
        "copy_paste_attempts", "fullscreen_exits", "tab_switch_count", "started_at",
        "is_proctored", "marks_possible", "marks_obtained", "attempt_number", "mode",
    ):
        op.drop_column("quiz_attempts", col)
    for col in ("bloom", "co", "marks"):
        op.drop_column("questions", col)
    for col in (
        "total_marks", "cie_component", "available_until", "available_from",
        "requires_proctoring", "max_attempts", "mode",
    ):
        op.drop_column("quizzes", col)
    op.drop_index("ix_student_profiles_usn", table_name="student_profiles")
    op.drop_column("student_profiles", "section")
    op.drop_column("student_profiles", "usn")
    for col in (
        "see_lab_max", "see_theory_max", "cie_lab_max", "cie_theory_max",
        "has_lab_split", "see_max", "cie_max", "credits", "category",
    ):
        op.drop_column("subjects", col)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name in GRADING_ENUMS:
            sa.Enum(name=name).drop(bind, checkfirst=True)
