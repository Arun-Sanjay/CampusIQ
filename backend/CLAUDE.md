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

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok",...}`. **The local venv (`backend/.venv`) is Python 3.14**; the Docker image and CI both pin **Python 3.12**. There's no `.python-version` file (and the Dockerfile's "3.12 locally" comment is stale) — don't assume the three match.

## Layout

```
backend/
├── app/
│   ├── main.py                 # create_application(), CORS, lifespan, /audio static mount, /health
│   ├── core/                   # config.py (Settings, active_anthropic_model), database.py, security.py
│   ├── api/
│   │   ├── deps.py             # DbSession, get_current_user, require_role, claude_rate_limit
│   │   ├── router.py           # mounts every route module under /api/v1/<prefix>
│   │   └── routes/             # 25 endpoint modules — see below
│   ├── models/                 # 10 table-bearing SQLAlchemy files (49 tables) + _enum_helper.py
│   ├── schemas/                # Pydantic request/response shapes (one file per domain)
│   ├── services/               # 60 service modules — business logic lives here
│   ├── tasks/                  # background task wrappers (currently empty scaffold)
│   └── utils/
├── alembic/versions/           # 8 chained migrations (001 baseline → 008) — see below
├── scripts/                    # seed_demo.py, reset_demo.py, import_curriculum.py (+ README)
├── uploads/                    # gitignored — audio/ (served at /audio) + grading/ (served behind auth)
├── tests/                      # conftest.py + 15 test modules
├── Dockerfile                  # multi-stage python:3.12-slim; runs alembic upgrade head then uvicorn
├── requirements.txt
├── requirements-dev.txt        # -r requirements.txt + pytest, pytest-asyncio, openpyxl
└── .env, .env.example
```

## Routes

25 modules, all mounted at `/api/v1/<prefix>` in `app/api/router.py`. One module per domain — when you add an endpoint, find the existing module first instead of creating a new one.

Prefixes: `/auth`, `/subjects`, `/enrollments`, `/documents`, `/college-documents`, `/chat`, `/quizzes`, `/dashboard`, `/announcements`, `/analytics`, `/resume`, `/skills`, `/interviews`, `/confidence`, `/jobs`, `/community`, `/gamification`, **`/grading`**, **`/grades`**, `/algorithms`, `/admin`, **`/ws` (WebSocket — notifications, not REST)**, `/boss-battles`, `/profile/public` (public, unauthenticated), `/coding`.

Routes are thin: validate input → call a service → return the response. Role gates use `require_role(...)` dependencies (`require_role` accepts string role names too, and can gate a whole router via `APIRouter(dependencies=[...])` — that's how `/enrollments` is locked to teacher/admin); `/profile/public` is intentionally open.

## Models + migrations (the schema is incremental)

10 table-bearing model files (`user`, `content`, `chat`, `quiz`, `coding`, `community`, `placement`, `gamification`, `algorithm`, **`grading`**) + the `_enum_helper.py` helper, **49 tables total**. `_enum_helper.enum_values(...)` feeds `Enum(..., values_callable=...)` so the DB stores enum **values** (`"student"`), not Python member names (`"STUDENT"`).

Recent table additions: `coding.py` gained `coding_patterns` (the 38-pattern curriculum); `user.py` gained `subject_enrollments` (the roster); `grading.py` (new) holds **9 tables** — `course_outcomes`, `subject_grade_configs`, `exams`, `exam_questions`, `answer_sheets`, `question_grades`, `exam_results`, `subject_grades`, `semester_results`. (CGPA is **not** a table — it's written to `student_profiles.cgpa`. To avoid a circular import, the `SubjectCategory` enum lives in `models/user.py`, not `grading.py`, because `Subject` is defined there.)

The schema is **incremental** — a baseline plus chained revisions (note: revisions **006, 007, 008 are currently untracked** in git, like much of the in-flight work):

1. `000000000001_phase4_baseline` — baseline (the real schema was applied out-of-band via Supabase; this exists so later revisions have a parent).
2. `000000000002_add_admin_knowledge_chat_type` — `admin_knowledge` chat-type enum value.
3. `000000000003_add_assistant_meta` — `chat_messages.assistant_meta` JSON.
4. `000000000004_add_coding_platform` — `coding_problems` + `coding_submissions`.
5. `000000000005_add_dsa_coach` — `dsa_coach` chat type + `coding_problem_id` + `leetcode_url`.
6. `000000000006_add_curriculum` — `coding_patterns` + the 10 curriculum columns on `coding_problems`.
7. `000000000007_usernames_and_enrollment` — `users.username` (added **nullable**, backfilled from the email local-part, then a unique index) + the `subject_enrollments` table.
8. `000000000008_add_grading` — the **9 grading tables** PLUS the quiz-mode/proctoring work: columns on `quizzes` (`mode`, `max_attempts`, proctoring flags, `cie_component`, `total_marks`), `questions` (`marks`, `co`, `bloom`), `quiz_attempts` (the proctor counters + marks), and grading columns on `subjects` (`category`, `credits`, `cie_max`/`see_max`, lab splits) + `student_profiles` (`usn`, `section`). Pre-creates Postgres enum types up-front with `create_type=False`; SQLite-safe (CREATE/ADD/INDEX only).

When the schema changes:

1. Edit the SQLAlchemy model in `app/models/<file>.py`.
2. Generate a revision: `alembic revision --autogenerate -m "what changed"`.
3. **Inspect it before running** — autogenerate misses enum-value changes (revisions 2 and 5 add enum values by hand) and Postgres-only DDL (008 hand-creates enum types and guards FKs to stay SQLite-safe).
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

**Login accepts email OR username.** `LoginRequest` has an optional `identifier` (preferred) and a legacy `email`, with a `login_id` property that lowercases whichever is set; `auth.get_user_by_identifier` tries email then username. Every signup must supply a `username` (`SignupRequest`, 3–30 chars, lowercased, `^[a-z0-9][a-z0-9_.]{2,29}$`); duplicates → 409. `users.username` is `String(50)`, unique, not-null at the model level (the migration adds it nullable + backfills, so prod and `create_all`-based tests differ on DB-level nullability).

JWT: HS256, 7-day expiry (`JWT_EXPIRE_MINUTES=10080`), `bcrypt(rounds=12)` for passwords. The secret comes from `JWT_SECRET_KEY`; the default is `change-me-in-production`. **Note:** nothing in the code rejects that default at startup — it MUST be overridden in prod via the Render env var. Don't rely on a startup guard that doesn't exist.

## AI cost rule (every Claude call must respect this)

Two independent layers — wire both:

1. **Model selection** — route through `app/services/claude_client.py`, which always reads `settings.active_anthropic_model` (`claude-haiku-4-5-20251001` unless `USE_PRODUCTION_MODEL=True` → `claude-opus-4-6`, demo only). Never hardcode the model string. `claude_client` is `@lru_cache`'d, returns `None` when no key is set, and **never raises** — all **four** entry points catch errors and return `""` / a fallback so callers degrade gracefully:
   - `generate_completion` (single-turn), `generate_completion_multiturn` (chat history, e.g. Resume Coach), `stream_completion` (SSE deltas), and **`generate_completion_vision`** (single-turn text + N images, base64; used by the answer-sheet grader and the scanned-scheme parser). The vision path caps at `MAX_IMAGES_PER_VISION_CALL=8` and `MAX_IMAGE_BYTES=4 MB`, sniffs the image MIME from magic bytes (no Pillow), and skips oversized images.
   - *Forward-looking:* the client passes `temperature`. If you ever bump `anthropic_model_prod` to Opus 4.7/4.8, drop `temperature` on all four entry points — it's removed on those models.
2. **Per-user rate limit** — add the `claude_rate_limit` dependency (`app/api/deps.py`) to any Claude-touching route. It's an in-process token bucket keyed by `user.id`, `CLAUDE_REQUESTS_PER_MINUTE=20` by default, returning 429 + `Retry-After: 5` on exhaustion. Already wired on `chat`, `quizzes` (generate), `resume`, `skills`, `interviews`, `confidence`, and the `grading` scheme-parse / grade / regrade / upload routes. (In-process only — multi-replica would need Redis, which we deliberately avoid.) The grader is **additionally serialized per-exam** with a process-local `threading.Lock` (`_exam_locks` in `answersheet_grader.py`) so a batch upload makes one vision call at a time.

## Grading subsystem (AI auto-grader — `grading.py`/`grades.py` routes)

The biggest recent addition. Teacher uploads a marking scheme + scanned answer sheets; Claude vision OCRs and grades them; the teacher reviews/overrides; a pure engine rolls everything up to RVCE-style grades. **The seam is the `exam_results` table** — the AI grader and any manual/quiz path write it, the grade engine only reads it.

Pipeline (services run as `BackgroundTasks`, each opening its own session):

1. `grading.create_exam` — a teacher creates an `Exam` for a subject (`kind` = quiz/test/experiential/lab/see).
2. `scheme_parser.process_scheme` — parses the uploaded answer-key PDF into `ExamQuestion`s + `CourseOutcome`s. Text-first (`text_extraction`), **Claude-vision fallback** for scanned schemes. Sets `scheme_status` → `parsing` → `review`.
3. Teacher reviews/edits questions, then `confirm_scheme` → `scheme_status = ready`. **Grading is blocked until `ready`** (hard gate).
4. `answersheet_ingest` — rasterizes uploaded PDFs/images to PNG pages (via `grading_images`/PyMuPDF), creates `AnswerSheet` rows, schedules grading.
5. `answersheet_grader.grade_answer_sheet` — **one fused Claude-vision call per student** (OCR + grade + USN/name detection). Writes `QuestionGrade` rows, flags low-confidence ones, rolls up totals. Idempotent re-grade preserves teacher overrides (unless `force=True`).
6. `answersheet_match.match_student` — matches detected USN/name against the roster (exact USN → fuzzy USN → fuzzy name, inlined Levenshtein, no new dep). Teacher confirms.
7. `grading_results.upsert_result` — rolls per-question "effective" marks into one `ExamResult` + `per_co` JSON.
8. Teacher overrides flagged grades + finalizes → `grading.recompute_subject_grade` calls the **pure, no-DB `grade_engine`** (condensation, CIE/SEE pass gates, 10-point grade table, CO attainment) → `SubjectGrade` → `recompute_semester` (SGPA) → `recompute_cgpa` (writes `student_profiles.cgpa`).

`/grading` endpoints are teacher/admin-only (exam/scheme/question/sheet/review/override/finalize/config CRUD + `GET /exams/{id}/attainment`). `/grades` has `GET /grades/me` (any user's own transcript) and `GET /grades/class` (teacher/admin).

Gotchas:
- **Answer-sheet page images live in `backend/uploads/grading/{exam_id}/{sheet_id}/page_NNN.png`** and are served **only** via the authenticated `GET /grading/answer-sheets/{id}/pages/{idx}` FileResponse (ownership-checked) — **not** a static mount (contrast `/audio`). That's why the frontend has `AuthedImage`. `uploads/` is gitignored.
- **No new OCR deps** — rasterization is PyMuPDF (`fitz`, already used by `text_extraction`); OCR is Claude vision. No Tesseract/OpenCV/Pillow.
- `grade_engine.py` is pure math (like `dijkstra.py`) — keep it DB-free; it's unit-tested against `grading_mdfiles/grading_feature_spec.md`. Failing any gate (CIE <40%, SEE <35%, aggregate <40%, or theory/lab separately) forces **F / grade-point 0**. Transitional/provisional grades are excluded from SGPA/CGPA.
- **CO attainment** is computed and surfaced; the CO→PO mapping itself is not implemented.

## Enrollment (content gating — `enrollment.py`, `/enrollments`)

`subject_enrollments` (in `models/user.py`) is a thin join: `subject_id`, `student_id`, `enrolled_at`, unique `(subject_id, student_id)`. **No status column** — enrolled is pure row-existence; unenroll hard-deletes. The whole `/enrollments` router is `require_role("teacher","admin")` (students get 403); teachers enroll a student **by username** (`POST /enrollments/subjects/{id}` with `{username}`, idempotent), and `_require_owned_subject` gates ownership (admins may manage any).

`enrollment.py` exposes the gate helpers (`enrolled_subject_ids_for_student`, `enrolled_student_ids_for_subject`, `enrolled_student_count_for_teacher`) imported by `quiz.py`, `announcement.py`, `task_feed.py`, `dashboard.py`, and `grading.py` — so a student only sees quizzes/announcements for subjects they're enrolled in. `seed_demo.py` auto-enrolls the demo student to keep demo content visible.

## Quiz modes + proctoring (`quiz.py`, `quiz_generator.py`)

A quiz now has a `mode` (enum `QuizMode`):
- **`practice`** — unlimited attempts (`max_attempts=0`), unproctored, no CIE feed. Legacy behavior.
- **`test`** — single attempt, proctored, feeds the subject's CIE. Generated questions carry per-question `marks`/`co`/`bloom`; scoring is marks-based. `cie_component` (`CIEComponent` enum: `quiz_1/quiz_2/test_1/test_2`) says which CIE bucket it fills.

Endpoints beyond the usual CRUD/generate (prefix `/quizzes`): `POST /{id}/attempts/start` (server-stamps `started_at` as the timer anchor, enforces availability window + single-attempt — an in-progress row is identified by `total_questions==0`), `POST /{id}/proctor-events` (logs one client-side event), `GET /{id}/proctor-report` (teacher/admin per-student counters + violation log). Proctoring data lives on `quiz_attempts` (`tab_switch_count`, `fullscreen_exits`, `copy_paste_attempts`, `face_absent_seconds`, `auto_submitted`, a `violations` JSON log) — **no camera images are stored**; integrity rests on the server (timer + single-attempt + availability), not the client locks.

On submit, a `test`-mode attempt **feeds CIE**: `_feed_cie_from_attempt` creates/updates an `Exam` (linked by `quiz_id`) + `ExamResult` (`source=quiz`) and recomputes the subject grade — wrapped in try/except so a CIE-wiring failure only logs a warning and never breaks quiz submission. (No dedicated migration — these columns ride in migration 008.)

## External services (all degrade gracefully)

- **Anthropic** — required for AI features (text + vision); absence returns clean fallbacks (empty output / 503-style responses), never a crash.
- **ElevenLabs** — the **primary speech path**: Scribe (`scribe_v1`) ASR + TTS, one key (`ELEVENLABS_API_KEY`). Without it the frontend falls back to the browser's `SpeechRecognition` / `speechSynthesis`.
- **OpenAI Whisper** — **opt-in ASR fallback** only (`OPENAI_API_KEY`). `speech.py` tries ElevenLabs Scribe first, then Whisper if the key is set, then the browser.
- **Supabase** — only for prod Postgres + Storage + pgvector. Local dev uses SQLite with the cosine fallback in `vector_search.py`.
- **Redis** — `REDIS_URL` is in settings but nothing uses it. `celery` is pinned but unwired. Don't introduce either without asking.

## Config worth knowing (`app/core/config.py`)

All fields read from `backend/.env` (case-insensitive). Beyond the AI/JWT/CORS settings above: `SEED_DSA_CURRICULUM` (default `True`; tests set `False` so the coding suite runs against just the 5 deterministic judge problems, not the full 376), `AUDIO_RETENTION_DAYS=7`, `AUDIO_CLEANUP_INTERVAL_HOURS=6` (set `0` to disable the cleanup loop), `SUPABASE_STORAGE_BUCKET=campusiq-documents`. Computed properties: `active_anthropic_model`, `cors_origins_list`.

## Background work

FastAPI `BackgroundTasks` only — no Celery, no separate worker. Document processing, quiz generation, embedding jobs, and **answer-sheet grading** all run as `BackgroundTasks` from inside the originating request. The BackgroundTask graders (`answersheet_grader`, `scheme_parser`) and `document_processor` import `SessionLocal` **inside the function** so the test suite's repointed `SessionLocal` is used. Two long-running loops are started by the lifespan handler in `main.py`: the **audio cleanup loop** (`_audio_cleanup_loop`, respects `AUDIO_CLEANUP_INTERVAL_HOURS=0` to disable) and the **TCP-style notification retry loop** (`notifications_service.start_retry_loop`). Both are cancelled cleanly on shutdown.

## WebSockets / notifications

`app/services/notifications.py` captures the running event loop at lifespan startup (`set_main_loop`) so synchronous handlers (e.g. inside a quiz-grading request) can dispatch WS messages via `run_coroutine_threadsafe` — use the `publish_sync` helper there, don't grab a fresh loop. Every notification is persisted to `notification_delivery` even if no socket is connected; the retry loop re-pushes un-ACKed deliveries with exponential backoff, and the client ACKs over WS. **WS auth is via a query-param token** (`/api/v1/ws/notifications?token=...`) because the handshake doesn't carry `Authorization` headers.

## Service-per-feature pattern

Each feature gets its own file in `app/services/`. The **pure-logic algorithm services take primitives in and return primitives out, no DB**: `dijkstra.py`, `knapsack.py`, `mst.py` (Prim's), `huffman.py`, `backtracking_schedule.py`, `spread_schedule.py`, and now **`grade_engine.py`** (condensation / pass-gates / grade table / SGPA-CGPA). Keep them pure. Note that three "algorithm" services **do** take a `Session` and hit the DB despite their names — `hamming.py` (loads quiz attempts, persists similarity flags), `inclusion_exclusion.py` (student profiles), `graph_coloring.py` (quiz slots); don't assume every algorithm file is DB-free. The DB-backed graph itself lives in `skill_graph.py` / `skill_graph_seed.py` / `skill_tree.py`. The grading domain service `grading.py` is the orchestrator (CRUD + the recompute cascade); `answersheet_match.py` inlines a Levenshtein so no new dep is added.

## Tests

- pytest, **15 modules**: `test_auth`, `test_dashboards`, `test_algorithms`, `test_schedules`, `test_speech_cleanup`, `test_chat_modes`, `test_coding`, `test_enrollment`, `test_knowledge_editor`, `test_notifications`, `test_rate_limit`, `test_quiz_modes` (practice vs proctored test, availability window, CIE feed), `test_grade_engine` (pure engine vs the spec), `test_grades` (transcript/SGPA/CGPA + `/grades` API), `test_grading` (the full upload→match→grade→review→override→finalize flow with **Claude vision mocked**).
- `conftest.py` sets env vars **before** importing app modules (including `SEED_DSA_CURRICULUM=false` and `AUDIO_CLEANUP_INTERVAL_HOURS=0`), builds one file-backed SQLite DB per session via `Base.metadata.create_all()` (no Alembic in tests), **repoints `app.core.database.SessionLocal`** at the test engine (so background workers see test tables), and truncates every table after each test. Its signup helper now includes a valid `username`.
- CI runs `pytest -ra` from `backend/` on Python 3.12 with `DATABASE_URL=sqlite:///./_ci.db`, `JWT_SECRET_KEY=ci-secret-do-not-use-in-prod`, `AUDIO_CLEANUP_INTERVAL_HOURS=0`.
- When you add a service that talks to Claude / ElevenLabs / Whisper, **mock the client** in the test — never hit the real API from CI. For grading, monkeypatch `claude_client.generate_completion_vision`.

## Scripts (`backend/scripts/`)

- `seed_demo.py` — seeds the 4 canonical demo accounts (`alice.reddy`/teacher, `bharat.iyer`/teacher, `demo.student`/student, `demo.admin`/admin; password `DemoPass123`) + rich state; assigns usernames and **auto-enrolls the demo student** into subjects (content is enrollment-gated now); idempotent, `--reset` to wipe + reseed.
- `reset_demo.py` — deletes only the 4 demo accounts (FK CASCADE).
- `import_curriculum.py` — dev-only, regenerates `app/services/dsa_curriculum.json` (38 patterns / 376 problems) from the source `.xlsx` spreadsheet, deduping problems by LeetCode slug (needs `openpyxl`, in requirements-dev only). The app reads the JSON at runtime — `dsa_curriculum_seed.seed_if_empty` lazily seeds it on the first `/coding` read, gated on `coding_patterns` being empty — so openpyxl isn't a prod dependency.

## Audio + grading storage

Voice interview + confidence recordings are written to `backend/uploads/audio/` and served via the static mount at `/audio` (`main.py`). They auto-purge after `AUDIO_RETENTION_DAYS=7`. Answer-sheet page images go to `backend/uploads/grading/...` and are served **only** through the authenticated `/grading/answer-sheets/{id}/pages/{idx}` route — never a static mount. Don't commit anything from `uploads/`; it's gitignored.

## Don't do this

- Don't add a `Co-Authored-By: Claude` trailer to commits (project-wide rule).
- Don't introduce LangGraph / LangChain — the interview state machine is intentionally hand-rolled (`mock_interview.py`).
- Don't add Celery / RQ / Dramatiq, or start using Redis. `BackgroundTasks` until proven insufficient.
- Don't bypass `active_anthropic_model` by hardcoding a model string — it quietly burns the demo budget. This applies to the vision path too.
- Don't add a Claude-calling route without the `claude_rate_limit` dependency.
- Don't store answer-sheet images under a static mount or commit anything from `uploads/`.
- Don't run `alembic downgrade base` against a real DB without confirming first; the baseline migration drops the entire schema.
