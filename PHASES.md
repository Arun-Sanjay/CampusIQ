# CampusIQ — Build Phases

The full plan to take CampusIQ from scaffold to final product, broken into 18 phases.
Each phase is small enough to complete in a single session and produces something testable.

---

## Design Decisions Locked In

- **No LangGraph** — Python state machine for the interview simulator (simpler, easier to debug)
- **Haiku for all dev/testing** — Opus only for the single final demo
- **ElevenLabs voices** — different voice per interview round, text mode during dev
- **No Celery/Redis in early phases** — FastAPI BackgroundTasks until needed
- **Sentence Transformers locally** for embeddings (or API fallback if too slow)
- **SQLite for Phases 4-7**, switch to Supabase PostgreSQL at Phase 8 (pgvector needed)
- **Adaptive Learning Engine** (Dijkstra + Knapsack + dynamic weights) = research paper core
- **5-Round Voice Interview Simulator** (Whisper + Claude + ElevenLabs) = demo showstopper
- **Frontend-first approach** — all UI built with mock data before any backend wiring

---

## Status Summary

| Phase | Status | What |
|-------|--------|------|
| 1 | ✅ Done | Design system + layout + auth pages |
| 2 | ✅ Done | All Learn Mode page UIs (mock data) |
| 3 | ✅ Done | All Place Mode + Profile + remaining UIs (mock data) |
| 4 | ✅ Done | Database schema (36 tables) + Supabase + CORS + config |
| 5 | ✅ Done | JWT auth (signup/login/me) + role guards + frontend wiring |
| 6 | ✅ Done | Subject + document CRUD wiring (upload, list, delete, filter, E2E verified) |
| 7 | ✅ Done | Document processing + Huffman (F19) — extract, chunk, compress, summarize, background tasks |
| 8 | ✅ Done | Embeddings + pgvector RAG foundation (semantic search verified, 5/5 queries) |
| 9 | ✅ Done | AI Note Assistant backend (RAG chat, streaming, citations, session persistence) |
| 10 | ✅ Done | CollegeGPT backend (admin upload, RAG over college_document_chunks, citations) |
| 11 | ✅ Done | Quiz Engine backend (AI generation, taking flow, adaptive difficulty, weak areas) |
| 12 | ✅ Done | Dashboard + XP + Task Feed (heap priority queue, level recurrence, academic pillar) |
| 13 | ✅ Done | Announcements + Teacher Analytics (V1 / Learn Mode complete) |
| 14 | ✅ Done | Resume Builder (AI chat coach, ATS scoring, GitHub import, print-to-PDF) |
| 15 | ✅ Done | **Adaptive Learning Engine** ★ RESEARCH CORE (Dijkstra + Knapsack + Prim's + dynamic edge rescaling) |
| 16 | ✅ Done | Mock Interview text mode (Python state machine, 4 personas, 5 rounds, per-turn scoring, debrief) |
| 17 | ✅ Done | Placement Chatbot + Job Tracker (Kanban + fit scores) + Community (AI fallback) |
| 18 | ✅ Done | Full gamification — 4-pillar composed score + leaderboard + skill tree + profile + badges |
| 19 | ✅ Done | Algorithm features (Hamming similarity, inclusion-exclusion, graph coloring, branch-and-bound schedule) — 4 backend services, 4 endpoints, 4 fully-wired pages, browser E2E verified |
| 20 | ⏳ Pending | **Voice Interview + Confidence Coach** (demo showstopper) |
| 21 | ⏳ Pending | Boss Battles + TCP notifications + final polish |

> **Note:** Phases 1-3 covered the entire frontend UI prototype. Phases 4-21 handle backend wiring and feature implementation. The numbering shifted from the original 18-phase plan because Phase 1 was split into 3 frontend phases.

---

## Phase 1 — Design System + Layout + Auth Pages ✅

**Complexity:** Low-Medium

**What was built:**
- Tailwind config with 5 themes (light, dark, premium violet, aurora, luxury gold)
- CSS variables for theming, custom font scale, shadows, border radius
- 9 reusable UI components: Button, Input, TextArea, Select, Card, Badge, Avatar, Modal, ProgressBar
- Layout components: Sidebar (collapsible, role-based nav), TopBar (theme toggle, score, streak), AppLayout
- Dashboard components: StatCard, ScoreRing, TaskFeed, ActivityFeed
- Chat components: ChatMessage, ChatInput, ChatLayout
- Framer Motion page transitions and stagger animations
- Premium effects: glassmorphism, gradient mesh background, noise texture, glow borders
- Auth pages: Landing, Login, Signup (with role selection)
- Theme system with persistence (Zustand + localStorage)

**Verification:** All 5 themes render correctly. Theme cycles via top-bar button. Auth pages navigate to dashboards.

---

## Phase 2 — Learn Mode Page UIs (Mock Data) ✅

**Complexity:** Medium

**What was built:**

**Student pages (5):**
- AI Note Assistant — chat with subject sidebar, source citations, suggested questions
- CollegeGPT — chat with college handbook answers, info banner
- Quiz Engine — 3 tabs (Available/History/Weak Areas), quiz cards with difficulty badges
- Doubt Community — search + tag filters, doubt cards with upvotes/answers
- Study Schedule — weekly calendar grid with colored subject blocks

**Teacher pages (5):**
- Dashboard — stat cards, quick actions, recent uploads
- My Subjects — subject card grid
- Documents — drag-drop upload, document table with Huffman compression stats
- Quiz Management — 3 tabs, AI generated badges, review/publish flow
- Class Performance — analytics, weakest topics with color-coded bars, student table

**Admin pages (2):**
- Dashboard — platform stats, user breakdown, recent activity, health metrics
- College Documents — upload zone, category filter, storage savings card

**Verification:** All pages render in all 5 themes. Mock data realistic. Animations smooth.

---

## Phase 3 — Place Mode + Profile + Remaining UIs (Mock Data) ✅

**Complexity:** Medium-High

**What was built:**

**Student Place Mode (7 pages):**
- Resume Builder — split layout: AI chat + live resume preview, template tabs, ATS score, GitHub import
- Skill Gap Analyzer — company/role selectors, gap score gauge, skill graph (Dijkstra path), Knapsack results table
- Mock Interview — 3-view flow (setup → interview → debrief), 4 personas, 6 companies, 5-round stepper, full debrief
- Confidence Coach — video record area, 6 metric cards, growth timeline, drill recommendations
- Job Tracker — 5-column Kanban with fit score badges
- Placement Chat — chat with profile context panel
- Crash Mode — urgent countdown, optimized study plan, quick actions

**Profile (3 pages):**
- Skill Tree — 6 domain cards with skill node pills
- Leaderboard — 3 tabs, top-3 podium, ranked table with tier badges
- My Profile — score breakdown, badges grid, skills, share URL

**Teacher (3 pages):**
- Announcements — compose form + posted list
- Student Details — searchable table + selected student detail card
- Similarity Checker — Hamming distance flagged pairs

**Admin (2 pages):**
- Skill Analytics — inclusion-exclusion filter builder + CSS Venn diagram
- Notification Status — TCP-style delivery table

**Total Phase 1-3:** 35 pages built with mock data, all themes working, full interactive prototype

---

## Phase 4 — Database Schema + Backend Foundation

**Complexity:** Low

**Goal:** Expand the database from 5 tables to the full ~25 table schema. Add CORS middleware, proper config.

**Files to create/modify:**
- `backend/app/models/user.py` — Add `college_id`, `last_login`; expand profiles
- `backend/app/models/content.py` — NEW: colleges, document_chunks, college_documents
- `backend/app/models/chat.py` — NEW: chat_sessions, chat_messages
- `backend/app/models/quiz.py` — NEW: quizzes, questions, quiz_attempts
- `backend/app/models/community.py` — NEW: doubts, doubt_answers
- `backend/app/models/placement.py` — NEW: resumes, interviews, jobs
- `backend/app/models/gamification.py` — NEW: xp_events, badges, scores, challenges
- `backend/app/models/algorithm.py` — NEW: skill_graph_edges, notifications, schedules
- `backend/alembic/versions/` — NEW migration
- `backend/app/main.py` — Add CORSMiddleware
- `backend/app/core/config.py` — Add all env vars

**Verification:** `alembic upgrade head` works. FastAPI starts. `/health` returns OK with CORS headers.

---

## Phase 5 — Authentication System

**Complexity:** Low-Medium

**Goal:** JWT auth with bcrypt, role-based access, frontend wired up.

**Files to create:**
- `backend/app/core/security.py` — JWT decode/verify, password hashing, get_current_user
- `backend/app/schemas/auth.py` — LoginRequest, SignupRequest, TokenResponse
- `backend/app/services/auth.py` — signup, login, get_current_user
- `backend/app/api/routes/auth.py` — POST /signup, /login, GET /me
- `backend/app/api/deps.py` — Reusable dependencies (require_role)
- `frontend/src/api/client.js` — Add auth token header
- `frontend/src/store/authStore.js` — Zustand auth store
- Wire up LoginPage and SignupPage to real API
- Add protected route wrapper

**Verification:** Signup → login → JWT returned → access /me → rejected without token. Frontend forms work end-to-end.

---

## Phase 6 — Subject & Document CRUD

**Complexity:** Medium

**Goal:** Teachers create subjects, upload documents to local storage, full CRUD.

**Files to create:**
- `backend/app/schemas/subject.py`, `backend/app/schemas/document.py`
- `backend/app/services/subject.py` — CRUD (teacher-scoped)
- `backend/app/services/document.py` — Upload, save metadata, list
- `backend/app/api/routes/subjects.py` — POST/GET /subjects
- `backend/app/api/routes/documents.py` — POST /upload, GET /documents
- Wire up Teacher Subjects + Documents pages

**Verification:** Teacher creates subject → uploads PDF → sees it listed. Student blocked from teacher routes.

---

## Phase 7 — Document Processing + Huffman Compression (F19)

**Complexity:** Medium

**Goal:** Extract text from PDFs, chunk into 500-word segments, Huffman compress.

**Files to create:**
- `backend/app/services/document_processor.py` — PyMuPDF text extraction, chunking
- `backend/app/services/huffman.py` — Huffman tree, encode/decode, compression ratio
- Update `document_chunks` table with `compressed_text`, `codebook`, `compression_ratio` columns
- Update document service to trigger processing pipeline
- Show processing status + compression stats on Teacher Documents page

**DAA Concept:** Huffman trees and codes, greedy algorithm (Unit IV)

**Verification:** Upload PDF → status becomes "ready" → compression stats visible (40-60% ratio).

---

## Phase 8 — Embeddings & pgvector RAG Foundation

**Complexity:** Medium-High

**Goal:** Generate vector embeddings, store in pgvector, build similarity search.

**Files to create:**
- `backend/app/services/embeddings.py` — Sentence Transformers loading + text-to-embedding
- `backend/app/services/vector_search.py` — pgvector cosine similarity, top-K retrieval with Huffman decompression
- Switch to Supabase PostgreSQL, enable pgvector extension
- New migration: add `embedding vector(384)` columns
- Document processor generates and stores embeddings

**Verification:** Upload document → chunks embedded → query returns top 5 similar chunks with cosine scores.

---

## Phase 9 — AI Note Assistant Backend (F2) ✅

**Complexity:** Medium-High

**What was built:**
- `backend/app/services/chat.py` — Session and message persistence (list/get/create/delete sessions, add messages, auto-titling from first user message)
- `backend/app/services/ai_chat.py` — RAG retrieval (top-K=5 chunks via vector_search) + Claude streaming with source citation capture, persists assistant message + citations on completion
- `backend/app/services/claude_client.py` — Added `stream_completion()` generator with graceful fallback when `ANTHROPIC_API_KEY` is unset
- `backend/app/schemas/chat.py` — `ChatTypeLiteral`, `SourceCitation`, `ChatMessageResponse`, `ChatSessionResponse`, `ChatSessionWithMessages`, request schemas
- `backend/app/api/routes/chat.py` — `GET/POST/DELETE /chat/sessions`, `GET /chat/sessions/{id}`, `POST /chat/sessions/{id}/messages` (streaming via `StreamingResponse`), blocking variant for tests
- `backend/app/services/subject.py` — Renamed `list_subjects_for_teacher` → `list_subjects_for_user` so students get read-only access to subject list (teacher sees own only)
- `frontend/src/types/chat.ts` — Full TS type set for sessions/messages/citations
- `frontend/src/api/client.ts` — Added `chatApi` with `streamMessage()` using `fetch` + `response.body.getReader()` + `TextDecoder`
- `frontend/src/pages/student/NoteAssistantPage.tsx` — Rewritten to use real backend: loads subjects, finds-or-creates session per subject, optimistic UI + streaming chunks, refreshes from server post-stream to pick up persisted citations, AbortController cancels in-flight stream when switching subjects, "New chat" button per subject

**Verification:** Backend service E2E proved RAG retrieval (sim=0.860 on algorithms.txt chunk 0), streaming chunks delivered, persistence + auto-titling, cross-user isolation (403), session deletion. Browser E2E: signed up student `student.phase9@example.com`, navigated to `/student/notes`, verified subjects loaded, sent "Explain how Huffman coding works step by step.", saw user message render optimistically + streamed assistant fallback ("[AI is not configured...]"), session persisted across page reload, switching subjects auto-creates a new session, frontend typecheck + vite build clean.

---

## Phase 10 — CollegeGPT Backend (F5) ✅

**Complexity:** Low-Medium

**What was built:**
- `backend/app/schemas/college_document.py` — `CollegeDocumentResponse`, `CollegeDocumentChunkPreview`, category literal
- `backend/app/services/college_document.py` — Admin-only upload + CRUD writing to the `college_documents` table
- `backend/app/services/college_document_processor.py` — Background processing pipeline (extract → chunk → Huffman → embed → store in `college_document_chunks`)
- `backend/app/services/vector_search.py` — Added `search_college_chunks()` + `CollegeSearchHit` dataclass
- `backend/app/services/ai_chat.py` — Dispatches retrieval by `session.chat_type`. Added `COLLEGE_GPT_SYSTEM` prompt, `_format_college_chunks_as_context()`, `_citations_from_college_hits()`. Note Assistant and CollegeGPT now share the streaming pipeline.
- `backend/app/api/routes/college_documents.py` — `GET /college-documents/`, `POST /upload` (admin), `GET /{id}`, `GET /{id}/chunks`, `POST /{id}/reprocess` (admin), `DELETE /{id}` (admin)
- `backend/app/api/router.py` + `routes/__init__.py` + `services/__init__.py` — Registered new module
- `backend/app/models/content.py` — Made `college_documents.college_id` nullable for v1 single-tenant; matching Supabase migration applied
- `backend/app/core/database.py` — **Critical fix:** registered pgvector's psycopg2 type adapter on every new SQLAlchemy connection. Without it, vector parameter binding silently degraded to text and `<=>` returned wrong distances.
- **Schema fix:** dropped IVFFlat indexes on both `document_chunks.embedding` and `college_document_chunks.embedding`, replaced with HNSW. IVFFlat returns 0 hits on small tables because the row sits in an unprobed cluster cell — HNSW works from row 1 and is the modern pgvector recommendation.
- `frontend/src/types/content.ts` — Added `CollegeDocument`, `CollegeDocumentCategory`, `UploadCollegeDocumentOptions`
- `frontend/src/api/client.ts` — Added `collegeDocumentsApi` (list, get, upload via FormData, reprocess, delete)
- `frontend/src/pages/admin/CollegeDocsPage.tsx` — Real admin dashboard: category-tagged upload, filterable table with status badges, processing poller, Huffman compression totals, reprocess + delete actions
- `frontend/src/pages/student/CollegeGPTPage.tsx` — Real chat UI: finds-or-creates a `college_gpt` session, streams responses, refreshes citations from server post-stream, "New chat" button

**Verification:** Browser E2E:
1. Signed up admin `admin.phase10@example.com`, uploaded `RVCE Student Handbook 2026` text → background pipeline extracted, chunked, Huffman-compressed (40.1% savings), embedded (384-dim) → status `ready`.
2. Signed in as student, navigated to `/student/college-gpt`, asked *"What is the minimum attendance requirement for laboratory sessions? Are there any medical exemptions?"*
3. Streaming response from Haiku 4.5 returned the correct 85% rule + medical exemption details, fully grounded in the handbook content.
4. Citation persisted with `similarity=0.8606`: `HANDBOOK · RVCE Student Handbook 2026 · chunk 1`
5. Frontend typecheck + vite build clean. Zero console errors.

**Bonus:** The pgvector + HNSW fix unblocks Phase 9 RAG citations too — any future chat session against a processed subject document will now return real grounded answers.

---

## Phase 11 — Quiz Engine Backend (F3) ✅

**Complexity:** Medium-High

**What was built:**

**Backend:**
- `backend/app/schemas/quiz.py` — Full schema set: `QuestionStudentView` / `QuestionTeacherView` (answers hidden vs full), `QuizResponse`, `QuizForStudent`, `QuizForTeacher`, `QuizGenerateRequest`, `QuizUpdate`, `QuizAttemptCreate`, `GradedAnswer`, `QuizAttemptResponse`, `AttemptHistoryRow`, `WeakAreaResponse`
- `backend/app/services/quiz_generator.py` — Claude Haiku JSON quiz generation grounded in document chunks. Strict prompt rules, markdown-fence stripping, tolerant parser that snaps mismatched correct answers to the closest option, hard cap at 20 questions per call. Returns a draft `Quiz` (`is_published=False`, `is_ai_generated=True`).
- `backend/app/services/quiz.py` — CRUD + grading + diagnostics:
    - `list_quizzes()` — role-scoped (students see only published, teachers see their own, admins see all)
    - `get_quiz_for_student()` returns `QuestionStudentView` (no answers leaked)
    - `get_quiz_for_teacher()` returns `QuestionTeacherView` (full record)
    - `update_quiz()` + `delete_quiz()` (teacher-owned)
    - `submit_attempt()` — grades MCQ + short answer, builds per-question `GradedAnswer`s, stores the answer bit vector for the Phase 19 Hamming similarity checker, returns inline weak-topic detection and the next adaptive difficulty
    - `_next_difficulty_recommendation()` — **DAA Unit IV greedy** — looks at the last 3 attempts on the same subject; if avg ≥ 80% promote, if avg ≤ 50% demote, else stay
    - `compute_weak_areas()` — **DMS Unit II boolean threshold** — for each topic with ≥ 2 attempts, flag as weak iff correctness < 60%
- `backend/app/api/routes/quizzes.py` — Replaced the placeholder with the full route set: `GET /`, `GET /{id}`, `POST /generate` (teacher), `PATCH /{id}` (teacher), `POST /{id}/publish` (teacher), `DELETE /{id}` (teacher), `POST /{id}/attempts` (student), `GET /attempts/me`, `GET /attempts/me/weak-areas`. Attempts routes are mounted before `/{quiz_id}` so the path doesn't shadow them.
- `backend/app/services/__init__.py` + `backend/app/schemas/__init__.py` — exported new modules

**Frontend:**
- `frontend/src/types/quiz.ts` — Mirror of all quiz schemas (`Difficulty`, `QuestionStudentView`, `QuizSummary`, `QuizForStudent`, `QuizForTeacher`, `QuizAttemptResponse`, `AttemptHistoryRow`, `WeakAreaResponse`, etc.)
- `frontend/src/api/client.ts` — Added `quizzesApi` (list, getAsStudent, getAsTeacher, generate, update, publish, delete, submitAttempt, myAttempts, myWeakAreas)
- `frontend/src/pages/teacher/QuizManagementPage.tsx` — Real teacher dashboard: pending/published/drafts tabs with counts, "Generate Quiz" modal pulling subject + ready document selectors, full review modal with per-question correct-answer highlighting + explanations, publish toggle, delete, error banner, polling-friendly refresh
- `frontend/src/pages/student/QuizTakingPage.tsx` — Net-new page: one-question-at-a-time flow with progress bar, dot navigator, timer, optimistic answer selection, sessionStorage hand-off to result page, abort-safe submit
- `frontend/src/pages/student/QuizResultPage.tsx` — Net-new page: hero score card with adaptive next-difficulty hint, per-topic breakdown with red/green progress bars, full question-by-question review with correct/wrong markers + explanations, weak-topic list
- `frontend/src/pages/student/QuizListPage.tsx` — Replaced mock data with real API: Available tab launches `QuizTakingPage`, History tab shows real attempts, Weak Areas tab shows server-computed boolean-threshold weak topics
- `frontend/src/routes/AppRouter.tsx` — Added `/student/quizzes/:quizId/take` and `/student/quizzes/:quizId/result/:attemptId`

**Verification — full browser E2E:**
1. Signed up `teacher.phase11@example.com`, created subject `P11DAA — Phase 11 — DAA Quiz Demo`, uploaded a 3 KB Huffman lecture text → background pipeline processed it (1 chunk, 41% Huffman savings, summary written)
2. Opened `/teacher/quizzes`, clicked **Generate Quiz**, picked subject + medium difficulty + 5 questions → Haiku 4.5 returned a clean JSON quiz **"Huffman Coding Fundamentals"** with 5 high-quality questions covering complexity, prefix-code property, algorithm steps, optimality, and compression ratio. Each question has a topic label and varied per-question difficulty.
3. Opened the review modal, verified all 5 question/answer/explanation triples, clicked **Publish to students** → quiz went `is_published=true`
4. Switched to student account, navigated `/student/quizzes` → quiz visible in Available tab → Start Quiz → took the quiz selecting all correct answers → submit → result page rendered:
    - **100% score**, 5/5 correct, 1m 13s
    - **Next recommended difficulty: hard** (greedy promote)
    - Per-topic breakdown all 100%
    - Full question review with explanations
5. Submitted a second deliberately-wrong attempt via API → 0% score, **next recommended difficulty: easy** (greedy demote), all 5 topics flagged in `weak_topics`
6. Verified `/quizzes/attempts/me` shows both attempts with correct scores/times
7. Verified `/quizzes/attempts/me/weak-areas` returns 5 topics @ 50% correctness (1 right + 1 wrong each, 2 attempts ≥ threshold, score < 60% threshold) with personalized study suggestions
8. History and Weak Areas tabs in the UI render the same data
9. Frontend typecheck + vite build clean (644 KB JS / 184 KB gzip). Zero console errors.

**DAA / DMS concepts used:**
- Greedy adaptive difficulty selection (DAA Unit IV)
- Boolean threshold weak-topic detection (DMS Unit II)
- Hamming-ready answer bit vectors stored per attempt for the Phase 19 similarity checker

---

## Phase 12 — Student Dashboard + XP + Smart Task Feed (F13, F16, F20) ✅

**Complexity:** Medium

**What was built:**

**Backend:**
- `backend/app/services/xp.py` — XP economy + level math:
    - **DMS Unit I recurrence relation** for level thresholds: T(L) = T(L-1) + 100·L → closed form T(L) = 50·L·(L-1). `level_for_xp()` inverts via the quadratic formula. `xp_progress_to_next_level()` returns the (xp-into-level, current-floor, next-threshold) triple.
    - Streak engine: `update_streak()` checks `last_active_date` and increments / resets on the day boundary; `streak_multiplier()` grows linearly capped at ×1.5 (1.0 + 0.05 × min(streak, 10)).
    - `award_xp()` persists an `XPEvent`, applies streak multiplier, updates `StudentProfile.xp_total` and `current_level`, returns an `AwardedXP` dataclass with a `leveled_up` flag.
    - `award_xp_for_quiz_attempt()` scales XP by `score_fraction × difficulty_multiplier × streak_multiplier`, with a 0.2 floor so even failed attempts give a small reward.
- `backend/app/services/campus_iq_score.py` — academic pillar weighted average of the last 10 attempts (easy×0.7, medium×1.0, hard×1.3). `recompute_score()` upserts the row in `campus_iq_scores`. The other 3 pillars stay at 0 until Phase 18.
- `backend/app/services/task_feed.py` — **DAA Unit III heap-based priority queue**:
    - Sources tasks from 4 signals: unattempted published quizzes, failed quizzes (best score < 60% → retake), weak topics (≥ 2 attempts < 60%), daily-login bonus.
    - Each task scored by `urgency + impact`; the worse you scored on a topic the more urgent the review task.
    - Pushes onto a `heapq` min-heap with negated scores so the largest pops first; `_pop_top_k()` returns the top 6.
- `backend/app/services/dashboard.py` — aggregator that bundles XP progress, score breakdown, quiz stats, the heap-built task feed, and the last 8 XP events into a single `DashboardResponse`.
- `backend/app/schemas/dashboard.py` — `XPProgress`, `CampusIQScoreBreakdown`, `DashboardStats`, `TaskItemResponse`, `ActivityItem`, `DashboardResponse`.
- `backend/app/api/routes/dashboard.py` — `GET /dashboard/me` (student-only).
- `backend/app/services/quiz.py` — `submit_attempt()` now flushes the attempt, then calls `xp.award_xp_for_quiz_attempt()` and `campus_iq_score.recompute_score()` before committing — XP and score are updated atomically with the attempt.
- Registered new module in router, schemas, services exports.

**Frontend:**
- `frontend/src/types/dashboard.ts` — Mirror of all dashboard schemas.
- `frontend/src/api/client.ts` — `dashboardApi.me()`.
- `frontend/src/pages/student/DashboardPage.tsx` — Replaced mock data with the real API:
    - Loading + error states.
    - Stat cards: CampusIQ Score, Total XP, Quizzes Done, Avg Score (all real numbers).
    - 4-pillar breakdown card.
    - Heap-based task feed where each task is wrapped in a clickable div that routes to its `action_url` (quiz take page, etc.) when clicked.
    - Level XP bar showing `xp_into_level / next_level_threshold`.
    - Right sidebar: Recent Activity (XP events with relative timestamps), Quick Stats (attempts/passed/streak/level).
    - Streak day counter + XP multiplier badge in the header.

**Verification — full browser E2E:**
1. Signed up `student.phase12@example.com`, navigated to `/student` → fresh dashboard rendered with all zeros, level 1, 0/100 XP, the published Phase 11 quiz appearing as the **urgent** top task in the heap, plus a **low** daily-login task.
2. Submitted a 100% attempt on the Phase 11 quiz → backend hooks fired:
    - Attempt persisted
    - **47 XP awarded** (30 base × 1.5 medium × 1.0 score × 1.05 streak)
    - Streak incremented to 1, multiplier to ×1.05
    - Academic pillar recomputed to 100%
    - CampusIQ score total = 100
    - XP event written, surfaced in the activity feed
3. Reloaded `/student` → dashboard rendered fully reactive: "1 day streak ×1.05 XP multiplier", CampusIQ Score 100, 47/100 XP bar, "Completed a quiz (+47 XP) just now" in activity, task feed dropped the quiz (now attempted) and only showed daily login.
4. Submitted a deliberately failing second attempt → score recomputed to 50, XP bumped to 56 (9 more from the floor), 6 weak-area tasks promoted to **high** priority and dominating the task feed.
5. Frontend typecheck + vite build clean (645 KB JS / 184 KB gzip). Zero console errors throughout.

**DAA / DMS concepts used:**
- DAA Unit III — heap data structure / priority queue (`heapq` for the smart task feed)
- DMS Unit I — recurrence relation T(L) = T(L-1) + 100·L for XP-to-level mapping

---

## Phase 13 — Announcements + Teacher Analytics ✅

**Complexity:** Low-Medium

**What was built:**

**Backend:**
- `backend/app/schemas/announcement.py` — `AnnouncementCreate`, `AnnouncementUpdate`, `AnnouncementResponse` (with author + subject denormalized for the list view).
- `backend/app/services/announcement.py` — Role-aware CRUD:
    - Teachers post per-subject (or all-broadcast) announcements; admins post college-wide ones too.
    - Students see all-broadcasts + their college's announcements + any subject announcement.
    - Teacher edit/delete is restricted to the original author.
- `backend/app/schemas/analytics.py` — `AnalyticsHeadline`, `WeakTopicRow`, `ScoreBucket`, `StudentPerformanceRow`, `ClassAnalytics`.
- `backend/app/services/analytics.py` — `get_class_analytics()` aggregates everything from the teacher's quizzes:
    - Headline numbers: class average, completion rate (distinct attempts / (active students × published quizzes)), most-missed topic, active student count.
    - Weakest topic rows (boolean threshold < 60% with ≥ 2 attempts each, sorted by score, top 8).
    - Score distribution histogram across 5 buckets (0-19 / 20-39 / 40-59 / 60-79 / 80-100).
    - Per-student performance rows with quiz count, avg score, last attempt date, **trend** (compares latter half avg vs former half), and per-student weakest topic.
- `backend/app/api/routes/announcements.py` — `GET /announcements/` (visible to current user, with `subject_id`/`only_mine` filters), `POST /` (teacher/admin), `PATCH /{id}`, `DELETE /{id}`.
- `backend/app/api/routes/analytics.py` — Replaced the placeholder with `GET /analytics/class?subject_id=…` (teacher/admin only).
- `backend/app/services/dashboard.py` + `schemas/dashboard.py` — Added `announcements: list[AnnouncementResponse]` to the `DashboardResponse` (top 5 visible to the student).
- Registered routes + services in router/__init__.py and services/__init__.py.

**Frontend:**
- `frontend/src/types/announcement.ts` — All announcement + analytics types (Trend, AnalyticsHeadline, WeakTopicRow, ScoreBucket, StudentPerformanceRow, ClassAnalytics, Announcement, AnnouncementCreate/Update).
- `frontend/src/types/dashboard.ts` — `DashboardResponse.announcements: Announcement[]`.
- `frontend/src/api/client.ts` — Added `announcementsApi` (list with filters, create, update, delete) and `analyticsApi.class()`.
- `frontend/src/pages/teacher/AnnouncementsPage.tsx` — Real CRUD UI: title/body/target/subject form (with subject-picker that only appears when target=subject), edit-in-place (toggling fills the form), delete with confirmation, posted-list rendering author + subject + relative date.
- `frontend/src/pages/teacher/AnalyticsPage.tsx` — Real analytics dashboard:
    - Subject filter dropdown (all my subjects | specific subject)
    - 4 stat cards (class average, completion rate, most missed, active students)
    - Score distribution histogram rendered with raw divs (no extra chart lib needed for v1)
    - Weakest topics list with bar charts and attempts count
    - Student performance table with up/down/flat trend icons and per-student weak area
- `frontend/src/pages/student/DashboardPage.tsx` — Right sidebar gained an **ANNOUNCEMENTS** card (Megaphone icon, top 5, author + subject + relative time, line-clamped body). Hardened with optional chaining so a partial response from a stale backend can't crash the render.

**Verification — full browser E2E:**
1. Logged in as `teacher.phase11@example.com`, navigated to `/teacher/announcements`, posted "Phase 11 Quiz Now Live" targeting all students. The posted-announcements list updated in place with author name and date.
2. Navigated to `/teacher/analytics` — real numbers populated immediately:
    - Class average **40%**, completion rate **100%**, most missed **Huffman Coding Complexity**, active students **3**
    - Score distribution histogram showing 3 attempts in 0-19 and 2 in 80-100
    - 5 weakest topics (all Huffman categories @ 40% across 5 attempts)
    - Per-student rows: Phase 9 Student 50%, Phase 12 Student 50%, Arun Sanjay 0%
3. Switched to `student.phase12@example.com`, navigated to `/student` → **ANNOUNCEMENTS** card on the right sidebar shows **"Phase 11 Quiz Now Live"** with the body, "Phase 11 Teacher · 1m ago" timestamp.
4. All other dashboard sections from Phase 12 still working (XP, score, heap-based task feed, recent activity).
5. Frontend typecheck + vite build clean (650 KB / 184 KB gzipped). Zero console errors after the optional-chaining fix.

**═══ END OF V1 (Phases 1-13) — Learn Mode Foundation Complete ═══**

---

## Phase 14 — Resume Builder Backend (F6) ✅

**Complexity:** Medium-High

**What was built:**

**Backend:**
- `backend/app/schemas/resume.py` — Full schema set: `ResumeContent` (personal / summary / education[] / experience[] / projects[] / skills[] / certifications[] / achievements[]), `ResumeResponse`, `ResumeContentUpdate`, `ResumeChatRequest`/`ResumeChatResponse`, `ResumeChatHistory`, `ATSScoreRequest`/`ATSScoreResponse`, `GitHubImportRequest`/`GitHubImportResponse`/`GitHubProjectImport`.
- `backend/app/services/github_import.py` — `fetch_top_repos(username, top_n)` calls GitHub's REST API unauthenticated (60 req/hr headroom), filters out forks and archived repos, sorts by stars desc, returns top N with language + topics as tech tags. Handles 404/403/timeout cleanly.
- `backend/app/services/resume_builder.py` — Three responsibilities in one module:
    1. **Conversational AI builder** — `chat_step()` drives the Resume Coach. Current resume JSON is stuffed into the system prompt alongside `RESUME_COACH_SYSTEM` instructions that demand a strict `{ai_reply, patch}` JSON response. The patch is deep-merged into `resume.content`, validated against the Pydantic schema, and persisted. List fields are replaced wholesale per patching rules. Chat history uses the existing `chat_sessions` / `chat_messages` tables with `chat_type='resume_builder'` (single session per student, auto-created).
    2. **ATS scoring** — `score_against_jd()` sends the resume JSON + pasted job description to Claude with `ATS_SCORER_SYSTEM` asking for `{score, matched_keywords, missing_keywords, suggestions}`. Score is clamped 0-100 and persisted on the resume row.
    3. **GitHub import** — `import_github_projects()` calls `github_import.fetch_top_repos()`, skips duplicates by URL, appends new repos to `content.projects`, auto-populates `personal.github` if missing.
- **Tolerant JSON parser** — `_parse_first_json_object()` uses `json.JSONDecoder().raw_decode()` to extract just the first complete `{...}` object from Claude's response, ignoring any trailing commentary it sometimes emits despite instructions. This fixed a bug where the ATS endpoint was returning 502 on "Extra data" errors.
- XP hook: chat turns that successfully apply a patch award 8 XP via `xp.award_xp()` (`RESUME_UPDATED` event). GitHub import awards 15 XP.
- `backend/app/api/routes/resume.py` — `GET /me`, `PATCH /me`, `GET /me/messages`, `DELETE /me/messages`, `POST /me/chat`, `POST /me/ats-score`, `POST /me/import-github`. Student-only.
- Registered new router + service + schema exports.

**Frontend:**
- `frontend/src/types/resume.ts` — Mirror of all resume schemas (`ResumeTemplate`, `ResumeContent` and sub-types, `ResumeResponse`, chat types, ATS types, GitHub import types).
- `frontend/src/api/client.ts` — Added `resumeApi` (me, update, history, resetHistory, chat, scoreAts, importGithub).
- `frontend/src/pages/student/ResumeBuilderPage.tsx` — Rewritten as a real split-pane workspace:
    - **Left pane**: AI Resume Coach chat with auto-scroll, persistent history, pending-message pulse, fully wired to `/resume/me/chat` with real Claude streaming turns.
    - **Right pane**: Live resume preview driven by `content` state — Header with name + summary + contact icons (email/phone/location/github), Education, Experience, Projects (with tech badges and URLs), Skills, Certifications, Achievements. Only renders sections that have data.
    - **Action bar**: "Download PDF" (triggers `window.print()`), "ATS Score" (opens modal), "Import from GitHub" (opens modal).
    - **ATS modal**: Paste a JD → hit "Score My Resume" → renders score badge (colored by threshold), matched-keywords (green), missing-keywords (red), and actionable suggestions list.
    - **GitHub modal**: Enter username → "Import top 5" → shows imported count + repo names, immediately updates the resume preview.
    - Top bar dynamically shows `Last updated X ago` or `Empty resume — start chatting to fill it in`, plus the current ATS score badge.
- `frontend/src/index.css` — Added `@media print` stylesheet that hides everything except `.print-resume`, forces colors to black/white for printing, and hides `.no-print` sections (sidebar, chat, action bar) so the PDF download is a clean one-page resume only.

**Verification — full browser E2E:**
1. Logged in as `student.phase12@example.com`, navigated to `/student/resume` → empty-state message "Empty resume — start chatting to fill it in", Resume Coach greeting pre-populated asking for name and email.
2. Sent *"My name is Arun Sanjay. Email: arun.sanjay@rvce.edu.in. Phone: +91 98765 43210. Based in Bangalore, India. GitHub: arun-sanjay"* → Claude Haiku responded with a friendly follow-up asking about LinkedIn, personal info populated in the live preview pane (name header + email + phone + location + github icons all rendering).
3. Sent a second message adding education and a project mention → coach acknowledged and asked a focused tech-stack follow-up.
4. Opened **Import from GitHub** modal, entered `torvalds`, imported → 5 real repos landed in the Projects section with correct names, descriptions, language tags, and GitHub URLs (linux, AudioNoise, uemacs, test-tlb, pesconvert). Modal displayed "Imported 5 projects" confirmation.
5. Opened **ATS Score** modal, pasted a Linux-kernel-intern JD, clicked Score My Resume:
    - **Initial attempt failed** with `ATS scorer returned invalid JSON: Extra data: line 32 column 1 (char 1212)` — Claude leaked trailing text after the JSON object.
    - **Fix**: replaced `json.loads()` with tolerant `_parse_first_json_object()` that uses `raw_decode` to extract just the first `{...}`.
    - **Retry succeeded**: ATS score **28/100**, matched keywords `[C, Linux, memory, TLB, open source]`, missing keywords `[Linux kernel, systems programming, Git, performance optimization, debugging, kernel modules, eBPF, perf tools, system call, upstream contributions]`, 5 actionable suggestions including the savagely accurate *"Replace placeholder GitHub projects (which appear to be forks of Linus Torvalds' repos) with your own original kernel contributions"*.
6. Frontend typecheck + vite build clean (659 KB / 186 KB gzipped). Print stylesheet verified — `window.print()` shows only the resume preview.

**Notes:**
- Claude Haiku 4.5 handles the multi-turn coach + ATS scoring cleanly at ~$0.0002 per turn. Running through dozens of test turns cost fractions of a cent from the $5.24 Console balance.
- Per-student resume row is auto-created on first `GET /resume/me`, so there's no onboarding friction.
- The Resume Coach is idempotent — users can reset the chat with `DELETE /resume/me/messages` and start over, or edit the content directly via `PATCH /resume/me`.

---

## Phase 15 — Adaptive Learning Engine (F7, F17, F18, F22) ★ RESEARCH CORE ✅

**Complexity:** High

**What was built:**

**Backend — algorithms:**
- `backend/app/services/dijkstra.py` — Binary-heap Dijkstra's shortest path over the weighted directed skill graph. `dijkstra_multi_target()` runs one heap pass from the source and returns the shortest path to each of N targets — used to find routes to every skill a company requires. O((V + E) log V) time.
- `backend/app/services/knapsack.py` — Bottom-up 0/1 Knapsack DP with ½-hour integer discretization (`SCALE = 2`), path reconstruction via standard predecessor backtracking. O(n · W) time, O(n · W) space for the DP table.
- `backend/app/services/mst.py` — Prim's Minimum Spanning Tree with a binary min-heap. `mst_over_subset()` builds an undirected view of the graph restricted to skills involved in the current plan, anchors at the highest-out-degree node, returns edges + total weight. O((V + E) log V).

**Backend — data + service layer:**
- `backend/app/services/skill_graph_seed.py` — **58 skill nodes** across 10 domains (DSA, Web, Systems, DB, Cloud, ML, SysDesign, Mobile, Fundamentals, Languages, Soft), **69 prerequisite edges** with hand-tuned base hours, and **20 company profiles** (MAANG, Indian unicorns, finance, service companies, OpenAI ML, Startup intern) each with 6-12 required + preferred skills. All idempotent — loaded on first API call via `seed_if_empty()`.
- `backend/app/services/skill_graph.py` — the research-paper core:
    - **Mastery computation** (`compute_mastery`) — walks `student_profile.skills` (implicit 0.75) + per-topic quiz averages (full credit), with a **strict word-boundary token-set matcher** that prevents false positives like matching "Go" to "Huffman Algorithm Steps". Returns `MasterySnapshot {per_skill, quiz_topics, declared_skills}`.
    - **Dynamic edge rescaling** (`_rescale_graph`) — the formula that IS the paper's contribution:
      ```
      adjusted = base × (1 − α·mastery(u)) × (1 + β·(1 − mastery(v) if v ∈ target))
      ```
      with `α = 0.55` (confidence discount for strong prerequisites), `β = 0.40` (urgency surcharge for weak target skills), and a `MIN_EDGE_WEIGHT = 0.5h` floor so nothing collapses to zero.
    - **Bootstrap source** (`_add_virtual_source`) — adds a synthetic `__START__` node with (a) 0-cost edges into every mastered skill, (b) small-cost edges into tier-1 foundation skills, and (c) small-cost edges into "orphan roots" (nodes with no incoming edges) so skills like OS Concepts, Problem Solving, and Computer Networks remain reachable for brand-new students.
    - **Dijkstra → Knapsack pipeline**: runs `dijkstra_multi_target(__START__, required_skills)`, turns each reachable missing skill into a `KnapsackItem(hours=path_cost, value=10·(1+gap))`, solves 0/1 Knapsack against the student's available-hours budget.
    - **Prim's MST** over the subgraph induced by all involved nodes — renders a companion "minimum learning tree" for the paper's visualization.
    - **Skill gap breakdown** (`_compute_gap`) — set difference + cosine similarity between the mastery vector and a binary requirement vector.
    - **Research logging** — every plan persists to the existing `study_optimizer_results` table with predicted improvement, included topics, and excluded topics, ready for the paper's evaluation on 30 classmates over 2 weeks.
- `backend/app/schemas/skills.py` — Pydantic mirror of every piece: `SkillNodeResponse`, `CompanyProfile`, `MasterySnapshotResponse`, `GapBreakdownResponse`, `SkillPathResult`, `MSTResponse`, `KnapsackResponse`, `AdaptivePlanRequest`, `AdaptivePlanResponse`, `StudyOptimizerHistoryRow`.
- `backend/app/api/routes/skills.py` — 5 endpoints:
    - `GET /skills/nodes` — all skills + metadata
    - `GET /skills/graph` — full edge list (base weights)
    - `GET /skills/companies` — all company profiles
    - `POST /skills/me/plan` — build an adaptive plan for a target company + role + hours budget
    - `GET /skills/me/plans` — past plan history for research paper data
- Registered the new router, services, and schemas in `__init__.py` / `router.py`.

**Frontend:**
- `frontend/src/types/skills.ts` — Full type mirror.
- `frontend/src/api/client.ts` — Added `skillsApi` (nodes, companies, buildPlan, planHistory).
- `frontend/src/pages/student/SkillGapPage.tsx` — Replaced the mock data with a full real-time adaptive learning dashboard:
    - Header with "Cosine sim X%" badge
    - Target company dropdown (20 real companies from the API)
    - Hours slider that re-computes the plan on every change
    - **Gap Score card** with readiness progress bar
    - **Skill Map** showing current skills + per-target Dijkstra paths rendered inline with arrow glyphs ("`Linked Lists → Trees`") and per-path hour badges
    - **Optimized Study Plan (0/1 Knapsack DP)** table with topic / hours / value / reason / status for every item (included or excluded), plus a predicted-gain summary row
    - **Minimum Learning Tree (Prim's MST)** — grid view of edges with hours
    - **Mastery Snapshot** — color-coded badges per declared or quiz-backed skill

**Verification — full browser E2E:**

Scenario: Student `student.phase12@example.com` targeting **Google SWE** with a 15h/week budget.

**Before any declared skills:**
- Readiness 0%, gap 100%, cosine 0.0
- All 9 required skills reachable via the foundation-bootstrap, shortest paths computed
- Knapsack picks 6 of 9 → Arrays (1h), Hashing (1h), Trees (7.2h), DP (3.8h), OS Concepts (1h), Problem Solving (1h) — predicted +66.67%, 15h of 15h used

**After declaring `["Arrays", "Hashing", "Linked Lists", "Problem Solving"]` on the student profile:**
- Readiness **33.33%**, cosine **0.50**, 3/9 present, 6 missing
- All edges from Arrays/Hashing/Linked Lists got α-discounted; Dijkstra re-routed:
    - Trees path was `Arrays → Stacks & Queues → Trees` at 7.2h → became **`Linked Lists → Trees` at 3.3h** (different route!)
    - Graphs: 5.2h → **2.5h** (Hashing prereq is mastered)
    - Dynamic Programming: 3.8h → **1.6h** (Problem Solving prereq is mastered)
    - DSA Advanced: 12.2h → **10.0h**
- Knapsack now fits **8 of 9 targets** in the same 15h budget (up from 6), predicted **+88.9%** (up from +66.67%)
- Only DSA Advanced excluded (10.0h was too expensive for the remaining budget)
- Prim's MST: 22h total across 7 edges touching 8 skills

**Budget stress test** (same student, varying hours):
- 5h → Knapsack picks 4 cheapest (Arrays, Hashing, OS Concepts, Problem Solving), predicted +40.89%
- 15h → Knapsack picks 8 (everything except DSA Advanced), predicted +88.9%
- 30h → Knapsack picks all 8, still excludes DSA Advanced due to path cost, predicted +83.44%

Every plan was persisted to `study_optimizer_results` with a `plan_id` UUID for the research paper's data collection. Frontend typecheck + vite build clean (663 KB / 187 KB gzipped).

**DAA concepts demonstrated in this single phase:**
- **Dijkstra's shortest path** (Unit IV) — with **dynamic edge weights** driven by student mastery
- **0/1 Knapsack DP** (Unit IV) — time-constrained study optimization
- **Prim's MST** (Unit IV) — minimum prerequisite tree visualization
- **Set operations + cosine similarity** (DMS Unit I) — skill gap breakdown
- **Graph theory** — orphan-root detection, topological bootstrap, multi-target shortest paths

**Research paper angle:** *"A Dynamic Graph-Based Framework for Personalized Learning Path Optimization Under Time Constraints in Engineering Education"*. The key contribution is the rescaling formula `adjusted = base · (1 − α·mastery(u)) · (1 + β·(1 − mastery(v)))` which makes edges adaptive to per-student performance without rebuilding the graph — students with strong prerequisites get shorter paths automatically, and weak target skills bias the plan toward more urgent foundational moves.

**Evaluation plan for the paper:** the `study_optimizer_results` table now logs every (student, target, budget, included_topics, predicted_improvement) tuple. To finish the paper, split 30 RVCE classmates into a control group (no optimizer) and a test group (uses the optimizer weekly) for 2 weeks, then compare the delta in quiz scores across the two groups.

---

## Phase 16 — Mock Interview Text Mode (F9) ✅

**Complexity:** Medium

**What was built:**

**Backend:**
- `backend/app/schemas/mock_interview.py` — `InterviewStartRequest`, `InterviewMessageRequest`, `InterviewTranscriptTurn`, `RoundSummary`, `InterviewSessionResponse`, `InterviewTurnResponse`, `InterviewSessionListRow`, plus the `ROUND_NAMES` map (1=HR, 2=Technical, 3=System Design, 4=Managerial, 5=Negotiation).
- `backend/app/services/mock_interview.py` — **pure-Python state machine, no LangGraph**:
    - **4 persona voices** (`FRIENDLY`, `TOUGH`, `RAPID_FIRE`, `UNPREDICTABLE`) — each with a distinct system-prompt voice injected into every Claude call.
    - **5 rounds** (`ROUND_DESCRIPTIONS`) with round-specific question guidance — HR asks about background/motivation, Technical probes DSA/coding, System Design covers load balancing/caching/sharding, Managerial probes STAR stories, Negotiation simulates compensation conversation.
    - **Per-round weighted scoring** (`ROUND_WEIGHTS`): HR 15% / Technical 30% / System Design 25% / Managerial 15% / Negotiation 15%, blended into a 0-100 overall score.
    - **Strict JSON protocol** for Claude turns — every assistant call returns `{score (0-10 REQUIRED), score_reason, next_message, advance_round}`. Tolerant parser via `_parse_first_json_object()` (reused from the resume phase) handles Claude's occasional trailing commentary.
    - **`student_turn()`** is the main state transition: appends the student answer to the transcript, builds the persona+round system prompt, sends the last 12 turns as conversation history, calls Claude, parses the JSON, attaches the score to the user turn, decides whether to advance rounds based on `advance_round OR scored_count >= questions_per_round`, persists transcript + state with `flag_modified()` on both JSON columns.
    - **`create_session()`** seeds a synthetic persona-appropriate opening message so the UI has instant content.
    - **`complete_and_debrief()`** computes the weighted overall score, calls Claude once more with `DEBRIEF_SYSTEM` to generate `{hire_verdict, headline, strengths, improvements, standout_answer, biggest_gap}`, persists to `feedback_report`, awards XP scaled by the overall score via `xp.award_xp(MOCK_INTERVIEW_COMPLETED, bonus_multiplier=1 + overall/100)`.
    - **`end_session()`** lets the student force-finish early and still get a debrief with whatever rounds they completed.
    - **Critical fix**: JSON column mutations in SQLAlchemy don't trigger dirty-tracking by default. Uses `flag_modified(session, "state")` and `flag_modified(session, "transcript")` after every mutation so the state machine actually persists between turns. Before this fix, `questions_asked` stayed at 0 and scores never accumulated.
- `backend/app/api/routes/interviews.py` — 5 endpoints: `POST /interviews/` (start), `GET /interviews/me` (list mine), `GET /interviews/{id}`, `POST /interviews/{id}/messages` (student turn), `POST /interviews/{id}/end` (force finish + debrief).
- Registered router + service + schema exports.

**Frontend:**
- `frontend/src/types/interview.ts` — Full mirror: `InterviewMode`, `InterviewPersona`, `HireVerdict`, `RoundStatus`, `InterviewTranscriptTurn`, `RoundSummary`, `InterviewFeedbackReport`, `InterviewSessionResponse`, `InterviewTurnResponse`, `InterviewSessionListRow`.
- `frontend/src/api/client.ts` — `interviewsApi` with `start`, `get`, `sendMessage`, `end`, `listMine`.
- `frontend/src/pages/student/MockInterviewPage.tsx` — Rewrote all 3 views to use the real API:
    - **Setup**: company grid, role chips, persona grid (with emojis + descriptions mapped to the backend enum values), mode toggle (Text active, Voice disabled with "Phase 20" tooltip), Start button with loading spinner.
    - **Interview**: 5-round stepper with `completed/active/locked` colors driven by the server `round_summaries`, round banner, chat transcript with per-answer score badges (color-coded by score band, showing `score_reason` inline), "Thinking…" placeholder during the server roundtrip, End Interview button.
    - **Debrief**: hero score card with overall/100 and verdict badge (`strong_hire / hire / leaning_no / no_hire`), round breakdown table with per-round progress bars, Strengths / Improvements / Standout / Gap cards populated from `feedback_report`, Download Report (print) and Try Again buttons.

**Verification — full browser + API E2E:**

**API-driven full run**:
1. Started session (`company=Google, role=SWE, persona=tough, mode=text`) → synthetic opening delivered instantly, rounds stepper showed Round 1 active.
2. Submitted 9 answers across 5 rounds via the `/messages` endpoint:
    - Round 1 (HR, 2 Qs): 6.0 avg
    - Round 2 (Technical — two-sum + two-pointer variant, 2 Qs): 7.0 avg
    - Round 3 (System Design — URL shortener, 2 Qs): 6.0 avg
    - Round 4 (Managerial — STAR story + prioritisation, 2 Qs): 6.5 avg
    - Round 5 (Negotiation — salary range + counter-offer, 2 Qs): 6.5 avg
3. `interview_completed=true` fired on the final turn → `complete_and_debrief()` ran → overall weighted score **64.5/100** → `hire_verdict="hire"` → headline *"Solid technical foundation with good project experience, but inconsistent focus and incomplete answers under pressure limit readiness for Google's bar."*
4. Session persisted with 21 transcript turns, every user turn has `score` + `score_reason`.

**Browser UI run**:
1. Navigated to `/student/interview`, picked `Google / SWE / Tough`, clicked Start Interview.
2. Interview view rendered with the 5-round stepper (Round 1 active, others locked), banner "ROUND 1: HR / BEHAVIOURAL", and the Tough persona's opening: *"Okay, let's get straight to it. We're interviewing for Google. In 60 seconds or less: who are you, and why should we even consider you?"*
3. Typed a response, hit Send → user message appeared, score badge rendered: **`Score: 7.0/10 — Strong technical credentials and shipped product, but claim needs scrutiny—'research-level' is vague and Dijkstra + pgvector are standard tools, not novel research.`** (the Tough persona absolutely landed). Next assistant question streamed in asking for specific contributions vs team.
4. Frontend typecheck + vite build clean (667 KB / 188 KB gzipped). Zero console errors.

**Cost**: full 5-round interview = ~10 Claude Haiku calls at ~$0.0002 each = ~$0.002 per interview. The $5.24 balance can handle ~2500 full interviews.

**Plumbing notes for Phase 20 voice mode:**
The state machine is already independent of the IO channel. Phase 20 only needs to add Whisper transcription in front of `student_turn()` and ElevenLabs TTS after it — the backend logic, scoring, and debrief generator stay as-is.

---

## Phase 17 — Placement Chatbot + Jobs + Community (F4, F8, F12) ✅

**Complexity:** Medium

**What was built:**

**Backend — Placement Chatbot (F8):**
- Reuses the existing chat_sessions / chat_messages infra with `chat_type='placement_chatbot'` — no new tables needed.
- `services/vector_search.py` — `search_college_chunks()` gained a `category` filter so we can narrow to `document_category='placement_record'`.
- `services/ai_chat.py` — Added `PLACEMENT_CHATBOT_SYSTEM` (placement-coach voice that demands data-backed advice) and a new dispatch branch in `stream_rag_response()` that runs college-chunk search with the placement filter. The note-assistant / CollegeGPT flows are unchanged.

**Backend — Job Tracker (F12):**
- `schemas/jobs.py` — `JobListingCreate/Response`, `JobApplicationCreate/Update/Response`, `JobBoardResponse` (Kanban-ready with 6 buckets).
- `services/job_tracker.py` — CRUD + **dynamic fit score**:
    - `_compute_fit_score()` extracts keyword tokens from the job's `requirements + description`, matches them against skill-graph node names (word-boundary token-set match with a majority rule), then averages the student's mastery across the matched skills × 100. Neutral 50 fallback if no overlap.
    - `_build_fit_context()` caches the Phase 15 mastery snapshot once per request so batch listings don't thrash.
    - `save_or_update_application()` is idempotent — clicking Save twice on the same listing just updates the existing application instead of creating duplicates.
    - `list_my_board()` returns applications pre-bucketed by status for the Kanban view.
    - `seed_sample_listings_if_empty()` drops 6 realistic listings (Google SWE Intern, Amazon SDE-1, Flipkart Full-Stack, Swiggy Backend, Infosys Power Programmer, Microsoft SWE Intern) with rich requirement strings that exercise the fit-score keyword matcher.
- `routes/jobs.py` — 7 endpoints: list, create, delete, seed (admin helper), my-board, save/update application, delete application.

**Backend — Community (F4):**
- `schemas/community.py` — `DoubtCreate`, `DoubtResponse`, `DoubtDetailResponse`, `DoubtAnswerCreate`, `DoubtAnswerResponse`.
- `services/community.py` — Full CRUD + **lazy AI fallback**:
    - Doubts CRUD: create, list (with search/tag/only_mine filters, batch answer-count aggregation, batch AI-flag aggregation), get-detail (auto-bumps view count, sorts answers by accepted → upvotes → created_at), upvote, delete.
    - Answers CRUD: create (awards `DOUBT_ANSWERED` XP), upvote (awards `DOUBT_UPVOTED` XP to the author if it's not their own answer), accept (only the doubt's author can accept, unsets any previously accepted answer, marks doubt resolved).
    - **AI fallback** — `_maybe_generate_ai_fallback()` is called on every `get_doubt()` read. Triggers iff: zero human answers AND zero existing AI answer AND doubt age ≥ 10 minutes AND Claude is configured. Uses `COMMUNITY_AI_SYSTEM` — a senior-student voice, 3-6 short paragraphs, no "AI" signature (the badge handles that). Lazy-on-read means no background scheduler needed, only pays for reads.
- `routes/community.py` — 8 endpoints: list, create, get, upvote, delete, create answer, upvote answer, accept answer.

**Frontend:**
- `types/jobs.ts` + `types/community.ts` — Full type mirrors.
- `api/client.ts` — `jobsApi` (list, create, delete, seed, myBoard, saveApplication, updateApplication, deleteApplication) + `communityApi` (list, create, get, upvote, delete, answer, upvoteAnswer, acceptAnswer).
- `pages/student/PlacementChatPage.tsx` — Rewrote to use the real chat infra: finds-or-creates a `placement_chatbot` session, streams Claude responses with citation refresh, right sidebar shows the real student profile (from `/auth/me`), "New chat" button spins up a fresh session.
- `pages/student/JobTrackerPage.tsx` — Real Kanban board:
    - Top strip of **Available Listings** with per-card fit scores (color-coded badges) and Save-to-board buttons that flip to "In board" once saved.
    - **Add Listing modal** with title/company/location/type/description/requirements fields.
    - **6-column Kanban** (Saved / Applied / OA Received / Interview / Offer / Rejected) with per-card status dropdown that calls `PATCH /jobs/me/applications/{id}` to move the card. Hover-reveal delete button per card.
    - Auto-seeds the listings table if empty on first load.
- `pages/student/CommunityPage.tsx` — Real doubt board:
    - Search + auto-computed tag filter chips from the posted doubts.
    - **Ask a Doubt modal** with title/body/tags form.
    - **Doubt cards** showing title, body snippet, tags, answer count, upvotes, relative time, `AI Answered` badge, `Resolved` badge.
    - **Detail modal** (xl size) showing full doubt, all answers sorted by accepted → upvotes, per-answer upvote + accept buttons (accept only shown to the doubt's author), and an answer composer at the bottom.

**Verification — backend + browser E2E for all 3 features:**

1. **Placement Chatbot**: Created a `placement_chatbot` session, asked *"What should I focus on for a Google SWE interview in 3 weeks?"* → Claude streamed a real placement-focused response starting with *"# Google SWE Interview in 3 Weeks — Focus Areas"* with priority-weighted time breakdowns. Correctly flagged that it didn't have college-specific placement records since none are uploaded yet.

2. **Job Tracker**:
    - Seeded 6 sample listings, fit scores computed against the Phase 12 student's mastery (Arrays/Hashing/Linked Lists/Problem Solving):
        - Google SWE Intern: **15%** (half the requirements mastered)
        - Amazon SDE-1: 7.5%
        - Flipkart Full-Stack: 0% (no React/TS mastery)
        - Swiggy Backend: 8%
        - Infosys Power Programmer: **19%** (closest match)
        - Microsoft SWE Intern: 9%
    - Saved Google to board (status=saved, fit=15), then moved to applied via PATCH → board reflected the change immediately.
    - Browser UI rendered the full Kanban with the applied Google card in the Applied column, status dropdowns working, Available Listings strip showing "In board" for the saved one and "Save to board" for the rest.

3. **Community**:
    - Posted a doubt *"Why does Dijkstra fail on negative edge weights?"* with tags `[DAA, Graphs]`.
    - Posted a peer answer with a concrete 3-node counter-example.
    - **AI fallback test**: backdated a separate doubt *"How does Huffman coding guarantee optimal prefix codes?"* to 15 minutes ago via SQL. Opened it via `GET /community/{id}` → the lazy fallback fired → Claude generated a real answer starting with *"The key insight is that Huffman coding is greedy — it always merges the two smallest-frequency nodes — and we can prove this choice is safe using an exchange argument..."* with `is_ai_generated=true`, `answered_by_name=null`.
    - Community page rendered both doubts with the "AI Answered" badge visible on the Huffman one; tag filter chips auto-computed `[All, DAA, Graphs, Greedy, Huffman]` from posted doubts.

4. **Build + typecheck clean** (680 KB / 190 KB gzipped). Zero console errors.

**Cost**: Placement Chatbot ~$0.0001 per question, Community AI fallback ~$0.0001 per triggered doubt. Fits comfortably in the $5.24 balance.

**Data-privacy note**: The AI fallback only fires on read (lazy), so doubts that never get opened also never burn Claude credits. And because the trigger requires zero human answers, any doubt with even one real peer reply stays human-only forever.

---

## Phase 18 — Full Gamification + CampusIQ Score (F13, F14, F16) ✅

**Complexity:** Medium

**What was built:**

**Backend:**
- `services/campus_iq_score.py` — **Expanded from the Phase 12 academic-only pillar into a full 4-pillar composition** (DMS Unit III function composition):
    - **Academic** (30% weight): weighted average of the last 10 quiz scores with difficulty bonus (easy 0.7, medium 1.0, hard 1.3).
    - **Skill** (25% weight): difficulty-tier-weighted average mastery across every skill-graph node, pulled from the Phase 15 `compute_mastery()`. Lazy-imports skill_graph to avoid circular deps.
    - **Interview** (25% weight): best overall mock-interview score + diminishing-returns session bonus (+1.5 per session, capped at +5).
    - **Placement** (20% weight): blended ATS score (0-50) + application count (0-25, 5 apps maxes it) + distinct-company diversity (0-25, 5 companies maxes it).
    - `total = 0.30·academic + 0.25·skill + 0.25·interview + 0.20·placement`
- `services/leaderboard.py` — **DMS Unit III partial order** over student scores. `tier_for_score()` maps into 5 equivalence classes (Diamond ≥ 90, Platinum ≥ 80, Gold ≥ 60, Silver ≥ 40, Bronze otherwise). `get_leaderboard()` returns top-K rows with per-pillar breakdown, tier, XP, level, and `is_current_user` flag. `get_my_rank()` counts "strictly better" scores so the current user can see their rank even when outside the top-K.
- `services/skill_tree.py` — **DAA Unit II DFS-based unlock detection**. For every graph node, reverses the adjacency list once to get `prereqs[v]`, then classifies each node as `mastered` (mastery ≥ 0.5), `unlocked` (all prereqs mastered or it's a root), or `locked`. Groups by domain with sort-order `difficulty_tier → name`, returns per-domain progress percentages + an overall progress number.
- `services/profile.py` — Full student profile service:
    - `BADGE_CATALOG` — 7 badge definitions (first_quiz, quiz_streak_5/10, first_interview, interview_pro, placement_ready, level_10).
    - `check_and_award_badges()` — idempotent scan of all thresholds, inserts any newly earned badges, safe to call after every XP event.
    - `get_profile()` — recomputes score + badges, bundles the full public profile (4 pillars, rank, tier, badges, skills, targets, GitHub/LinkedIn, XP/level/streak, member_since).
    - `update_profile()` — self-service update with validation, auto-recomputes CampusIQ score on every change so the skill pillar stays in sync with declared skills.
- `schemas/gamification.py` — `LeaderboardRowResponse`, `LeaderboardResponse`, `SkillNodeStateResponse`, `DomainProgressResponse`, `SkillTreeResponse`, `BadgeResponse`, `PublicProfileResponse`, `ProfileUpdateRequest`.
- `routes/gamification.py` — 5 endpoints under `/gamification/`:
    - `GET /leaderboard?limit=50` — top-K + my_row + total_students
    - `GET /skill-tree/me` — full domain-grouped tree with unlock states
    - `GET /profile/me` — full profile with pillars + badges + rank + tier
    - `PATCH /profile/me` — self-service edit with auto-recompute
    - `POST /score/me/recompute` — force a full 4-pillar refresh
- Registered router + service exports.

**Frontend:**
- `types/gamification.ts` — Full type mirror with `Tier`, `UnlockState` literal types.
- `api/client.ts` — Added `gamificationApi` (leaderboard, mySkillTree, myProfile, updateProfile, recomputeScore).
- `pages/student/LeaderboardPage.tsx` — Rewritten:
    - Top-3 **podium** with colored blocks (gold/silver/bronze), highlighting the current user with "(you)" suffix when they're in the top 3.
    - **Ranked table** for everyone below rank 3, with rank # / name / score / level / XP / tier badge. Current-user row gets a primary-tinted background.
    - Tier-band legend.
    - "YOUR RANK" header showing the current user's rank + tier even if they're outside the top-K.
- `pages/student/SkillTreePage.tsx` — Rewritten:
    - Overview card with `X/Y skills mastered` + overall progress bar.
    - 2-column grid of **DomainCard**s (one per domain), each showing label (mapped from domain code to pretty name), mastered/unlocked counts, per-domain progress bar, and a flex-wrap of skill pills colored by state (`mastered` → green CheckCircle2, `unlocked` → primary-tinted Sparkles, `locked` → grey Lock + 60% opacity).
    - All 11 domains (DSA / Web / Systems / DB / Cloud / ML / SysDesign / Mobile / Fundamentals / Languages / Soft).
- `pages/student/ProfilePage.tsx` — Rewritten:
    - Header card with avatar, name, tier badge, rank badge, branch/sem/CGPA line, Edit + Share buttons.
    - 4 stat cards (CampusIQ Score, Total XP, Level, Streak).
    - **CampusIQ Score Breakdown** card with per-pillar progress bars and the composed total at the bottom — all 4 pillars rendered from real backend values.
    - **Badges** grid showing earned badges with icons pulled from `lucide-react` via a `BADGE_ICONS` map.
    - **Skills** chip list.
    - **Placement Targets** card with target role, target companies, GitHub / LinkedIn links.
    - **Edit Profile modal** — branch / semester / cgpa / github / linkedin / skills / target companies / target role fields. Saves via `PATCH /profile/me` which triggers a score recompute server-side.

**Verification — full E2E:**

1. `GET /gamification/profile/me` returned for the Phase 12 student:
    - **Pillars**: academic 50, skill 3.66, interview 66, placement 24
    - **Total**: 37.22 (= 0.30·50 + 0.25·3.66 + 0.25·66 + 0.20·24)
    - Rank 2, tier Bronze, 2 badges auto-awarded ("First Quiz", "First Mock Interview")
    - Skills: `[Arrays, Hashing, Linked Lists, Problem Solving]`, Level 2, 253 XP, 2-day streak
2. `GET /gamification/leaderboard` returned 3 ranked students:
    - #1 Phase 9 Student — 50, silver
    - #2 Phase 12 Student — 37.22, bronze (highlighted as "you")
    - #3 Arun Sanjay — 0, bronze
3. `GET /gamification/skill-tree/me` returned 11 domains with correct DFS unlock detection:
    - DSA: 3/15 mastered, 3 unlocked (Arrays/Hashing/LinkedLists mastered → Strings/Searching/Sorting/etc. unlocked because their prereqs are satisfied)
    - Soft Skills: 1/2 mastered (50%), Problem Solving mastered → Communication unlocked
    - Fundamentals: 0/4 mastered but 4 unlocked (all roots)
    - Systems, Web, DB, Mobile, Languages each have unlocked roots
    - ML/SysDesign/Cloud have 0 unlocked (prereqs not met yet)
    - Overall: 4/58 = 6.9% mastered
4. **Profile edit round-trip**: `PATCH /gamification/profile/me` with 11 declared skills and updated branch/semester/CGPA/GitHub/targets:
    - Skill pillar jumped from **3.66 → 12.54** (more declared skills → higher tier-weighted average)
    - Total CampusIQ jumped from **37.22 → 39.44** automatically
    - The 3 unchanged pillars stayed exactly the same
5. Browser UI for all 3 pages renders cleanly with real data — podium, ranked table, domain cards with unlock state colors, pillar breakdown card, badges grid, skills chips, placement targets.
6. Frontend typecheck + vite build clean (683 KB / 190 KB gzipped). Zero console errors.

**DAA / DMS concepts demonstrated:**
- **DMS Unit III — function composition**: total = weighted sum of 4 pillar functions
- **DMS Unit III — equivalence relations / partial order**: tier bands partition students into 5 classes
- **DAA Unit II — BFS/DFS**: skill-tree unlock traversal via reversed adjacency lists
- **DAA Unit II — topological sort**: implicit in the DFS-based unlock order

**Instant feedback loop**: every quiz submit, mock interview finish, job application change, and profile edit automatically triggers `campus_iq_score.recompute_score()`, keeping the 4-pillar total + leaderboard rank fresh with zero manual work. The badge catalog is scanned on every profile fetch so newly crossed thresholds become visible immediately.

---

## Phase 19 — Algorithm Showcase Features (F18, F21, F23, F25, F26) ✅

**Complexity:** Medium-High

**Goal:** Implement the four remaining syllabus-mapped algorithm services and wire them to existing teacher/admin/student pages so each one is demonstrable end-to-end.

**Backend services:**
- `backend/app/services/hamming.py` — pairwise Hamming distance over `QuizAttempt.answer_bit_vector` (1 = correct, 0 = wrong). Auto-pads variable-length vectors, takes the latest attempt per student to avoid retake double-counting, returns `(flagged_pairs, total_attempts, mean_pairwise_similarity)`. `persist_flags()` is idempotent — re-running on the same quiz upserts into `quiz_similarity_flags` (DMS Unit IV).
- `backend/app/services/inclusion_exclusion.py` — set operations for skill analytics. `analyze_skills()` reads up to 4 skills, finds matching students per skill (case-insensitive), then uses `itertools.combinations` to compute every k-way intersection (k = 2..n) and applies the inclusion-exclusion principle to derive the actual union from the naive sum. Returns per-skill counts, intersections, naive sum, actual union, correction, and matching student names (DMS Unit I).
- `backend/app/services/graph_coloring.py` — greedy chromatic number for quiz scheduling. Builds the conflict graph (nodes = quizzes, edges = "share at least one student"), then runs largest-degree-first greedy coloring. Each color is one parallel time slot — every quiz in the same color can run simultaneously without anyone facing two at once. Teachers see only their own quizzes; admins see everything (DMS Unit V).
- `backend/app/services/backtracking_schedule.py` — branch-and-bound study schedule. 2D grid (days × hours), locks lunch at 13:00 and dinner at 20:00, then runs DFS over (place task in feasible slot run | skip task) with priority-desc ordering and bound pruning (`remaining_max + current ≤ best ⇒ skip`). Returns scheduled slots, skipped tasks, total value, total hours, and explored node count (DAA Unit V).

**API routes** (`backend/app/api/routes/algorithms.py`):
- `POST /api/v1/algorithms/hamming/quiz/{quiz_id}` (teacher/admin) — `?max_distance=2&persist=true`
- `POST /api/v1/algorithms/inclusion-exclusion` (teacher/admin) — body: `{ skills: [up to 4] }`
- `POST /api/v1/algorithms/graph-coloring/quizzes` (teacher/admin) — no body
- `POST /api/v1/algorithms/schedule/generate` (any authenticated student) — body: `{ tasks: [...], days, hours?, locked_hours? }`

**Schemas:** `backend/app/schemas/algorithms.py` — `HammingPairResponse`, `SimilarityCheckResponse`, `SkillSetCount`, `SkillIntersection`, `InclusionExclusionRequest/Response`, `QuizSlotAssignmentResponse`, `GraphColoringResponse`, `StudyTaskInput/Response`, `ScheduleSlotResponse`, `GenerateScheduleRequest/Response`.

**Frontend pages wired:**
- `frontend/src/pages/teacher/SimilarityCheckerPage.tsx` — quiz selector + threshold dropdown + run button. Renders stat cards (total attempts / flagged pairs / mean similarity %) and a table of flagged pairs with severity-coloured Hamming distance badges (red ≤1, amber ≤3, green higher).
- `frontend/src/pages/admin/SkillAnalyticsPage.tsx` — 4 skill input fields + run analysis. Renders matching students, naive sum, overlap correction, per-skill counts, every k-way intersection card, the inclusion-exclusion formula, and matching student names.
- `frontend/src/pages/teacher/QuizSchedulingPage.tsx` — auto-runs on mount. Renders quiz / edge / chromatic-number stat cards, time-slot assignment cards (one per color, with rotating slot border accent), and a conflict graph card listing each quiz with its conflict list.
- `frontend/src/pages/student/SchedulePage.tsx` — editable task list (topic / hours / priority / subject), days input, generate button, auto-run on mount. Renders scheduled / hours / value / nodes-explored stat cards, skipped tasks card, and a `days × hours` weekly grid table with subject-coded cells (DAA blue, CN purple, DMS green, OS amber) and lunch/dinner locks shown as italic "lunch"/"dinner" placeholders.

**Frontend types/api:** `frontend/src/types/algorithms.ts` exports the 4 endpoint shapes; `frontend/src/api/client.ts` exports `algorithmsApi.{hammingForQuiz, inclusionExclusion, graphColoringForQuizzes, generateSchedule}`.

**Concepts wired into the syllabus:**
- Pairwise Hamming distance (DMS Unit IV) → similarity checker
- Inclusion-exclusion principle (DMS Unit I) → skill analytics
- Greedy graph coloring / chromatic number (DMS Unit V) → quiz scheduling
- Backtracking + branch-and-bound (DAA Unit V) → study schedule generator

**Browser E2E (verified):**
- **SchedulePage** (Phase 12 student) — 5 default tasks, 3 days, branch-and-bound returned `5/5 scheduled, 14h used, value=43, 95 nodes explored`. Weekly grid renders Arrays/Hashing, Trees, DP, TCP/UDP, and Mock Interview Prep correctly across Mon/Tue/Wed with the 13:00 lunch lock visible.
- **SimilarityCheckerPage** (Phase 11 teacher) — selecting "Huffman Coding Fundamentals" + threshold ≤2 returns `4 attempts, 6 flagged pairs, 80% mean similarity`. The flagged-pairs table shows three pairs at distance 0 (100% similarity, red badge) and three pairs at distance 2 (60% similarity, amber badge).
- **QuizSchedulingPage** (Phase 11 teacher) — after seeding 2 extra quizzes (CN OSI Layers, DMS Set Theory) plus 6 cross-attempts that form K₃, the page renders `3 quizzes, 3 conflict edges, χ = 3`. Each quiz lands in its own slot (Slot 1 / 2 / 3) with the conflict list shown — exactly what the chromatic number of a triangle should be.
- **SkillAnalyticsPage** (Phase 19 admin) — running with `[Python, React, SQL, JavaScript]`: matching = 1/6, naive sum = 4, every k-way intersection (6 pairs + 4 triples + 1 quadruple) = 1, overlap correction = -3. Inclusion-exclusion: |A∪B∪C∪D| = 4 − 6 + 4 − 1 = **1** ✓.

**Build:** `npx tsc --noEmit` clean, `npx vite build` succeeds in 757 ms (691 KB JS / 36 KB CSS).

---

## Phase 20 — Voice Interview + Confidence Coach (F9 voice, F11) ★ DEMO SHOWSTOPPER ✅

**Complexity:** High

**Goal:** Whisper transcription + Claude scoring + ElevenLabs voices (5 personas, one per round) for the mock interview, plus a Confidence Coach that captures video/audio in the browser, scores filler words / pace / clarity, and tracks growth across sessions.

**Backend services:**
- `backend/app/services/speech.py` — Single home for both vendors. `transcribe_audio()` wraps OpenAI `whisper-1` (accepts the browser's `audio/webm;codecs=opus` blob directly). `synthesize_speech()` / `synthesize_and_save()` wrap ElevenLabs v2 `text_to_speech.convert()` with the `eleven_turbo_v2_5` model and persist MP3s to `backend/uploads/audio/`. Both clients are `lru_cache`-d, both `is_*_available()` checks return False when keys are missing so the rest of the app degrades gracefully. `MAX_TTS_CHARS = 900` truncates long prompts to protect the starter plan quota. `VOICE_BY_ROUND` maps each interview round to a different voice (Rachel/Adam/Antoni/Domi/Josh).
- `backend/app/services/confidence_coach.py` — `analyse_recording()` is the orchestrator. It:
  1. Either uses the `transcript_override` (browser ASR) or transcribes via Whisper.
  2. Counts fillers via a compiled regex over `["um+","uh+","like","actually","basically","literally","you know","i mean",…]` (DMS Unit III — string matching as formal language).
  3. Computes WPM = `words / (duration_seconds/60)`.
  4. Runs `analyse_clarity()` which calls Claude Haiku with a strict JSON protocol asking for `{clarity_score, headline, strengths[], improvements[], recommended_drill}`. Falls back to a word-count heuristic when Claude fails (`<15 → 20`, `<50 → 55`, else `70`).
  5. Composes `_weighted_overall()` with `WEIGHTS = {eye:.25, posture:.25, clarity:.20, pace:.15, filler:.15}`. Missing metrics are dropped and remaining weights are re-normalised so the score still adds to 100.
- `backend/app/services/mock_interview.py` — Added `voice_turn(db, user, session_id, audio_bytes, transcript_override)` and `VoiceTurnResult` dataclass. The voice turn delegates straight to the existing `student_turn()` for scoring + state advancement, then best-effort calls `speech.synthesize_and_save(round_number=current_round)` to TTS the assistant reply. Returns `transcribed_text`, `assistant_audio_url` (or None), and `assistant_voice_id` so the frontend can play the audio without re-fetching.

**API routes:**
- `POST /api/v1/confidence/sessions` (multipart: audio + prompt + duration_seconds + eye_contact_pct + posture_pct + **browser_transcript** optional) — runs the analyser, persists a `ConfidenceSession`, awards XP via `xp.award_xp(CONFIDENCE_SESSION, bonus_multiplier=0.5+overall/100)`.
- `GET /api/v1/confidence/sessions/me` — timeline (oldest → newest), latest session, and a rotating list of 8 next prompts (`offset = len(rows) % 8`).
- `GET /api/v1/confidence/sessions/{id}` — single fetch.
- `POST /api/v1/interviews/{id}/voice` (multipart: audio + **browser_transcript** optional) — voice turn endpoint that returns the updated session, the transcribed text, and the assistant audio URL.
- `GET /api/v1/interviews/voice/capabilities` — `{asr_available, tts_available, voice_by_round}` so the frontend can show users exactly which path is live.

**Schemas:** `backend/app/schemas/confidence.py` (`ConfidenceSessionCreate/Response`, `ConfidenceMetric`, `ConfidenceTimelineResponse`) and additions to `backend/app/schemas/mock_interview.py` (`InterviewVoiceTurnResponse`, `VoiceCapabilitiesResponse`).

**Static-files mount:** `backend/app/main.py` mounts `backend/uploads/audio/` at `/audio` so generated MP3s stream straight from FastAPI. Frontend builds the URL via `API_BASE_URL.replace(/\/api\/v\d+\/?$/,'')`.

**Frontend hooks (new):**
- `frontend/src/hooks/useMediaRecorder.ts` — `MediaRecorder` wrapper with mime-type negotiation (`video/webm;codecs=vp9,opus` or `audio/webm;codecs=opus`), elapsed timer (250ms tick), `getUserMedia` lifecycle, and unmount cleanup that releases the mic/camera tracks (so the OS indicator turns off). `stop()` resolves to `{blob, durationSeconds, mimeType}`.
- `frontend/src/hooks/useBrowserSpeechRecognition.ts` — Web Speech API wrapper using `webkitSpeechRecognition`. Declares minimal TS types for the non-standard API, accumulates final segments into `finalBufferRef`, exposes interim results, and silently ignores benign `no-speech`/`aborted` errors. **This is the key cost saver on the input side** — it lets the demo run with a real, accurate transcript without ever calling Whisper, which is critical because the dev `.env` has no OpenAI key.
- `frontend/src/hooks/useBrowserSpeechSynthesis.ts` — Web Speech Synthesis API wrapper around `window.speechSynthesis`. Listens for `voiceschanged` (Chrome loads voices async) and auto-picks the best English voice from a priority list (Google US English → Microsoft Aria/Guy/David → macOS Samantha/Alex/Daniel → any en-* voice). Cancels in-flight utterances on every new `speak()` and on unmount. **This is the key cost saver on the output side** — it gives the demo a voice on the *output* side too when the dev `.env` has no `ELEVENLABS_API_KEY`. Quality is robotic vs. ElevenLabs but ships in every modern browser, so the voice mode always feels alive instead of awkwardly silent.

**Frontend types/api:**
- `frontend/src/types/confidence.ts` — `ConfidenceSessionResponse`, `ConfidenceMetric`, `ConfidenceTimelineResponse`, `ConfidenceSubmitForm`. `detailed_feedback` typed with optional `headline`, `strengths[]`, `improvements[]`, `recommended_drill`, `metrics{}`.
- `frontend/src/types/interview.ts` — `InterviewVoiceTurnResponse`, `VoiceCapabilitiesResponse` additions.
- `frontend/src/api/client.ts` — `confidenceApi.{timeline, get, submit}` with multipart `submit()` that conditionally appends `browser_transcript`. `interviewsApi.voiceCapabilities()` and `interviewsApi.sendVoice({sessionId, audioBlob, browserTranscript})`.

**Frontend pages wired:**
- `frontend/src/pages/student/ConfidenceCoachPage.tsx` — full rewrite from the static prototype:
    - Live camera preview via `useMediaRecorder({video: true})` — the `<video>` element binds to `recorder.stream` while recording, then switches to a `<video src={URL.createObjectURL(blob)} controls>` playback element afterwards.
    - Live transcript box that streams `speech.transcript + speech.interim` while the user speaks.
    - One-tap **Start Recording** → records → **Stop & Score** → auto-submits the blob + browser transcript via `confidenceApi.submit()`. Shows a "Scoring with Claude…" hint while waiting.
    - 6 metric cards driven by the latest server response: Eye Contact, Posture, Filler Words (variant: success ≤3 / warning ≤8 / danger), Speaking Pace (warning <110 / >175), Clarity, Overall Confidence.
    - Headline banner from Claude in a green check box. "What you said" card with the server-confirmed transcript.
    - Strengths + Improvements two-column cards.
    - **Growth Timeline** Recharts `LineChart` with three series (overall = purple `#7C3AED`, eye contact = blue `#2563EB`, clarity = green `#2EA043`), themed with CSS variables for grid/axis/tooltip so it matches the active theme. `ResponsiveContainer` for fluid sizing. Refresh button reloads the timeline.
    - Recommended Drills section that shows Claude's `recommended_drill` (highlighted at the top) followed by 3 evergreen fallback drills.
    - 8 rotating prompts pulled from `timeline.next_prompts[0]` so each new session starts with a fresh question.
- `frontend/src/pages/student/MockInterviewPage.tsx` — voice mode toggle live:
    - `mode` is now stateful (was a no-op `useState`). Voice button enables when either `speech.supported` (Chrome) OR `capabilities.asr_available` (server Whisper) is true. Tooltip explains both paths. Capabilities banner shows `Browser ASR ready · Browser voice fallback` (or `· ElevenLabs voices on` when the prod key is loaded) so the user knows exactly which voices to expect.
    - Calls `interviewsApi.voiceCapabilities()` on mount and stores the result.
    - In voice mode, the chat input area swaps to a "Tap to speak" mic button. Recording state shows `Stop & Send (M:SS)` with a live elapsed timer. Live transcript appears in a small card above the button while speaking, and a "You said" replay card persists after stop.
    - On stop: calls `interviewsApi.sendVoice()` with the blob + browser transcript, updates the session, and the new `useEffect` either auto-plays the ElevenLabs MP3 (when `assistant_audio_url` is set) **or** falls back to `synth.speak(lastAssistantText)` so the dev laptop demo also has a real spoken reply. The "Replay AI voice" button is wired to whichever path is active and shows "Speaking…" while the browser TTS is talking.
    - Starting a new turn calls `synth.cancel()` so the AI voice never overlaps the user's mic. Same on `End Interview` and `Try Again`.
    - Text mode is fully preserved — the existing flow is gated by `mode === 'text'`.

**Graceful degradation strategy** (because the dev `.env` has neither `OPENAI_API_KEY` nor `ELEVENLABS_API_KEY`):
1. `confidence_coach.analyse_recording()` and `mock_interview.voice_turn()` both accept `transcript_override`. The frontend sends the browser-side Web Speech API result so the server never needs to call Whisper. **(input side covered)**
2. `speech.is_tts_available()` returns False when ElevenLabs is missing → `voice_turn()` skips the TTS call and the response has `assistant_audio_url: null`. The frontend then auto-falls-back to `useBrowserSpeechSynthesis().speak()`, which uses `window.speechSynthesis` to speak the assistant's text reply with the best installed system voice. **(output side covered)**
3. The `/voice/capabilities` endpoint surfaces both flags so the UI can label the mode honestly: `Browser ASR ready · Browser voice fallback` instead of pretending ElevenLabs is on.
4. For the **final demo only**, drop a real `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` into the prod `.env` and the same code path lights up Whisper + 5 ElevenLabs voices automatically — zero refactor needed. The browser-TTS hook stays as a permanent safety net in case ElevenLabs rate-limits us mid-demo.

**XP wiring:** `XPEventType.CONFIDENCE_SESSION` was added in Phase 18. Each confidence submission awards XP scaled by `0.5 + overall/100` (so a perfect 100% gives 1.5×). The student's level visibly ticked from **Lv. 2 → Lv. 3** in the test session below.

**Concepts wired into the syllabus:**
- **DMS Unit III — String matching / formal language**: filler word regex over a fixed pattern set
- **DAA — Heuristic / weighted composite**: missing-metric renormalisation in `_weighted_overall()`
- **CN — Reliable degradation**: best-effort vendor calls with sentinel returns instead of exceptions
- **DMS — Recurrence / state**: the 8-prompt rotation `offset = len(rows) % 8`

**Browser E2E (verified):**
- **GET /api/v1/interviews/voice/capabilities** → `{asr_available: false, tts_available: false, voice_by_round: {1..5: <real ElevenLabs IDs>}}`. Confirms graceful degradation when keys are missing.
- **MockInterviewPage setup screen** — Voice button enables, capabilities banner correctly reads "Browser ASR ready · TTS off (text replies only)". Clicking Voice swaps the variant from secondary → primary. Starting an interview transitions to the chat view with a "Tap to speak" mic button instead of a text input. First interviewer message rendered: *"Okay, let's get straight to it. We're interviewing for Google. In 60 seconds or less: who are you, and why should we even consider you?"*
- **POST /api/v1/interviews/{id}/voice** with a browser_transcript override — backend transcribed the override directly, Claude Haiku scored the answer **7/10** with reason *"Strong technical initiative and shipping velocity, but lacks depth on teamwork, conflict resolution, and self-awareness—core HR signals."* and generated a sharp follow-up *"Impressive pace on CampusIQ. But tell me: of those 26 features, which one required you to depend on someone else to ship it?"* — full state machine intact.
- **POST /api/v1/confidence/sessions** with a 99-word, 38-second STAR-style transcript containing 4 fillers (`um, uh, you know, you know`):
    - Filler count: **4** ✓
    - Speaking pace: **156 WPM** (in the ideal 125-170 band → `pace_score: 100`) ✓
    - Eye contact: 78%, Posture: 82% (from input)
    - Claude clarity score: **72**
    - Headline: *"Solid STAR structure with concrete technical details, but hedging language and filler words undermine confidence."*
    - 2 strengths (94% test pass rate, infinite-loop-on-left-recursion specificity)
    - 2 improvements (remove fillers, strengthen the Action verb)
    - Recommended drill: **"Confidence Cadence"**
    - Composite overall: **81.37** ✓
- **ConfidenceCoachPage** post-submission render — all 6 metric cards populated with the real values, headline banner displayed, "What you said" card shows the full transcript, Strengths/Improvements lists rendered, **Recharts LineChart** draws three coloured dots (overall purple, eye blue, clarity green) at the S1 axis position, and the recommended-drill card pins "Confidence Cadence" above the 3 default drills. Top-right level indicator ticked **Lv. 2 → Lv. 3** confirming XP awarded.

**Build:** `tsc --noEmit` clean, `vite build` succeeds in **930ms** (1054 KB JS / 37 KB CSS, gzipped 300 KB / 8.46 KB) — the new browser-TTS hook adds ~1 KB gzipped.

**Demo Notes:** Use Haiku for all dev. Switch to **Opus for the single final demo** by setting `ANTHROPIC_MODEL=claude-opus-4-6` in `.env`. ElevenLabs starter plan = ~7-8 full interviews per month, so the actual `ELEVENLABS_API_KEY` only goes into the prod `.env` on demo day — until then, the frontend uses the browser's free `speechSynthesis` API (Chrome/Safari/Edge native voices) so the demo always has a real spoken AI reply. If ElevenLabs goes down or rate-limits us mid-demo, the same fallback kicks in automatically — no manual intervention needed.

---

## Phase 21 — Boss Battles + TCP Notifications + Recruiter Profile + Final Polish (F10, F15, F24)

**Complexity:** High

**Goal:** Final features, security audit, performance optimization, demo prep.

**Files to create:**
- `backend/app/services/interview_simulator.py` — 5-round full simulator (uses state machine from Phase 16)
- `backend/app/services/boss_battle.py` — Monthly event, 80th percentile badge
- `backend/app/services/notifications.py` — TCP-style seq/ack/retry with exponential backoff
- `backend/app/api/routes/notifications.py` — WebSocket endpoint
- Frontend: Recruiter Profile page (public)
- Mobile responsive pass on all pages
- Security: rate limiting, input validation
- Loading states, error boundaries
- Switch Claude to Opus for demo

**CN Concepts:** TCP seq/ack/retry (Unit V), congestion control backoff (Unit III)

**Verification:** Full demo run-through matches the 10-minute demo script.

---

## Demo Day Configuration

| Component | Dev/Testing | Final Demo |
|-----------|------------|------------|
| Claude model | Haiku | **Opus** |
| Whisper (input) | Browser Web Speech API (free) | **OpenAI Whisper** (more accurate) |
| TTS (output) | Browser `speechSynthesis` (free, robotic) | **ElevenLabs 5 voices** (cinematic) |
| Interview rounds | Voice mode works end-to-end | **Full voice, all 5 ElevenLabs personas** |
| Fallback if ElevenLabs rate-limits | n/a | Browser TTS auto-takes over (zero downtime) |
| Database | Supabase | Supabase (same) |
| Skill graph | Live data | Pre-seeded with good demo data |

---

## The Two Flagship Features

### 1. Adaptive Learning Engine (Research Paper)
**Phase 15** — combines Dijkstra + Knapsack + dynamic edge weights based on quiz performance. Becomes the publishable research piece. Evaluation done on real classmates over 2 weeks.

### 2. Voice Interview Simulator (Demo Showstopper)
**Phase 20** — full 5-round interview with Whisper + Claude Opus + ElevenLabs voices. Each round has a different voice persona. Final debrief with per-round scores and predicted hire probability.

---

## Subject Mapping (RVCE 4th Sem CS)

**DAA — Design and Analysis of Algorithms (CD343AI):**
- Heap/priority queue (Unit III) → Phase 12 task feed
- Greedy algorithms (Unit IV) → Phase 11 quiz adaptive difficulty
- Huffman coding (Unit IV) → Phase 7 document compression
- Dijkstra's shortest path (Unit IV) → Phase 15 learning path
- Knapsack DP (Unit IV) → Phase 15 study optimizer
- Prim's MST (Unit IV) → Phase 15 prerequisite chains
- BFS/DFS, topological sort (Unit II) → Phase 18 skill tree
- Backtracking, branch-and-bound (Unit V) → Phase 19 schedule generator
- String matching (Unit III) → Phase 20 filler word detection
- Divide and conquer (Unit II) → Phase 7 document chunking

**CN — Computer Networks (CY245AT):**
- TCP reliability, seq/ack/retry (Unit V) → Phase 21 notifications
- Congestion control, backoff (Unit III) → Phase 21 notifications
- Routing algorithms, distance vector (Unit II) → Phase 15 Dijkstra
- HTTP/HTTPS, REST APIs (Unit V) → Entire backend
- JWT, TLS, CORS, RLS → Phase 5 auth + security

**DMS — Discrete Mathematical Structures (CS241AT):**
- Recurrence relations (Unit I) → Phase 12 XP/streak
- Inclusion-exclusion (Unit I) → Phase 19 analytics
- Boolean logic (Unit II) → Phase 11 quiz weak area detection
- Equivalence relations, partial orders (Unit III) → Phase 18 tier system
- Function composition (Unit III) → Phase 18 CampusIQ score
- Hamming distance (Unit IV) → Phase 19 similarity checker
- Graph coloring, chromatic number (Unit V) → Phase 19 quiz scheduling
- Spanning trees, MST (Unit V) → Phase 15 prerequisite chains
- Set theory operations (Unit I) → Phase 17 community tag search

---

## Execution Rules

- Each phase = one conversation/session with Claude Code
- Test/verify before moving to next phase
- Commit after each phase
- Phases 1-13 = V1 (deployable Learn Mode)
- Phases 14-19 = V2 (Place Mode added, competition-ready)
- Phases 20-21 = V3 (final voice + polish, submission ready)
