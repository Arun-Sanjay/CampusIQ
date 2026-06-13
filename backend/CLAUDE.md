# Backend — Claude rules

FastAPI + SQLAlchemy 2 (sync) + Alembic + Pydantic v2. Read `../CLAUDE.md` first for project-wide rules. This file covers backend-specific conventions and the gotchas you only learn by stepping on them.

## The cwd gotcha (read this first)

**Always `cd backend` before starting the app or running pytest.** `app/core/config.py` uses `SettingsConfigDict(env_file=(".env", "../.env"))`, resolved relative to the **process's current working directory**, not to `app/`. Launch from the project root and:

- `backend/.env` is never read.
- `database_url` falls back to its default `sqlite:///./campusiq.db`.
- An empty `campusiq.db` is created at the project root, the app points at it, and the real DB at `backend/campusiq.db` (with seeded users + tables) is silently bypassed.

Symptoms: login fails with "user not found" though the same credentials worked yesterday; document/quiz tables look empty. Fix: stop the server, delete the bogus `campusiq/campusiq.db`, restart from `backend/`.

```bash
# Correct
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Also correct (if you must launch from root)
.venv/bin/python -m uvicorn app.main:app --reload --port 8000 --env-file backend/.env
```

`.claude/launch.json` uses `--app-dir backend`, which sets the import path but **does not** change cwd — same bug. Prefer the manual `cd backend` invocation.

## Run / verify

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
.venv/bin/python -m pytest                              # all tests
.venv/bin/python -m pytest tests/test_auth.py -k login  # one test
.venv/bin/python -m alembic upgrade head                # apply migrations
```

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok",...}`. **The local venv (`backend/.venv`) is Python 3.14**; the Docker image and CI both pin **Python 3.12**. There's no `.python-version` file — don't assume the three match.

## Layout

```
backend/
├── app/
│   ├── main.py                 # create_application(), CORS, lifespan, /audio static mount, /health
│   ├── core/                   # config.py (Settings, active_anthropic_model), database.py, security.py
│   ├── api/
│   │   ├── deps.py             # DbSession, get_current_user, require_role, claude_rate_limit
│   │   ├── router.py           # mounts every route module under /api/v1/<prefix>
│   │   └── routes/             # 23 endpoint modules — see below
│   ├── models/                 # 9 SQLAlchemy files (40 tables) + _enum_helper.py
│   ├── schemas/                # Pydantic request/response shapes (one file per domain)
│   ├── services/               # 52 service modules — business logic lives here
│   ├── tasks/                  # background task wrappers (currently empty scaffold)
│   └── utils/
├── alembic/versions/           # 7 chained migrations (001 baseline → 007) — see below
├── scripts/                    # seed_demo.py, reset_demo.py, import_curriculum.py (+ README)
├── tests/                      # conftest.py + 11 test modules
├── uploads/audio/              # gitignored — generated audio served at /audio
├── Dockerfile                  # multi-stage python:3.12-slim; runs alembic upgrade head then uvicorn
├── requirements.txt
├── requirements-dev.txt        # -r requirements.txt + pytest, pytest-asyncio, openpyxl
└── .env, .env.example
```

## Routes

23 modules, all mounted at `/api/v1/<prefix>` in `app/api/router.py`. One module per domain — when you add an endpoint, find the existing module first instead of creating a new one.

Prefixes: `/auth`, `/subjects`, `/enrollments`, `/documents`, `/college-documents`, `/chat`, `/quizzes`, `/dashboard`, `/announcements`, `/analytics`, `/resume`, `/skills`, `/interviews`, `/confidence`, `/jobs`, `/community`, `/gamification`, `/algorithms`, `/admin`, **`/ws` (WebSocket — notifications, not REST)**, `/boss-battles`, `/profile/public` (public, unauthenticated), `/coding`.

Routes are thin: validate input → call a service → return the response. Role gates use `require_role(...)` dependencies; `/profile/public` is intentionally open.

## Models + migrations (the schema is now incremental)

9 table-bearing model files (`user`, `content`, `chat`, `quiz`, `coding`, `community`, `placement`, `gamification`, `algorithm`, + the `_enum_helper.py` helper), 40 tables total. `_enum_helper.enum_values(...)` feeds `Enum(..., values_callable=...)` so the DB stores enum **values** (`"student"`), not Python member names (`"STUDENT"`).

The schema is **incremental** — a baseline plus 6 chained revisions:

1. `000000000001_phase4_baseline` — baseline (the real schema was applied out-of-band via Supabase; this exists so later revisions have a parent).
2. `000000000002_add_admin_knowledge_chat_type` — `admin_knowledge` chat-type enum value.
3. `000000000003_add_assistant_meta` — `chat_messages.assistant_meta` JSON.
4. `000000000004_add_coding_platform` — `coding_problems` + `coding_submissions`.
5. `000000000005_add_dsa_coach` — `dsa_coach` chat type + `coding_problem_id` + `leetcode_url`.
6. `000000000006_add_curriculum` — `coding_patterns` + problem-metadata columns.
7. `000000000007_usernames_and_enrollment` — usernames + `subject_enrollments`.

When the schema changes:

1. Edit the SQLAlchemy model in `app/models/<file>.py`.
2. Generate a revision: `alembic revision --autogenerate -m "what changed"`.
3. **Inspect it before running** — autogenerate misses enum-value changes (revisions 2 and 5 add enum values by hand).
4. `alembic upgrade head`. (The Docker image runs this on every boot, so revisions must be idempotent-safe.)

`app.models.__init__` re-exports every model; the lifespan handler does `import app.models` on startup so SQLAlchemy registers everything before any query — don't lazy-import models elsewhere.

**Vector columns** (`document_chunks.embedding`, `college_document_chunks.embedding`, `job_listings.embedding`) are typed `Vector(384)` (pgvector) at the ORM level regardless of dialect. The dialect branch happens at **query time** in `vector_search.py` (`_is_sqlite()` → Python cosine loop; Postgres → pgvector `<=>` / `cosine_distance`). `pgvector` is imported but **not pinned** in requirements — flag if you touch deps.

## Auth + dependency injection

```python
from app.api.deps import DbSession, get_current_user
from app.models.user import User

@router.get("/me")
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse: ...
```

- `DbSession` is the typed session dependency.
- `get_current_user` resolves the JWT from `Authorization: Bearer <token>` (`HTTPBearer(auto_error=False)`, so we control the 401 message). Inactive accounts → 403; missing/invalid token → 401.
- For role gates, use `require_role(UserRole.teacher)` rather than checking inline.

JWT: HS256, 7-day expiry (`JWT_EXPIRE_MINUTES=10080`), `bcrypt(rounds=12)` for passwords. The secret comes from `JWT_SECRET_KEY`; the default is `change-me-in-production`. **Note:** nothing in the code rejects that default at startup (despite what older docs claimed) — it MUST be overridden in prod via the Render env var. Don't rely on a startup guard that doesn't exist.

## AI cost rule (every Claude call must respect this)

Two independent layers — wire both:

1. **Model selection** — route through `app/services/claude_client.py`, which always reads `settings.active_anthropic_model` (`claude-haiku-4-5-20251001` unless `USE_PRODUCTION_MODEL=True` → `claude-opus-4-6`, demo only). Never hardcode the model string. `claude_client` is `@lru_cache`'d, returns `None` when no key is set, and **never raises** — all three entry points (`generate_completion`, `generate_completion_multiturn`, `stream_completion`) catch errors and return `""` / a fallback so callers degrade gracefully.
   - *Forward-looking:* the client passes `temperature`. If you ever bump `anthropic_model_prod` to Opus 4.7/4.8, drop `temperature` — it's removed on those models.
2. **Per-user rate limit** — add the `claude_rate_limit` dependency (`app/api/deps.py`) to any Claude-touching route. It's an in-process token bucket keyed by `user.id`, `CLAUDE_REQUESTS_PER_MINUTE=20` by default, returning 429 + `Retry-After: 5` on exhaustion. Already wired on `chat`, `quizzes`, `resume`, `skills`, `interviews`, `confidence`. (In-process only — multi-replica would need Redis, which we deliberately avoid.)

## External services (all degrade gracefully)

- **Anthropic** — required for AI features; absence returns clean fallbacks (empty output / 503-style responses), never a crash.
- **ElevenLabs** — the **primary speech path**: Scribe (`scribe_v1`) ASR + TTS, one key (`ELEVENLABS_API_KEY`). Without it the frontend falls back to the browser's `SpeechRecognition` / `speechSynthesis`.
- **OpenAI Whisper** — **opt-in ASR fallback** only (`OPENAI_API_KEY`). `speech.py` tries ElevenLabs Scribe first, then Whisper if the key is set, then the browser.
- **Supabase** — only for prod Postgres + Storage + pgvector. Local dev uses SQLite with the cosine fallback in `vector_search.py`.
- **Redis** — `REDIS_URL` is in settings but nothing uses it. `celery` is pinned but unwired. Don't introduce either without asking.

## Config worth knowing (`app/core/config.py`)

All fields read from `backend/.env` (case-insensitive). Beyond the AI/JWT/CORS settings above: `SEED_DSA_CURRICULUM` (default `True`; tests set `False` so the coding suite runs against just the 5 deterministic judge problems, not the full 376), `AUDIO_RETENTION_DAYS=7`, `AUDIO_CLEANUP_INTERVAL_HOURS=6` (set `0` to disable the cleanup loop), `SUPABASE_STORAGE_BUCKET=campusiq-documents`. Computed properties: `active_anthropic_model`, `cors_origins_list`.

## Background work

FastAPI `BackgroundTasks` only — no Celery, no separate worker. Document processing, quiz generation, and embedding jobs all run as `BackgroundTasks` from inside the originating request. Two long-running loops are started by the lifespan handler in `main.py`: the **audio cleanup loop** (`_audio_cleanup_loop`, respects `AUDIO_CLEANUP_INTERVAL_HOURS=0` to disable) and the **TCP-style notification retry loop** (`notifications_service.start_retry_loop`). Both are cancelled cleanly on shutdown.

## WebSockets / notifications

`app/services/notifications.py` captures the running event loop at lifespan startup (`set_main_loop`) so synchronous handlers (e.g. inside a quiz-grading request) can dispatch WS messages via `run_coroutine_threadsafe` — use the `publish_sync` helper there, don't grab a fresh loop. Every notification is persisted to `notification_delivery` even if no socket is connected; the retry loop re-pushes un-ACKed deliveries with exponential backoff, and the client ACKs over WS. **WS auth is via a query-param token** (`/api/v1/ws/notifications?token=...`) because the handshake doesn't carry `Authorization` headers.

## Service-per-feature pattern

Each feature gets its own file in `app/services/`. The **pure-logic algorithm services take primitives in and return primitives out, no DB**: `dijkstra.py`, `knapsack.py`, `mst.py` (Prim's), `huffman.py`, `backtracking_schedule.py`, `spread_schedule.py`. Keep them pure. Note that three "algorithm" services **do** take a `Session` and hit the DB despite their names — `hamming.py` (loads quiz attempts, persists similarity flags), `inclusion_exclusion.py` (student profiles), `graph_coloring.py` (quiz slots); don't assume every algorithm file is DB-free. The DB-backed graph itself lives in `skill_graph.py` / `skill_graph_seed.py` / `skill_tree.py`.

## Tests

- pytest, 11 modules: `test_auth`, `test_dashboards`, `test_algorithms`, `test_schedules`, `test_speech_cleanup`, `test_chat_modes`, `test_coding`, `test_enrollment`, `test_knowledge_editor`, `test_notifications`, `test_rate_limit`.
- `conftest.py` sets env vars **before** importing app modules, builds one file-backed SQLite DB per session via `Base.metadata.create_all()` (no Alembic in tests), **repoints `app.core.database.SessionLocal`** at the test engine (so background workers see test tables), and truncates every table after each test. It forces `AUDIO_CLEANUP_INTERVAL_HOURS=0` and `SEED_DSA_CURRICULUM=false`.
- CI runs `pytest -ra` from `backend/` on Python 3.12 with `DATABASE_URL=sqlite:///./_ci.db`, `JWT_SECRET_KEY=ci-secret-do-not-use-in-prod`, `AUDIO_CLEANUP_INTERVAL_HOURS=0`.
- When you add a service that talks to Claude / ElevenLabs / Whisper, **mock the client** in the test — never hit the real API from CI.

## Scripts (`backend/scripts/`)

- `seed_demo.py` — seeds the 4 canonical demo accounts + rich state (password `DemoPass123`); idempotent, `--reset` to wipe + reseed.
- `reset_demo.py` — deletes only the 4 demo accounts (FK CASCADE).
- `import_curriculum.py` — dev-only, regenerates `app/services/dsa_curriculum.json` from the source spreadsheet (needs `openpyxl`). The app reads the JSON at runtime, so openpyxl isn't a prod dependency.

## Audio storage

Voice interview + confidence recordings are written to `backend/uploads/audio/` and served via the static mount at `/audio` (`main.py`). They auto-purge after `AUDIO_RETENTION_DAYS=7`. Don't commit anything from `uploads/`; it's gitignored.

## Don't do this

- Don't add a `Co-Authored-By: Claude` trailer to commits (project-wide rule).
- Don't introduce LangGraph / LangChain — the interview state machine is intentionally hand-rolled (`mock_interview.py`).
- Don't add Celery / RQ / Dramatiq, or start using Redis. `BackgroundTasks` until proven insufficient.
- Don't bypass `active_anthropic_model` by hardcoding a model string — it quietly burns the demo budget.
- Don't add a Claude-calling route without the `claude_rate_limit` dependency.
- Don't run `alembic downgrade base` against a real DB without confirming first; the baseline migration drops the entire schema.
