# CampusIQ

**AI-powered LMS + placement-prep platform for engineering students.**

CampusIQ is a full-stack, role-based academic platform built for engineering
students (originally for RVCE). A single React SPA and a single FastAPI backend
serve three distinct experiences — **student**, **teacher**, and **admin** —
covering everything from RAG-grounded study chat and AI quiz generation to an
**AI answer-sheet auto-grader** that produces RVCE-style CIE/SEE marks, CO
attainment, and SGPA/CGPA.

> **Status:** Live and feature-rich. What began as a 21-phase course build has
> grown well past it. The scaffold-era description this README used to carry is
> long obsolete — the platform now ships dozens of working features across all
> three roles. A mobile/PWA responsiveness pass is the main work currently in
> flight.

- **Live frontend:** https://campusiq-psi.vercel.app
- **Live backend:** Google Cloud Run (`/health` reports `environment: production`)
- **API version:** `0.1.0` · base path `/api/v1`

---

## Table of contents

- [Live demo & accounts](#live-demo--accounts)
- [What's inside (feature map)](#whats-inside-feature-map)
- [Flagship subsystems](#flagship-subsystems)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Getting started (local dev)](#getting-started-local-dev)
- [Environment variables](#environment-variables)
- [Testing & CI](#testing--ci)
- [Deployment](#deployment)
- [AI cost controls](#ai-cost-controls)
- [Project documentation](#project-documentation)
- [At a glance](#at-a-glance)

---

## Live demo & accounts

The hosted stack is seeded with four canonical demo accounts. **Login accepts
either the username or the email**; the password is the same for all four.

| Role    | Username      | Email                      | Password      | Notes                                   |
| ------- | ------------- | -------------------------- | ------------- | --------------------------------------- |
| Teacher | `alice.reddy` | `teacher.a@example.com`    | `DemoPass123` | Owns **DAA** (CD343AI), authored quizzes |
| Teacher | `bharat.iyer` | `teacher.b@example.com`    | `DemoPass123` | Owns **DMS** (CS241AT)                  |
| Student | `demo.student`| `student.demo@example.com` | `DemoPass123` | Enrolled, quiz attempts, resume, CGPA   |
| Admin   | `demo.admin`  | `admin.demo@example.com`   | `DemoPass123` | Platform admin                          |

Seed/refresh this state with `backend/scripts/seed_demo.py` (see
[Getting started](#getting-started-local-dev)). The demo runbook lives in
[`DEMO.md`](./DEMO.md).

---

## What's inside (feature map)

CampusIQ is organized around three roles. Students get two top-level "modes" —
**Learn Mode** (academics) and **Place Mode** (placement prep) — plus a
gamification layer.

### 👩‍🎓 Student · Learn Mode

- **AI Note Assistant** — RAG chat grounded in a teacher's uploaded documents,
  with streaming responses, citations, and Explain / Diagram / Questions modes
  (Mermaid diagrams render inline).
- **CollegeGPT** — a college-wide knowledge assistant grounded in an admin-curated corpus.
- **Quizzes** — AI-generated, adaptive, weak-area-aware. Two modes:
  **practice** (unlimited, unproctored) and **proctored test** (single attempt,
  webcam + anti-cheat, feeds CIE marks).
- **Coding platform** — an in-browser Python judge (Monaco editor + Pyodide
  WASM) over 5 seed problems, plus a **38-pattern / 376-problem DSA curriculum**
  rendered as a pattern grid → pattern detail → problem (non-judge problems link
  out to LeetCode).
- **DSA Coach** — a Socratic, hint-ladder tutor for DSA problems.
- **Study Schedule planner** — weekly planner with spread and backtracking strategies.
- **Crash Mode** — focused last-minute revision.
- **My Grades** — read-only transcript: CIE/SEE marks, per-CO attainment, letter
  grade, per-semester SGPA, and CGPA.

### 💼 Student · Place Mode

- **Resume Builder** — AI coaching, ATS scoring, GitHub import, print-to-PDF.
- **Skill-Gap / Adaptive Learning Engine** — computes a personalized learning
  path using classic algorithms (Dijkstra + Knapsack + Prim's MST).
- **Mock Interview** — text **and** voice, 4 interviewer personas, 5 rounds
  (a hand-rolled Python state machine, no LangChain/LangGraph).
- **Confidence Coach** — live eye-contact / posture scoring via MediaPipe plus
  speech metrics.
- **Placement Chat**, **Job Tracker**, and a **Community** feed.

### 🎮 Gamification

A 4-pillar **CampusIQ Score**, leaderboard, skill tree, badges, **Boss Battles**,
and a public, shareable **recruiter profile** at `/p/:studentId` (no login required).

### 👨‍🏫 Teacher

- Subjects and **per-subject enrollment / roster** (add students by username).
- Document upload (chunked + embedded for RAG).
- **AI quiz authoring + scheduling** — test-mode quizzes are proctored and feed CIE.
- Announcements and analytics.
- **Answer-similarity checker** (Hamming distance) for catching copied answers.
- **AI Auto-Grader** — upload a marking scheme + scanned answer sheets; Claude
  vision performs OCR + per-question grading; the teacher reviews/overrides; a
  pure grade engine rolls everything up to CIE/SEE, CO attainment, letter grades,
  SGPA, and CGPA.
- **Class Grades** dashboard + CO attainment per subject.

### 🛠️ Admin

- **CollegeGPT corpus** upload.
- **Knowledge Editor** — chunk-level CRUD with AI-mediated edit suggestions
  (word-diff review UI).
- User management and skill analytics.
- **Live notification delivery dashboard** (TCP-style retry/ACK; see below).

---

## Flagship subsystems

A few subsystems are the heart of the project and worth calling out.

### AI answer-sheet auto-grader

The largest subsystem. The pipeline runs as FastAPI `BackgroundTasks`:

1. Teacher creates an **exam** for a subject.
2. The uploaded **marking scheme** PDF is parsed into questions + course
   outcomes (text-first, with a **Claude-vision fallback** for scanned schemes).
3. Teacher reviews/confirms the scheme (grading is hard-gated until it's ready).
4. Scanned **answer sheets** are rasterized to page images (PyMuPDF).
5. **One fused Claude-vision call per student** does OCR + grading + USN/name
   detection, writing per-question grades and flagging low-confidence ones.
6. Detected students are **matched to the roster** (USN/name fuzzy match with an
   inlined Levenshtein — no new dependency).
7. A **pure, DB-free grade engine** (`grade_engine.py`) applies RVCE-style CIE/SEE
   pass gates, the 10-point grade table, and CO attainment → `SubjectGrade` →
   SGPA → CGPA. It's unit-tested against a written spec.

No Tesseract/OpenCV — rasterization is PyMuPDF and OCR is Claude vision. Answer-
sheet page images are served **only** through an authenticated, ownership-checked
route (never a public static mount), which is why the frontend has an
`AuthedImage` blob-fetching component.

### Coding platform + DSA curriculum + DSA Coach

The coding judge runs **entirely in the browser**: Monaco for editing and Pyodide
(WASM CPython, pinned) for executing submissions against test cases — no server-
side code execution. On top of the 5 in-app-judge problems sits a curated
**38-pattern, 376-problem DSA curriculum** (Core/Advanced tracks, per-pattern
progress); non-judge problems open on LeetCode. The **DSA Coach** is a Socratic
tutor that walks students up a hint ladder instead of handing out solutions.

### Proctored quizzes

Test-mode quizzes add a preflight (camera permission, MediaPipe face tracker, rules),
then a fullscreen run with a **server-anchored countdown** (clock-skew corrected),
a live face-presence badge, and anti-cheat monitoring (tab-switch/blur, fullscreen
exit, copy/paste, DevTools/print combos). **No camera images are ever stored** —
only event counters and a live face-presence signal; integrity rests on the server
(timer + single-attempt + availability window), not on client-side locks. On submit,
a test-mode attempt **feeds the subject's CIE**.

### RAG (Note Assistant + CollegeGPT)

Embeddings are generated locally with Sentence Transformers (`all-MiniLM-L6-v2`,
384-dim). Vector search uses **pgvector** in production and a **pure-Python cosine
fallback** for SQLite in local dev — so RAG works on the dev database without any
vector extension.

### Voice & confidence (Mock Interview, Confidence Coach)

ElevenLabs Scribe is the primary ASR + TTS path, with OpenAI Whisper as an opt-in
ASR fallback; absent both keys, the app falls back to the browser's native
`SpeechRecognition` / `speechSynthesis`. Eye-contact / posture / face-presence
scoring uses MediaPipe Tasks Vision (Face + Pose landmarkers), loaded lazily.

### TCP-style notification delivery

WebSocket notifications are persisted to the database even when no socket is
connected; an in-process retry loop re-pushes un-ACKed deliveries with exponential
backoff, and clients ACK over the socket. The admin dashboard visualizes delivery
state live. WS auth uses a query-param token (the handshake can't carry an
`Authorization` header).

### Classic algorithms, wired into real features

CampusIQ doubles as a Design-and-Analysis-of-Algorithms showcase — textbook
algorithms power real product surfaces, exposed under `/api/v1/algorithms`:

| Algorithm                         | Powers                                   |
| --------------------------------- | ---------------------------------------- |
| Dijkstra + Knapsack + Prim's MST  | Skill-Gap / Adaptive Learning path        |
| Backtracking + spread strategies  | Study Schedule planner                    |
| Hamming distance                  | Answer-similarity checker                 |
| Graph coloring                    | Quiz-slot scheduling                      |
| Inclusion–exclusion               | Student analytics                         |
| Huffman coding                    | Encoding demo                             |

The pure-logic services (Dijkstra, Knapsack, Prim's, Huffman, the schedulers, and
the grade engine) take primitives in and return primitives out — no database —
which keeps them unit-testable in isolation.

---

## Tech stack

### Frontend

- **React 19** + **TypeScript 6** + **Vite 8**
- **Tailwind CSS 3.4** (CSS-variable theming — `nebula` / `light` / `dark`)
- **Zustand 5** for state (auth, theme, notifications, quiz-generation), **React Router 7**
- **Framer Motion 12**, **Recharts 3**, **lucide-react**, **react-markdown + remark-gfm**, **Mermaid 11**
- **Monaco editor** + **Pyodide** (in-browser code editor + Python judge)
- **MediaPipe Tasks Vision** (proctoring + Confidence Coach)
- **GSAP** + **tsParticles** (marketing landing page)
- **vite-plugin-pwa** + **sharp** (installable PWA / icon generation — in progress)

### Backend

- **FastAPI 0.135** + **Uvicorn**, **SQLAlchemy 2** (sync) + **Alembic**, **Pydantic v2**
- **PyJWT** (HS256, 7-day tokens) + **bcrypt** for auth
- **PyMuPDF** (`fitz`) for PDF rasterization + text extraction
- **Sentence Transformers** (local embeddings) + **pgvector** (prod vector search)
- **SQLite** locally, **PostgreSQL 16 + pgvector** in production

### AI & speech

- **Anthropic Claude** — text and **vision/multimodal** (answer-sheet OCR + grading).
  Haiku 4.5 for all dev/test; Opus 4.6 reserved for the live demo.
- **ElevenLabs** (Scribe ASR + TTS, primary speech path)
- **OpenAI Whisper** (opt-in ASR fallback)

### Architecture notes (intentional constraints)

- **No Celery / RQ / worker queue** — everything async runs on FastAPI `BackgroundTasks`.
- **No LangChain / LangGraph** — the interview engine is a hand-rolled state machine.
- **No React Query / Redux** — Zustand + local component state only.
- Redis (`REDIS_URL`) is wired in config but intentionally unused.

---

## Repository layout

The git repository is the `campusiq/` directory. (The parent folder is a scratch
workspace for screenshots and media — it is **not** a git repo.)

```text
campusiq/
├── README.md                  # this file
├── CLAUDE.md                  # contributor/agent orientation (project-wide)
├── PHASES.md                  # the original 21-phase build narrative (partly historical)
├── DEMO.md                    # 10-minute demo runbook + pre-flight checklist
├── HOSTING.md                 # deploy guide (Render-era; see Deployment below)
├── plan_phase2.md             # DSA curriculum plan (Part A done; Chrome extension is Part B)
├── render.yaml                # Render Blueprint (alternate backend deploy path)
├── docker-compose.yml         # local prod-parity for the backend image
├── docs/screenshots/          # landing + login imagery
├── grading_mdfiles/           # local-only grading spec + RVCE handbook references (gitignored)
│
├── backend/                   # FastAPI app — see backend/CLAUDE.md
│   ├── app/
│   │   ├── main.py            # app factory, CORS, lifespan loops, /health, /audio mount
│   │   ├── core/              # config (Settings, model selection), database, security
│   │   ├── api/
│   │   │   ├── deps.py        # DbSession, get_current_user, require_role, claude_rate_limit
│   │   │   ├── router.py      # mounts every route module under /api/v1/<prefix>
│   │   │   └── routes/        # 25 endpoint modules (one per domain)
│   │   ├── models/            # SQLAlchemy models — 49 tables across 10 domain files
│   │   ├── schemas/           # Pydantic request/response shapes
│   │   ├── services/          # 60 service modules — business logic lives here
│   │   ├── tasks/ · utils/
│   ├── alembic/versions/      # 8 chained migrations (baseline → grading)
│   ├── scripts/               # seed_demo, reset_demo, import_curriculum, migrate_to_postgres
│   ├── tests/                 # pytest — 15 modules
│   ├── Dockerfile             # multi-stage python:3.12-slim; runs alembic then uvicorn
│   ├── requirements.txt · requirements-dev.txt
│   └── .env.example
│
└── frontend/                  # Vite SPA — see frontend/CLAUDE.md
    ├── src/
    │   ├── routes/AppRouter.tsx   # single routing source of truth
    │   ├── pages/                 # ~45 pages: student / teacher / admin / auth / marketing
    │   ├── components/            # ui / layout / chat / coding / dashboard / admin + AuthedImage
    │   ├── hooks/                 # theme, proctoring, confidence tracker, speech, media query
    │   ├── store/                 # Zustand stores (auth, notifications, quiz-generation)
    │   ├── api/client.ts          # one typed method per backend endpoint
    │   └── types/                 # response types mirroring backend schemas
    ├── vercel.json
    └── .env.example
```

---

## Getting started (local dev)

### Prerequisites

- **Python 3.12+** (a `backend/.venv` is used locally; CI and the Docker image pin 3.12)
- **Node.js 20+** and npm
- No database server required for dev — local development runs on SQLite.

### Backend (port 8000)

> ⚠️ **Always run the backend from inside `backend/`.** Pydantic Settings resolves
> the `.env` file relative to the process's working directory; launching from the
> repo root silently reads the wrong env and creates an empty SQLite DB. This is
> the single most common local-dev gotcha.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements-dev.txt                 # first time only
cp .env.example .env                                 # then fill in values

.venv/bin/python -m alembic upgrade head             # apply migrations
.venv/bin/python scripts/seed_demo.py                # seed the 4 demo accounts (optional)
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://127.0.0.1:8000/health` →
`{"status":"ok","service":"CampusIQ API","version":"0.1.0",...}`

### Frontend (port 5173)

```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm run dev
```

Open **http://localhost:5173** (use `localhost`, not `127.0.0.1` — Vite binds IPv6).

Useful frontend scripts: `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`.

---

## Environment variables

Secrets are never committed — copy each `.env.example` to `.env` and fill it in.

### Backend (`backend/.env`)

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | DB connection (defaults to local SQLite; Postgres in prod) |
| `JWT_SECRET_KEY` | JWT signing secret (**must** be overridden in prod) |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | HS256 / `10080` (7 days) |
| `ANTHROPIC_API_KEY` | Claude (text + vision); absent → AI features degrade gracefully |
| `ANTHROPIC_MODEL_DEV` / `ANTHROPIC_MODEL_PROD` | Haiku (dev) / Opus (demo) |
| `USE_PRODUCTION_MODEL` | `False` by default — flip to `True` for a live demo only |
| `CLAUDE_REQUESTS_PER_MINUTE` | Per-user rate limit on Claude routes (default `20`) |
| `ELEVENLABS_API_KEY` | Scribe ASR + TTS (optional; browser fallback if unset) |
| `OPENAI_API_KEY` | Whisper ASR fallback (optional) |
| `SEED_DSA_CURRICULUM` | Seed the 376-problem curriculum on first read (default `True`) |
| `AUDIO_RETENTION_DAYS` / `AUDIO_CLEANUP_INTERVAL_HOURS` | Voice-recording cleanup loop |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origins |
| `ENVIRONMENT` | `development` / `production` |

### Frontend (`frontend/.env`)

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Backend API base, e.g. `http://127.0.0.1:8000/api/v1` (baked at build time) |

---

## Testing & CI

- **Backend:** `pytest` from `backend/` — 15 test modules covering auth, dashboards,
  algorithms, schedules, chat modes, coding, enrollment, knowledge editor,
  notifications, rate limiting, quiz modes, the grade engine, grades/transcript,
  and the full grading flow (with Claude vision mocked). Tests build a file-backed
  SQLite DB via `create_all()` (no Alembic) and never hit a real AI API.

  ```bash
  cd backend && .venv/bin/python -m pytest
  ```

- **Frontend:** `vitest` + Testing Library (jsdom) — `npm test`. Heavy deps
  (Pyodide, Mermaid) are mocked.

- **CI:** GitHub Actions (`.github/workflows/ci.yml`). Backend runs `pytest` on
  Python 3.12 against SQLite; frontend runs **typecheck → lint → test → build**,
  all four of which must pass. CI does **not** deploy.

---

## Deployment

The platform is **live on Google Cloud Platform + Vercel**.

| Tier | Service | Detail |
| --- | --- | --- |
| **Frontend** | **Vercel** | https://campusiq-psi.vercel.app · SPA rewrites; `VITE_API_BASE_URL` baked at build time |
| **Backend** | **GCP Cloud Run** (`campusiq-backend`, region `asia-south1`) | Container from Artifact Registry; single always-on instance (`min=max=1`, no CPU throttling) so the in-process notification/WebSocket loop stays alive |
| **Database** | **GCP Cloud SQL** — PostgreSQL 16 (`campusiq-db`) | pgvector enabled; Cloud Run connects via the Cloud SQL socket connector |

The backend image runs `alembic upgrade head` on every boot, so migrations apply
on each deploy (keep them idempotent). The frontend and backend each deploy from
their own pipeline; CI does not deploy.

**Alternate / local paths also in the repo:**

- `render.yaml` — a Render Blueprint for the backend (an earlier hosting path;
  the live stack has since moved to GCP). [`HOSTING.md`](./HOSTING.md) documents
  this Render + Vercel + Supabase setup.
- `docker-compose.yml` — `docker compose up backend` builds and boots the
  production image locally for prod-parity checks (the frontend stays on
  `npm run dev` for HMR).

> **Note:** `HOSTING.md`, `DEMO.md`, and the `.env.example` files still reference
> the earlier Render + Supabase hosting. The current production database and
> backend run on GCP (Cloud SQL + Cloud Run); local development is unchanged
> (SQLite). Treat the table above as the source of truth for where the live app runs.

---

## AI cost controls

Every Claude call is protected by two independent layers, treated as a hard constraint:

1. **Model selection** — all four client entry points (`generate_completion`,
   `generate_completion_multiturn`, `stream_completion`, and the vision path
   `generate_completion_vision`) read `settings.active_anthropic_model`. The model
   is **Haiku 4.5** for all dev/test and only switches to **Opus 4.6** when
   `USE_PRODUCTION_MODEL=True` (the single live demo). Model strings are never
   hardcoded at a call site, and the client never raises — it degrades to a clean
   fallback when no key is configured.
2. **Per-user rate limit** — a token-bucket dependency (`claude_rate_limit`,
   default 20 req/min) guards every Claude-touching route (429 + `Retry-After`).
   The answer-sheet grader is additionally serialized per-exam so a batch upload
   makes one vision call at a time.

ElevenLabs and Whisper are similarly optional and metered; without keys the app
falls back to the browser's native speech APIs.

---

## Project documentation

| Doc | What it covers |
| --- | --- |
| [`CLAUDE.md`](./CLAUDE.md) | Project-wide contributor/agent orientation — run commands, locked decisions, cost rule, theming, git etiquette |
| [`backend/CLAUDE.md`](./backend/CLAUDE.md) | Backend conventions: the cwd gotcha, routes, models/migrations, auth, grading pipeline, services |
| [`frontend/CLAUDE.md`](./frontend/CLAUDE.md) | Frontend conventions: routing, state, theming rules, API client, components, proctoring hooks |
| [`PHASES.md`](./PHASES.md) | The original 21-phase build narrative (the status table is historical — the live code is the source of truth) |
| [`DEMO.md`](./DEMO.md) | 10-minute demo runbook + pre-flight checklist |
| [`HOSTING.md`](./HOSTING.md) | End-to-end deploy guide (Render-era; see [Deployment](#deployment) for the current GCP stack) |
| [`plan_phase2.md`](./plan_phase2.md) | DSA curriculum plan — Part A (curriculum + UI) is done; Part B (a LeetCode Chrome extension) is the remaining unbuilt piece |

> The repo is developed across multiple git worktrees (e.g. `main`,
> `claude/coding-learn-platform`, `claude/place-mode-student`), so `main` often
> carries in-flight work. Run `git status` / `git worktree list` before assuming a
> clean tree.

---

## At a glance

| | |
| --- | --- |
| Backend route modules | **25** (mounted under `/api/v1`) |
| Database tables | **49** across 10 domain model files |
| Backend services | **60** |
| Alembic migrations | **8** (chained baseline → grading) |
| Backend tests | **15** modules |
| Frontend pages | **~45** across student / teacher / admin / auth / marketing |
| Themes | 3 — `nebula` (default), `light`, `dark` |
| Demo accounts | 4 (1 student, 2 teachers, 1 admin) |

---

CampusIQ is an academic project. Treat the live code and `git log` as the
authoritative source of truth; planning docs may lag behind what's shipped.
