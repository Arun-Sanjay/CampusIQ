"""add admin_knowledge chat type

Adds the `admin_knowledge` value to the `chat_type` Postgres enum so the
Knowledge Editor's chat sessions can be persisted. On SQLite the enum is
backed by a permissive `VARCHAR + CHECK` constraint, so this migration
is effectively a no-op there (SQLAlchemy regenerates the CHECK on the
next `create_all`). The `IF NOT EXISTS` guard makes the upgrade safe to
re-run.

Revision ID: 000000000002
Revises: 000000000001
Create Date: 2026-05-11 02:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = "000000000002"
down_revision: Union[str, Sequence[str], None] = "000000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # ALTER TYPE ADD VALUE cannot run inside a transaction block on older
        # Postgres versions; use COMMIT + autocommit semantics via raw SQL.
        op.execute("ALTER TYPE chat_type ADD VALUE IF NOT EXISTS 'admin_knowledge'")
    # SQLite: nothing to do — CHECK constraint regenerates on schema sync.


def downgrade() -> None:
    # Postgres has no clean way to drop a single enum value; leaving it in
    # place is the safe no-op. Downgrade is not supported.
    pass
