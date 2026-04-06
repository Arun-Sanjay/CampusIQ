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
| 4 | ⏳ Pending | Database schema + backend foundation |
| 5 | ⏳ Pending | Authentication system |
| 6 | ⏳ Pending | Subject + document CRUD wiring |
| 7 | ⏳ Pending | Document processing + Huffman |
| 8 | ⏳ Pending | Embeddings + pgvector RAG foundation |
| 9 | ⏳ Pending | AI Note Assistant backend |
| 10 | ⏳ Pending | CollegeGPT backend |
| 11 | ⏳ Pending | Quiz Engine backend |
| 12 | ⏳ Pending | Dashboard + XP + Task Feed backend |
| 13 | ⏳ Pending | Announcements + analytics backend |
| 14 | ⏳ Pending | Resume Builder backend |
| 15 | ⏳ Pending | **Adaptive Learning Engine** (research paper core) |
| 16 | ⏳ Pending | Mock Interview text mode backend |
| 17 | ⏳ Pending | Placement Chatbot + Job Tracker + Community |
| 18 | ⏳ Pending | Full gamification + CampusIQ Score |
| 19 | ⏳ Pending | Algorithm features (Hamming, graph coloring, etc) |
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

## Phase 9 — AI Note Assistant Backend (F2)

**Complexity:** Medium-High

**Goal:** Full RAG chat with Claude, streaming responses, source citations.

**Files to create:**
- `backend/app/services/ai_chat.py` — Claude API integration, RAG prompt construction, streaming
- `backend/app/schemas/chat.py`
- `backend/app/services/chat.py` — Session and message persistence
- `backend/app/api/routes/chat.py` — POST /note-assistant (streaming), GET /sessions
- Wire up frontend Note Assistant page to real streaming API

**Verification:** Student asks question about uploaded PDF → streaming AI answer with source citations → conversation persists.

---

## Phase 10 — CollegeGPT Backend (F5)

**Complexity:** Low-Medium

**Goal:** Same RAG architecture, separate `college_document_chunks` table.

**Files to create:**
- `backend/app/services/college_document.py`
- `backend/app/api/routes/admin.py` — Admin upload college docs
- Add `POST /chat/college-gpt` endpoint
- Wire up frontend CollegeGPT page

**Verification:** Admin uploads handbook → student asks "attendance rule for labs?" → correct answer.

---

## Phase 11 — Quiz Engine Backend (F3)

**Complexity:** Medium-High

**Goal:** AI quiz generation, taking, scoring, adaptive difficulty.

**Files to create:**
- `backend/app/services/quiz_generator.py` — Claude generates structured JSON quizzes
- `backend/app/services/quiz.py` — CRUD, attempt scoring, adaptive difficulty (greedy tier selection), weak area detection
- `backend/app/api/routes/quizzes.py` — POST /generate, GET /quizzes, POST /attempt
- Wire up Quiz pages (list, taking, results)

**DAA Concept:** Greedy approach (Unit IV), Boolean threshold conditions (DMS Unit II)

**Verification:** Teacher generates quiz → publishes → student takes → score + adaptive difficulty + weak areas shown.

---

## Phase 12 — Student Dashboard + XP + Smart Task Feed (F13, F16, F20)

**Complexity:** Medium

**Goal:** XP system, basic CampusIQ score (academic only), heap-based task feed.

**Files to create:**
- `backend/app/services/xp.py` — Award XP, level calculation, streak tracking (recurrence relation)
- `backend/app/services/campus_iq_score.py` — Academic pillar (weighted quiz scores)
- `backend/app/services/task_feed.py` — Max-heap priority queue, urgency × impact
- `backend/app/api/routes/dashboard.py`
- Wire up Student Dashboard page

**DAA Concept:** Heap data structure, priority queue (Unit III). DMS: Recurrence relations (Unit I).

**Verification:** Quiz completed → XP awarded → score recalculates → task feed updates.

---

## Phase 13 — Announcements + Teacher Analytics

**Complexity:** Low-Medium

**Goal:** Teacher posts announcements, views class analytics.

**Files to create:**
- `backend/app/services/announcement.py`, `backend/app/services/analytics.py`
- `backend/app/api/routes/announcements.py`, `backend/app/api/routes/analytics.py`
- Wire up Teacher Analytics + Announcements pages

**Verification:** Teacher sees class performance data, posts announcement visible on student dashboard.

**═══ END OF V1 (Phases 1-13) — Learn Mode Foundation Complete ═══**

---

## Phase 14 — Resume Builder Backend (F6)

**Complexity:** Medium-High

**Goal:** Conversational AI resume builder, ATS scoring, GitHub import, PDF download.

**Files to create:**
- `backend/app/services/resume_builder.py` — Multi-turn Claude conversation, ATS scoring
- `backend/app/services/github_import.py` — GitHub public API integration
- `backend/app/api/routes/resume.py`
- Wire up Resume Builder page with React-PDF

**Verification:** AI conversation builds resume → PDF downloadable → ATS score against JD → GitHub repos imported.

---

## Phase 15 — Adaptive Learning Engine (F7, F17, F18, F22) ★ RESEARCH CORE

**Complexity:** High

**Goal:** Build the publishable research piece — dynamic skill graph + Dijkstra + Knapsack + Prim's MST.

**Files to create:**
- `backend/app/services/skill_graph.py` — Load weighted graph, seed 50+ skills + 20-30 company profiles
- `backend/app/services/dijkstra.py` — Dijkstra's shortest path with **dynamic edge weights** based on student quiz performance
- `backend/app/services/knapsack.py` — 0/1 Knapsack DP for time-constrained study optimization
- `backend/app/services/mst.py` — Prim's minimum spanning tree for prerequisite chains
- `backend/app/services/skill_gap.py` — Set difference + cosine similarity gap score
- `backend/app/api/routes/skills.py`
- **Data collection logging** — log all recommendations + actual student outcomes for paper evaluation

**DAA Concepts:**
- Dijkstra's shortest path (Unit IV)
- Dynamic programming, 0/1 Knapsack (Unit IV)
- Prim's MST (Unit IV)

**Research Paper Angle:** "A Dynamic Graph-Based Framework for Personalized Learning Path Optimization Under Time Constraints in Engineering Education"

**Evaluation Plan:** Split 30 classmates into control + test groups, compare quiz improvement after 2 weeks of using the optimizer.

**Verification:** Select "Google SWE" → Dijkstra path highlighted → set "15 hours" → Knapsack recalculates optimal subset → after quiz, weights update and path adapts.

---

## Phase 16 — Mock Interview Text Mode (F9)

**Complexity:** Medium

**Goal:** Python state machine, 4 personas, 5 rounds, scoring, debrief report.

**Files to create:**
- `backend/app/services/mock_interview.py` — State machine (no LangGraph), persona system prompts, scoring
- `backend/app/api/routes/interviews.py`
- Wire up Mock Interview page (all 3 views)

**Verification:** Full 5-round text interview works end-to-end with correct round transitions, scoring, and debrief.

---

## Phase 17 — Placement Chatbot + Jobs + Community (F4, F8, F12)

**Complexity:** Medium

**Goal:** Placement RAG, Kanban job tracker, peer doubt community with AI fallback.

**Files to create:**
- `backend/app/services/placement_chatbot.py` — Separate pgvector for placement experiences
- `backend/app/services/job_tracker.py` — CRUD, fit score calculation
- `backend/app/services/community.py` — Doubts, AI fallback after 10 min
- API routes for each
- Wire up the 3 frontend pages

**Verification:** Placement chatbot gives company-specific advice. Job tracker shows fit scores. Community AI answers stale questions.

---

## Phase 18 — Full Gamification + CampusIQ Score (F13, F14, F16)

**Complexity:** Medium

**Goal:** All 4 score pillars, skill tree, leaderboard, tier system.

**Files to create/expand:**
- `backend/app/services/xp.py` — All XP events, streak multiplier
- `backend/app/services/campus_iq_score.py` — All 4 pillars composed function
- `backend/app/services/leaderboard.py` — Top-K, tier assignment
- API routes
- Wire up Skill Tree, Leaderboard, Profile pages

**DAA Concepts:** Topological sort, BFS/DFS (Unit II). DMS: Equivalence relations, partial orders (Unit III).

**Verification:** All actions award XP → skill tree grows → score updates from 4 pillars → leaderboard ranks correctly → tier badges assigned.

---

## Phase 19 — Algorithm Showcase Features (F18, F21, F23, F25, F26)

**Complexity:** Medium-High

**Goal:** Implement remaining algorithm features for the syllabus.

**Files to create:**
- `backend/app/services/hamming.py` — Pairwise Hamming distance on quiz answer vectors
- `backend/app/services/inclusion_exclusion.py` — Set operations with inclusion-exclusion counting
- `backend/app/services/graph_coloring.py` — Greedy graph coloring for quiz scheduling
- `backend/app/services/backtracking_schedule.py` — Constraint satisfaction with branch-and-bound
- API routes
- Wire up Crash Mode, Similarity Checker, Skill Analytics, Schedule pages

**Concepts:**
- Hamming distance (DMS Unit IV)
- Graph coloring (DMS Unit V)
- Backtracking, branch-and-bound (DAA Unit V)
- Inclusion-exclusion principle (DMS Unit I)

**Verification:** Each algorithm produces correct output. Hamming flags similar submissions. Graph coloring assigns conflict-free quiz slots.

---

## Phase 20 — Voice Interview + Confidence Coach (F9 voice, F11) ★ DEMO SHOWSTOPPER

**Complexity:** High

**Goal:** Whisper transcription, Claude responses, ElevenLabs voices (5 different personas), MediaPipe Face Mesh + Pose for confidence.

**Files to create:**
- `backend/app/services/speech.py` — OpenAI Whisper API, ElevenLabs TTS
- `backend/app/services/confidence_coach.py` — Filler word detection, WPM, Claude STAR analysis
- API routes for voice and confidence
- Wire up Voice Interview + Confidence Coach pages with MediaRecorder + MediaPipe JS SDK

**ElevenLabs Voice Mapping:**
- HR: Rachel (warm)
- Technical: Adam (direct)
- System Design: Antoni (calm)
- Managerial: Arnold (authoritative)
- Negotiation: Domi (corporate)

**Demo Notes:** Use Haiku for all dev. Switch to **Opus for the single final demo**. ElevenLabs starter plan = ~7-8 full interviews per month, so save them for demo.

**Verification:** Voice loop works (speak → transcribe → AI → speech). Confidence coach scores eye contact, posture, filler words. Growth timeline charts improvement.

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
| ElevenLabs | Disabled (text mode) | **Enabled (5 voices)** |
| Interview rounds | Text only | **Full voice, all 5 rounds** |
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
