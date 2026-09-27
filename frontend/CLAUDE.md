# Frontend — Claude rules

Vite 8 + React 19 + TypeScript 6 SPA. Read `../CLAUDE.md` first for project-wide rules (cost rule, git etiquette, locked decisions). This file covers frontend-specific conventions.

## Run / verify

```bash
cd frontend
npm run dev          # http://localhost:5173 (use localhost, not 127.0.0.1 — Vite binds IPv6)
npm run typecheck    # tsc --noEmit
npm run lint         # ESLint flat config
npm test             # vitest run (single pass, not watch)
npm run build        # production bundle into dist/
```

If `./node_modules/.bin/tsc` is missing, run `npm install` first — `typescript@^6.0.2` is in `package.json` but isn't always present locally. Tailwind is **v3** (`^3.4`, with `postcss` + `autoprefixer`), not v4 — don't reach for v4 syntax.

## TypeScript / lint posture

`tsconfig.json` is `strict: true` but `noUnusedLocals` / `noUnusedParameters` are **off** — don't waste a turn deleting unused imports unless they trip a lint error. `allowJs: true` (a few legacy `.js`/`.jsx` files load; most pages are `.tsx`). Path alias `@/*` → `./src/*` is configured but the codebase mostly uses relative imports — match the surrounding file. **ESLint only lints `.js`/`.jsx`** (the flat config doesn't match `.ts`/`.tsx`), so TSX correctness rides on `tsc --noEmit`, not ESLint. CI runs typecheck → lint → test → build, in that order; all four must pass for green.

## Routing

`src/routes/AppRouter.tsx` is the single source of truth (`createBrowserRouter`). Wrappers: `ProtectedRoute` (role-gated — calls `authApi.me()` on load to validate the token), `PublicOnlyRoute` (bounces authed users off `/login` `/signup`), `AppLayout` (sidebar shell). When you add a route, also update `src/components/layout/Sidebar.tsx` so it appears in the role's nav.

- **Public:** `/` (Landing), `/p/:studentId` (public recruiter profile, no auth), `/login`, `/signup`.
- **Student (`/student/*`):** dashboard, `notes`, **coding** (`coding`, `coding/pattern/:slug`, `coding/:slug`), `college-gpt`, `quizzes` (+ `/:quizId/take`, **`/:quizId/proctored`**, `/:quizId/result/:attemptId`), `community`, `schedule`, `resume`, `skill-gap`, `interview`, `confidence`, `jobs`, `placement-chat`, `crash-mode`, `skill-tree`, `leaderboard`, `profile`, **`grades`** (transcript), `boss-battles`.
- **Teacher (`/teacher/*`):** dashboard, `subjects`, `roster` (enrollment / "My Students"), `documents`, `quizzes`, **`grading`** + **`grading/:examId`** (AI Auto-Grader workspace), `announcements`, `quiz-scheduling`, `analytics`, **`grades`** (class grades dashboard), `students`, `similarity`.
- **Admin (`/admin/*`):** dashboard, `college-docs`, `knowledge` (Knowledge Editor), `users`, `skill-analytics`, `notifications` (TCP delivery dashboard).

Gotchas: `coding/pattern/:slug` is declared **before** `coding/:slug` so the literal `pattern` segment wins — load-bearing ordering. A test-mode quiz routes to `/:quizId/proctored` (`ProctoredQuizPage`), a practice quiz to `/:quizId/take` (`QuizTakingPage`); both share the result route. The resume print view (`/student/resume/print`) sits **outside** `AppLayout` so the whole page is the printable resume — don't wrap it in the sidebar shell. There is **no 404/catch-all route**.

## State

- **Auth:** `src/store/authStore.ts` — Zustand + `persist`, localStorage key `campusiq-auth`, persists only `{user, token}`. The API client reads the token directly from this store per request; any non-auth `401` triggers `logout()`.
- **Theme:** `src/hooks/useTheme.ts` (a Zustand store that lives under `hooks/`, not `store/`), localStorage key `campusiq-theme`. Three themes: `nebula` (default), `light`, `dark`. Legacy `premium`/`aurora`/`luxury` are stripped on load.
- **Notifications:** `src/store/notificationStore.ts` — in-memory toast stack (caps at 5), fed by `useNotificationsSocket`.
- **Quiz generation:** `src/store/quizGenerationStore.ts` — in-memory; tracks in-flight AI quiz generations so the floating progress chips survive navigation away from `/teacher/quizzes`.

Everything else is local component state. **No React Query / SWR / Redux.**

## Theming rule (hard rule)

Always use CSS variables from `src/index.css`:

- Backgrounds: `var(--bg-primary | --bg-secondary | --bg-tertiary | --bg-elevated | --bg-sidebar)`
- Text: `var(--text-primary | --text-secondary | --text-tertiary | --text-inverted)`
- Borders: `var(--border-default | --border-subtle | --border-strong)`
- Inputs: `var(--input-bg)`; Shadows: `var(--shadow-card | --shadow-card-hover | --shadow-elevated)`
- Glass / glow: `var(--glass-bg | --glass-border | --glow-color)`; Accent: `var(--gradient-accent)`

Hardcoded hex breaks the theme switcher. Fixed-color Tailwind utilities (`bg-white`, `text-zinc-500`) are also off-limits in component styling — use `style={{ background: 'var(--bg-elevated)' }}` or a Tailwind utility that points at the variable. **Exception:** the marketing landing page (`src/pages/marketing/`, `src/pages/auth/LandingPage.tsx`) has its own `landing.css` with hard-coded brand colors because the Nebula theme mirrors it.

## API client

`src/api/client.ts` is one big file, one method per backend endpoint, grouped into exported objects. Conventions:

- Base URL: `import.meta.env.VITE_API_BASE_URL` (code default `http://localhost:8000/api/v1`; the `.env`/`.env.example` use `127.0.0.1`). Exported as `API_BASE_URL`; the notifications WebSocket URL derives from it.
- Auth header pulled from `useAuthStore.getState().token` per request. `FormData` bodies pass through untouched (browser sets the multipart boundary) — used by all uploads + voice/audio + answer-sheet scans.
- Errors throw `ApiError(status, detail, body)` — UI catches and surfaces `err.detail`.
- **Streaming:** `chatApi.streamMessage` uses raw `fetch` + `response.body.getReader()` + `TextDecoder`, delivering deltas to an `onChunk` callback (supports `AbortSignal`). Match this pattern for new streaming surfaces.
- **Authed images:** `<img>` can't send an `Authorization` header, so private images (answer-sheet pages) are fetched as a blob via `AuthedImage` (see below); `gradingApi.pageUrl(sheetId, idx)` returns the absolute URL it loads.
- All response shapes are typed in `src/types/` (one file per domain, barrel-exported from `src/types/index.ts`; each mirrors the matching `backend/app/schemas/*.py`). Add the type first, then the client method, then call it from the page. **Don't `fetch` directly from a component.**

Method groups (25): `authApi`, `enrollmentApi`, `subjectsApi`, **`gradingApi`**, **`gradesApi`**, `chatApi`, `documentsApi`, `collegeDocumentsApi`, `knowledgeApi`, `quizzesApi`, `dashboardApi`, `adminApi`, `announcementsApi`, `analyticsApi`, `bossBattlesApi`, `algorithmsApi`, `gamificationApi`, `publicProfileApi`, `jobsApi`, `communityApi`, `interviewsApi`, `confidenceApi`, `skillsApi`, `codingApi`, `resumeApi`.

## Component conventions

- **UI primitives:** `src/components/ui/` — `Button`, `Input`, `TextArea`, `Select`, `Card` (+ `CardHeader`, `CardTitle`, `CardLabel`), `Badge`, `Avatar`, `Modal`, `ProgressBar`, re-exported from `src/components/ui/index.ts`. `Disclosure` also lives here but is **not** in the barrel — import it directly. Check here before creating a new primitive.
- **Layout:** `src/components/layout/` — `AppLayout`, `Sidebar`, `TopBar`, `PageTransition`, `NotificationToasts`, `QuizGenerationChips`. The shell for all authenticated pages. Sidebar nav is grouped per role (student: LEARN MODE / PLACE MODE / PROFILE; teacher: DASHBOARD / CONTENT / ANALYTICS; admin: DASHBOARD / ANALYTICS).
- **Dashboard / chat:** `src/components/dashboard/` (`StatCard`, `ScoreRing`, `TaskFeed`, `ActivityFeed`); `src/components/chat/` (`ChatLayout`, `ChatMessage`, `ChatInput`, `ModeSelector`, `markdownComponents`). Reuse these on new dashboard/chat pages.
- **Structured chat cards:** `src/components/chat/cards/` parses fenced blocks out of assistant markdown (` ```solved `, ` ```step `, etc.) via `FenceDispatcher` into `SolvedCard` / `UnsolvedCard` / `StepCard` / `AnswerBox` / `HintReveal` / `MermaidDiagram`. The Note Assistant, DSA Coach, and CollegeGPT all render through this — match it for new AI surfaces.
- **Coding platform:** `src/components/coding/` — `CodeEditor` (**lazy-loads `@monaco-editor/react`** so its ~3 MB chunk only ships on coding pages), `pyodideRunner.ts` (Pyodide WASM Python runner pinned to v0.29.4, exports `TestResult`), `TestResultPanel`, `ProblemDescription`, `DifficultyBadge`, `CoachChat`.
- **Knowledge Editor (admin):** `src/components/admin/` — `ChunkEditorList`, `ChunkCard`, `EditProposalCard` (word-diff via `src/utils/wordDiff.ts`), `QuickUpdateBar`, `KnowledgeChatDrawer`.
- **`AuthedImage`:** `src/components/AuthedImage.tsx` — fetches a private image as a blob with the bearer token from `authStore`, renders it via an object URL (revoked on unmount), and falls back to "image unavailable". Used **only** by the grading workspace to display answer-sheet page images served behind the authenticated `/grading/answer-sheets/{id}/pages/{idx}` route.
- **Errors:** `src/components/ErrorBoundary.tsx` wraps the routed page `<Outlet>` **inside `AppLayout`** (keyed `scope={location.pathname}`), so each authenticated page is error-isolated. Public pages (landing/login/signup/recruiter) are not wrapped. Keep new error UIs consistent with it.

## Coding pages (pattern-first)

`CodingProblemsPage` (`/student/coding`) is now a **pattern grid**, not a flat problem list: a stats banner, a Core/Advanced track toggle, and patterns grouped by tier as `PatternBox` cards with per-pattern progress. Each box links to `CodingPatternPage` (`/student/coding/pattern/:slug`) — a pattern header + an ordered problem list. A problem row links to `CodingProblemPage` (`/student/coding/:slug`). Only the 5 in-app-judge problems (`source==='seed_inapp'` with starter code → `has_editor`) show the Monaco/Pyodide editor; the other ~371 curriculum problems hide the editor and offer Coach + an Open-on-LeetCode link instead. Honor `has_editor` when touching the problem detail page.

## Grading workspace (teacher) + grades

- `GradingExamsPage` (`/teacher/grading`, "AI Auto-Grader") lists exams + a create modal. `GradingWorkspacePage` (`/teacher/grading/:examId`) is a 4-tab workspace (Scheme / Answer Sheets / Review Queue / CO Attainment) for upload → confirm scheme → match student → override grades → finalize; it **polls every ~3 s while parsing/grading** and renders answer-sheet pages via `AuthedImage` + `gradingApi.pageUrl`.
- `GradingDashboardPage` (`/teacher/grades`, "Class Grades") shows the class grade overview + CO attainment per subject.
- `GradesPage` (`/student/grades`, "My Grades") is the student's read-only transcript: CGPA hero, per-semester SGPA, per-subject CIE/SEE + letter grade + per-CO bars.

## Proctored quizzes (student)

`ProctoredQuizPage` (`/student/quizzes/:quizId/proctored`) is the test-mode flow (`QuizTakingPage` remains the unproctored practice flow; `QuizListPage` branches on `quiz.mode`). It adds a **preflight** phase (camera permission via `getUserMedia`, webcam preview, MediaPipe tracker start, rules screen), then a `running` phase that enters fullscreen, wires `useProctoring`, shows a **server-anchored countdown** (anchored to `started_at`/`server_now` with clock-skew correction), a live webcam thumbnail + face-detected badge, and per-question `co`/`marks` badges. It auto-submits on time-out or excessive violations, stashes the result in `sessionStorage`, and navigates to the shared result page. **No camera snapshots are captured or uploaded** — only event counters + a live MediaPipe face-presence signal.

## Animation pattern

Stagger + fade-up for dashboard-style pages:

```tsx
const stagger = { animate: { transition: { staggerChildren: 0.05 } } }
const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

<motion.div variants={stagger} initial="initial" animate="animate">
  <motion.div variants={fadeUp}>...</motion.div>
</motion.div>
```

Use sparingly on transactional pages (forms, taking a quiz) — only on overview / dashboard surfaces.

## Code editor + Pyodide (coding pages)

The coding platform runs Python **entirely in the browser**: `CodeEditor` lazy-loads Monaco, and `pyodideRunner.ts` loads the Pyodide WASM runtime (v0.29.4, from the jsDelivr CDN) to execute submissions against test cases. Both are heavy — keep them lazy and off the critical path of non-coding pages. In tests, **mock `pyodide`** (`loadPyodide`) so jsdom never fetches the WASM bundle (see `coding-components.test.tsx`).

## Speech / confidence / proctoring hooks

- `useBrowserSpeechRecognition` / `useBrowserSpeechSynthesis` — the free browser fallbacks for ASR/TTS when ElevenLabs keys are absent.
- `useMediaRecorder` — mic+camera capture (default `audio/webm;codecs=opus`) for voice interview + confidence recordings.
- `useConfidenceTracker` — eye-contact/posture scoring via **MediaPipe Tasks Vision** (`FaceLandmarker` + `PoseLandmarker`), lazy-loading WASM/models from CDN. Reused by `ProctoredQuizPage` for live face-presence.
- `useProctoring` — anti-cheat for proctored quizzes: monitors tab-switch/blur (`visibilitychange`), fullscreen exit, copy/paste/cut/contextmenu, and DevTools/print key combos (all blocked), maintains a server-anchored countdown, and auto-submits on time-out or when tab-switches hit `maxViolations` (default 6). It posts each event to `POST /quizzes/{id}/proctor-events` (fire-and-forget) and reports accumulated counters in the final submit body.

## lucide-react gotcha

Locked at `^1.7.0`. Verify an icon exists before importing — `Github` is **not** in this version; use `Code`/`Code2` or `GitBranch`. When in doubt:

```bash
node -e "const l = require('lucide-react'); console.log(typeof l.Github, typeof l.Code2)"
```

## Markdown rendering

Assistant-side chat messages render through `react-markdown` + `remark-gfm` with shared overrides in `chat/markdownComponents.tsx`, plus the structured fence-card system above. When you build a new chat surface, render the same way so code blocks, lists, tables, and structured cards match the existing AI surfaces. Mermaid diagrams render lazily and skip while a message is still streaming.

## Tests

`src/__tests__/` — vitest + `@testing-library/react` (jsdom). Four real test files (`api-client.test.ts`, `coding-components.test.tsx`, `note-assistant-cards.test.tsx`, `wordDiff.test.ts`) + `setup.ts`. Heavy deps are mocked (`pyodide`, `mermaid`). Tests use `fireEvent` — `@testing-library/user-event` is not installed. (`scripts/dress_rehearsal.spec.ts` is a Playwright demo spec, outside the vitest glob.) The grading/proctoring pages don't have unit tests yet — verify them in the browser.

## When verifying UI changes

The user runs the dev servers themselves; don't `npm run dev` in a foreground tool call. Either ask them to refresh, or use the Playwright MCP (`mcp__playwright__browser_navigate`, `browser_take_screenshot`) against `http://localhost:5173` if it's already running. Watch the browser console — a backend 5xx often surfaces as a CORS error there, because the error response can't carry CORS headers.


<!-- storage-cleanup-2026-08-26 -->
## ⚠️ Dependencies were removed to reclaim disk space (2026-08-26)

`node_modules` was deleted here during a disk cleanup — the drive had reached 99% full.
**No source code, lockfiles, or config were touched.** If you are picking this project
back up, reinstall before running or building anything:

- `.` → run `npm install`

The lockfile is intact, so the reinstall is byte-identical to what was removed.
Build output (`.next` / `target`) was cleared too and regenerates on the next build.
Full inventory: `~/STORAGE-CLEANUP-2026-08-26.md`
