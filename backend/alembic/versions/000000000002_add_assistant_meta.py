"""add chat_messages.assistant_meta

Adds a nullable JSON column for per-assistant-message metadata. Currently used
by Note Assistant to stash `{"mode": "explain"|"diagram"|"questions"}` so the
frontend can pick the right structured-output renderer when re-rendering
history.

Old rows get NULL — the renderer treats absent mode as `explain`.

Revision ID: 000000000002
Revises: 000000000001
Create Date: 2026-05-11 08:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000002"
down_revision: Union[str, Sequence[str], None] = "000000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("assistant_meta", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "assistant_meta")
