"""add usernames + per-subject enrollment

- Adds `users.username` (unique). It's added NULLABLE, existing rows are
  backfilled from the email local-part (deduped), then a UNIQUE index is created.
  The app always sets a username on signup, so it behaves as required going
  forward (the model declares it NOT NULL; create_all in tests enforces that).
- Creates `subject_enrollments` (student <-> subject), unique on
  (subject_id, student_id).

Only CREATE/ADD/INDEX + a data backfill — no column alters, so SQLite needs no
table rebuild.

Revision ID: 000000000007
Revises: 000000000006
Create Date: 2026-06-09 00:00:00.000000
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000007"
down_revision: Union[str, Sequence[str], None] = "000000000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slug(local: str) -> str:
    return re.sub(r"[^a-z0-9_.]+", "", (local or "").lower())


def upgrade() -> None:
    # 1. username column (nullable for the backfill).
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))

    # 2. backfill existing rows from the email local-part, deduped.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users")).fetchall()
    seen: set[str] = set()
    for row in rows:
        uid, email = row[0], row[1]
        base = _slug((email or "").split("@")[0]) or "user"
        if len(base) < 3:
            base = (base + "user")
        base = base[:30]
        uname = base
        n = 1
        while uname in seen:
            suffix = str(n)
            uname = base[: 30 - len(suffix)] + suffix
            n += 1
        seen.add(uname)
        conn.execute(
            sa.text("UPDATE users SET username = :u WHERE id = :id"),
            {"u": uname, "id": uid},
        )

    # 3. unique index now that every row has a distinct username.
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # 4. per-subject enrollment table.
    op.create_table(
        "subject_enrollments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.UUID(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("subject_id", "student_id", name="uq_subject_enrollment"),
    )
    op.create_index("ix_subject_enrollments_subject_id", "subject_enrollments", ["subject_id"])
    op.create_index("ix_subject_enrollments_student_id", "subject_enrollments", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_subject_enrollments_student_id", table_name="subject_enrollments")
    op.drop_index("ix_subject_enrollments_subject_id", table_name="subject_enrollments")
    op.drop_table("subject_enrollments")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
