"""One-shot migration: local SQLite  →  a target Postgres (Cloud SQL).

Why not just `alembic upgrade head`? The baseline revision (001_phase4_baseline)
is an intentional no-op — the original schema was applied out-of-band — so a
fresh Postgres can't be built by replaying migrations. Instead we:

  1. CREATE EXTENSION vector            (embedding columns need the pgvector type)
  2. Base.metadata.create_all(dest)     (build the full current 49-table schema)
  3. TRUNCATE every table               (idempotent — safe to re-run)
  4. copy every populated table in FK-dependency order
  5. reset any serial sequences

Embedding columns are stored as pgvector text ('[-0.04,0.05,...]') in SQLite;
we json.loads them to a list so the pgvector bind-processor re-encodes them for
Postgres. SQLite doesn't enforce foreign keys, so the source may contain orphan
rows (e.g. a resume whose student was deleted); Postgres rejects those, so we
fall back to row-by-row inserts and skip only the broken rows.

After this script, run `alembic stamp head` against the same DB so the
container's boot-time `alembic upgrade head` is a clean no-op.

Usage (from backend/, with the venv + PYTHONPATH=backend):
    DEST_DATABASE_URL='postgresql+psycopg2://postgres:PW@HOST:5432/campusiq' \
        .venv/bin/python scripts/migrate_to_postgres.py
"""
from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError

# Import every model so Base.metadata is fully populated before create_all.
import app.models  # noqa: F401
from app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - pgvector always present in prod now
    Vector = None


SRC_URL = os.environ.get("SRC_DATABASE_URL", "sqlite:///./campusiq.db")
DEST_URL = os.environ.get("DEST_DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")
if not DEST_URL:
    sys.exit("ERROR: set DEST_DATABASE_URL (or pass the Postgres URL as argv[1])")
if not DEST_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
    sys.exit("ERROR: DEST_DATABASE_URL must be a Postgres URL")

print(f"SOURCE : {SRC_URL}")
print(f"DEST   : {DEST_URL.split('@')[-1]}")  # never print credentials

src = create_engine(SRC_URL)
dest = create_engine(DEST_URL)


def vector_columns(table) -> set[str]:
    if Vector is None:
        return set()
    return {c.name for c in table.columns if isinstance(c.type, Vector)}


# 1 + 2 — extension then schema
with dest.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
print("pgvector extension ready")

Base.metadata.create_all(dest)
tables = Base.metadata.sorted_tables  # FK-dependency order (parents first)
print(f"schema ready on dest ({len(tables)} tables)")

# 3 — clean slate (idempotent re-runs); reverse order, CASCADE covers the rest
with dest.begin() as conn:
    names = ", ".join(t.name for t in reversed(tables))
    conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
print("dest truncated")

# 4 — copy data
total = 0
skipped_total = 0
for table in tables:
    vcols = vector_columns(table)
    with src.connect() as sconn:
        rows = [dict(r._mapping) for r in sconn.execute(select(table))]
    if not rows:
        continue
    if vcols:
        for r in rows:
            for c in vcols:
                v = r.get(c)
                if isinstance(v, str) and v:
                    r[c] = json.loads(v)  # '[...]' text -> list[float]
    try:
        with dest.begin() as dconn:
            dconn.execute(table.insert(), rows)
        inserted, skipped = len(rows), 0
    except IntegrityError:
        # SQLite never enforced FKs, so the source can hold orphan rows that
        # Postgres rejects. Retry row-by-row, skipping only the broken ones.
        inserted, skipped = 0, 0
        for r in rows:
            try:
                with dest.begin() as dconn:
                    dconn.execute(table.insert().values(**r))
                inserted += 1
            except IntegrityError:
                skipped += 1
    total += inserted
    skipped_total += skipped
    suffix = f"   ({skipped} orphan rows skipped)" if skipped else ""
    print(f"  {table.name:<34} {inserted:>5} rows{suffix}")

print(f"copied {total} rows  ({skipped_total} orphan rows skipped across all tables)")

# 5 — reset serial sequences (UUID PKs have none; this is a no-op for them)
with dest.begin() as conn:
    for table in tables:
        for col in table.primary_key.columns:
            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:t, :c)"),
                {"t": table.name, "c": col.name},
            ).scalar()
            if seq:
                conn.execute(
                    text(
                        f"SELECT setval('{seq}', "
                        f"COALESCE((SELECT MAX({col.name}) FROM {table.name}), 1))"
                    )
                )
print("sequences reset")
print("MIGRATION COMPLETE")
