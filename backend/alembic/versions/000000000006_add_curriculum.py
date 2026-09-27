"""add coding curriculum: patterns + problem metadata

Phase 2 of the DSA Coach. Adds the `coding_patterns` table (38 DSA patterns)
and the curriculum columns on `coding_problems` so the 388-problem LeetCode
track can be grouped by pattern and ordered easy->hard.

Existing judge columns (function_signature, test cases, starter code, ...) are
left NOT NULL — curriculum (LeetCode-only) problems are seeded with empty
values and distinguished by `source='curriculum'`. So this migration only
CREATEs a table and ADDs columns; it never alters an existing column (keeps
SQLite happy, no table rebuild).

Revision ID: 000000000006
Revises: 000000000005
Create Date: 2026-06-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000006"
down_revision: Union[str, Sequence[str], None] = "000000000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "coding_patterns",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("track", sa.String(length=20), nullable=False, server_default="core"),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("core_idea", sa.Text(), nullable=False, server_default=""),
        sa.Column("recognize_when", sa.Text(), nullable=False, server_default=""),
        sa.Column("difficulty_span", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("problem_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_coding_patterns_slug", "coding_patterns", ["slug"], unique=True)

    # Curriculum columns on coding_problems.
    op.add_column(
        "coding_problems",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="seed_inapp"),
    )
    op.add_column("coding_problems", sa.Column("pattern_id", sa.UUID(), nullable=True))
    op.create_index("ix_coding_problems_pattern_id", "coding_problems", ["pattern_id"])
    if dialect == "postgresql":
        op.create_foreign_key(
            "fk_coding_problems_pattern_id",
            "coding_problems",
            "coding_patterns",
            ["pattern_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.add_column("coding_problems", sa.Column("track", sa.String(length=20), nullable=True))
    op.add_column("coding_problems", sa.Column("tier", sa.Integer(), nullable=True))
    op.add_column("coding_problems", sa.Column("seq", sa.Integer(), nullable=True))
    op.add_column("coding_problems", sa.Column("lc_number", sa.Integer(), nullable=True))
    op.add_column("coding_problems", sa.Column("priority", sa.String(length=20), nullable=True))
    op.add_column(
        "coding_problems",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("coding_problems", sa.Column("free_alternative", sa.String(length=255), nullable=True))
    op.add_column("coding_problems", sa.Column("also_appears_in", sa.String(length=120), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("fk_coding_problems_pattern_id", "coding_problems", type_="foreignkey")
    for col in (
        "also_appears_in",
        "free_alternative",
        "is_premium",
        "priority",
        "lc_number",
        "seq",
        "tier",
        "track",
        "pattern_id",
        "source",
    ):
        op.drop_column("coding_problems", col)
    op.drop_index("ix_coding_patterns_slug", table_name="coding_patterns")
    op.drop_table("coding_patterns")
