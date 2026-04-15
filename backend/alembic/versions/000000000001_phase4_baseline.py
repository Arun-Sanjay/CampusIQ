"""phase 4 baseline: full schema with ~36 tables applied directly via Supabase MCP

This is a baseline revision. The actual schema was applied via Supabase migrations
(tracked in supabase_migrations.schema_migrations), not through Alembic. The
upgrade() and downgrade() functions here are no-ops; this file only exists so
future Alembic migrations have a parent revision to build on.

If you clone this repo fresh and need to recreate the schema, apply the Supabase
migrations listed below — or use SQLAlchemy's `Base.metadata.create_all()` for
local SQLite dev.

Supabase migrations (in order):
    20260406064927_enable_extensions_and_core_enums
    20260406064955_create_user_and_college_tables
    20260406065024_create_content_and_chat_tables
    20260406065056_create_quiz_and_community_tables
    20260406065125_create_placement_tables
    20260406065155_create_gamification_tables
    20260406065232_create_algorithm_feature_tables
    20260406065648_enable_rls_deny_anon_access

Revision ID: 000000000001
Revises:
Create Date: 2026-04-06 10:30:00.000000
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "000000000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — schema was applied directly via Supabase migrations in Phase 4."""
    pass


def downgrade() -> None:
    """No-op — to fully reset, drop all tables in the Supabase dashboard."""
    pass
