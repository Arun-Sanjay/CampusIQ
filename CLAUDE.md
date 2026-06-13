# CampusIQ — Claude orientation

CampusIQ is a monorepo for an AI-assisted academic + placement-prep platform built for engineering students at RVCE. Single SPA frontend, single FastAPI backend, role-based experiences for **student / teacher / admin**. It started as a 21-phase build and has since grown past it (coding platform, DSA coach + curriculum, knowledge editor, per-subject enrollment, usernames). This file is the orientation you need before touching code; deeper rules live in `frontend/CLAUDE.md` and `backend/CLAUDE.md`.

## Canonical docs (read these before doing real work)

- **The live code + `git log` are the real source of truth.** The product is well past the original plan; when a planning doc and the code disagree, trust the code.
- `PHASES.md` — the 21-phase build narrative with per-phase file lists and verification notes. Good for the algorithm-to-syllabus story, but the **status table at the top is stale**: phases 20 (Voice Interview + Confidence Coach) and 21 (Boss Battles + TCP notifications + public recruiter profile) are marked "Pending" yet are fully built and shipped, and the doc has **no record at all** of the post-phase-21 work (coding platform, DSA coach, DSA curriculum, knowledge editor, enrollment + usernames, spread-schedule). Don't trust its table or its "5 themes" Phase-1 text.
- `DEMO.md` — the 10-minute demo runbook + pre-flight checklist, rewritten for the **hosted Render + Vercel + Supabase** stack. Treat it as the spec for the user-visible product surface and the canonical demo-account list.
- `HOSTING.md` — end-to-end deploy guide (Render backend, Vercel frontend, Supabase Postgres, keep-warm). See "Deployment" below.
- `plan_phase2.md` — DSA Coach "Phase 2" plan. **Part A (38-pattern / 376-problem curriculum + pattern UI) is DONE and verified; Part B (a Manifest V3 "Claude-in-Chrome"-style LeetCode extension) is the only unbuilt piece.**
- `README.md` — outdated scaffold-era overview ("scaffold-only, no auth/models/workflows"). **Entirely false today** — useful only for the high-level role framing.

## Stack at a glance

- **Frontend:** React 19.2, Vite 8, TypeScript 6, Tailwind 3.4, Zustand 5, React Router 7.13, Framer Motion 12, Recharts 3, lucide-react 1.7, react-markdown 10 + remark-gfm 4, Mermaid 11. Coding platform adds **`@monaco-editor/react` (code editor) + `pyodide` (in-browser Python judge)**; Confidence Coach adds **`@mediapipe/tasks-vision`**; the landing page uses `gsap` + `@tsparticles/*`.
- **Backend:** FastAPI 0.135, SQLAlchemy 2 (sync), Alembic, Pydantic v2, PyJWT + bcrypt. SQLite locally, Supabase Postgres + pgvector in prod.
- **AI / speech:** Anthropic SDK (Claude). **ElevenLabs is the primary speech path — Scribe (`scribe_v1`) ASR + TTS;** OpenAI Whisper is an opt-in ASR fallback. Sentence Transformers (`all-MiniLM-L6-v2`, 384-dim) for embeddings.
- **Python:** local venv is **3.14** (`backend/.venv`); the Docker image and CI pin **3.12**. Don't assume they match.
- **Infra:** GitHub Actions CI (`.github/workflows/ci.yml`). **Backend deploys to Render (Docker), frontend to Vercel, DB on Supabase** — see "Deployment".

## Layout

```
campusiq/                         # ← the git repo (parent dir is NOT a repo; see below)
├── PHASES.md, DEMO.md, HOSTING.md, plan_phase2.md, README.md, image-prompts.md
├── render.yaml                   # Render Blueprint (backend web service)
├── docker-compose.yml            # real now — defines the `backend` service for local prod-parity
├── .github/workflows/ci.yml
├── docs/screenshots/             # landing + login images (no prose docs)
├── frontend/                     # Vite SPA — see frontend/CLAUDE.md
└── backend/                      # FastAPI app (+ Dockerfile) — see backend/CLAUDE.md
```

## Running locally

```bash
# Backend (port 8000) — MUST be run from backend/ (see backend/CLAUDE.md for the cwd gotcha)
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Frontend (port 5173)
cd frontend && npm run dev
```

Health: `curl http://127.0.0.1:8000/health`. Frontend is reached at **`http://localhost:5173`** (Vite binds IPv6 — `127.0.0.1:5173` may not resolve).

## Locked design decisions (do not relitigate)

- **No LangGraph / LangChain.** The mock interview is a hand-rolled Python state machine in `backend/app/services/mock_interview.py`.
- **No Celery / RQ / Dramatiq.** FastAPI `BackgroundTasks` for everything until something is actually too slow. `redis` and `celery` are in `requirements.txt` but nothing wires them.
- **Frontend-first.** UI was built with mock data first; backend wiring came later. When wiring a new feature, check the existing page's mock shape and match the API contract to it.
- **Sentence Transformers locally** for embeddings, with a **SQLite cosine fallback** (`backend/app/services/vector_search.py`) so RAG works on the dev DB without pgvector.

## Cost rule (treat as a hard constraint)

Two layers protect the AI budget:

1. **Model selection.** Every dev/test Claude call uses **Haiku 4.5** (`claude-haiku-4-5-20251001`); **Opus 4.6** (`claude-opus-4-6`) is reserved for the single live demo. The switch is `USE_PRODUCTION_MODEL` in `backend/.env`; the active model is read via `settings.active_anthropic_model` (`backend/app/core/config.py`). Default is `False` — leave it that way unless explicitly demoing. Never hardcode a model string at a call site.
2. **Per-user rate limit.** A token-bucket dependency (`claude_rate_limit`, default `CLAUDE_REQUESTS_PER_MINUTE=20`) guards every Claude-touching route (429 + `Retry-After`). See `backend/CLAUDE.md`.

ElevenLabs (Scribe ASR + TTS) and Whisper are similarly metered. Both are optional — without keys the app falls back to the browser's native `speechSynthesis` / `SpeechRecognition`. Don't burn the ElevenLabs starter quota during dev; the **text-mode** interview is the right path for iterating.

## Theming (only 3 themes exist)

`light`, `dark`, `nebula`. Nebula is the signature theme and the default for new visitors. The earlier `premium` / `aurora` / `luxury` themes were dropped — `frontend/src/hooks/useTheme.ts` rewrites those legacy values on load. Always style via the CSS variables in `frontend/src/index.css` (`--bg-*`, `--text-*`, `--border-*`, `--input-bg`, `--shadow-*`, `--gradient-accent`, glass/glow). Hardcoding hex breaks theme switching. (The marketing landing page is the one documented exception — see `frontend/CLAUDE.md`.)

## Feature map (what's actually wired today)

- **Learn Mode (student):** AI Note Assistant (RAG chat, streaming, citations, Explain/Diagram/Questions modes + Mermaid), CollegeGPT, Quizzes (AI-generated, adaptive, weak-areas), study Schedule planner (spread + backtracking strategies), Crash Mode, **Coding platform** (Monaco + Pyodide in-browser judge, 5 judge problems + the 38-pattern curriculum) with the **DSA Coach** (Socratic hint-ladder + LeetCode redirect).
- **Place Mode (student):** Resume Builder (AI coach, ATS score, GitHub import, print-to-PDF), Skill-Gap / Adaptive Learning Engine (Dijkstra + Knapsack + Prim's), Mock Interview (text **and** voice, 4 personas, 5 rounds), Confidence Coach (MediaPipe eye-contact/posture + speech metrics), Placement Chat, Job Tracker, Community.
- **Gamification:** 4-pillar CampusIQ score, leaderboard, skill tree, badges, Boss Battles, public recruiter profile at `/p/:studentId`.
- **Teacher:** subjects, **per-subject enrollment/roster**, documents, AI quiz authoring + scheduling, announcements, analytics, answer-similarity (Hamming) checker.
- **Admin:** CollegeGPT corpus upload, **Knowledge Editor** (chunk CRUD + AI-mediated edit suggestions), user management, skill analytics, **live TCP-style notification delivery dashboard**.

## Deployment

- **Backend → Render.** Web service `campusiq-backend` (Starter plan, Singapore), built from `backend/Dockerfile` (multi-stage `python:3.12-slim`) via the `render.yaml` Blueprint. On boot it runs **`alembic upgrade head` then `uvicorn`** (migrations apply on every deploy; keep them idempotent). Health check at `/health`, `autoDeploy: true`. Secrets are set in the Render dashboard (`sync: false`): `DATABASE_URL`, `JWT_SECRET_KEY`, `ANTHROPIC_API_KEY`, `SUPABASE_*`, `CORS_ALLOWED_ORIGINS`, optional `OPENAI_API_KEY` / `ELEVENLABS_API_KEY`.
- **Frontend → Vercel** (`frontend/vercel.json`, SPA rewrites). One env var: `VITE_API_BASE_URL=https://<render-service>.onrender.com/api/v1`.
- **DB → Supabase free tier** (Postgres + pgvector + Storage bucket `campusiq-documents`, project ref `zngdzrdselzflvfriznc`). Auto-pauses after ~7 days idle; an UptimeRobot ping on `/health` keeps both Render and Supabase warm.
- **Local prod-parity:** `docker compose up backend` (reads `backend/.env`, maps `8000:8000`). The frontend is intentionally not in compose — run it with `npm run dev`.
- CI does **not** deploy — Render and Vercel each deploy off their own GitHub integration on push to `main`.

## Git etiquette & worktrees

- **Never add a `Co-Authored-By: Claude` trailer** to commit messages on this repo (or any of Arun's repos). Standing instruction.
- **Never `git push` without explicit permission.** Remote is `https://github.com/Arun-Sanjay/CampusIQ.git`.
- Stage specific files (`git add path/to/file`), not `git add -A` — the **parent** folder holds many large screenshots and a hero `.mov`, and `main` often carries unrelated in-progress changes.
- **There are multiple active git worktrees** (run `git worktree list` to see the current set). As of this writing:
  - `campusiq/` → **`main`** (the primary worktree; this is where you usually are).
  - `campusiq-coding-learn/` → `claude/coding-learn-platform`.
  - `campusiq-place-mode-student/` → `claude/place-mode-student`.
- **Stay in your assigned worktree.** Before editing shared infrastructure (migrations, `requirements.txt`, `package.json`, CI, config), check the sibling worktrees with `git status` / `git log` so you don't collide with parallel work. `main` itself frequently has uncommitted work in flight — run `git status` before assuming a clean tree.

## Where the project root sits

The git repo is `/Users/arunsanjay/Documents/Projects/CampusIQ/campusiq/` (and its worktrees, listed above). The parent `/Users/arunsanjay/Documents/Projects/CampusIQ/` is **not** a git repo — it's the user's working folder holding screenshots, hero video sources, and scratch demo assets. Don't `git init` there or stage files from it.

## Auto-memory location

Project memory lives at `/Users/arunsanjay/.claude/projects/-Users-arunsanjay-Documents-Projects-CampusIQ/memory/`. Read `MEMORY.md` there for user-curated context that persists across sessions. The path encoding uses the parent directory name (`-CampusIQ`), not the inner `campusiq/` repo.
