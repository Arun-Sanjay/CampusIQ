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
- **Student (`/student/*`):** dashboard, `notes`, `college-gpt`, `quizzes` (+ `/:quizId/take`, `/:quizId/result/:attemptId`), `community`, `schedule`, `resume`, `skill-gap`, `interview`, `confidence`, `jobs`, `placement-chat`, `crash-mode`, `skill-tree`, `leaderboard`, `profile`, `boss-battles`, and **coding**: `coding`, `coding/pattern/:slug`, `coding/:slug`.
- **Teacher (`/teacher/*`):** dashboard, `subjects`, `roster` (enrollment), `documents`, `quizzes`, `quiz-scheduling`, `announcements`, `analytics`, `students`, `similarity`.
- **Admin (`/admin/*`):** dashboard, `college-docs`, `knowledge` (Knowledge Editor), `users`, `skill-analytics`, `notifications` (TCP delivery dashboard).

Gotchas: `coding/pattern/:slug` is declared **before** `coding/:slug` so the literal `pattern` segment wins. The resume print view (`/student/resume/print`) sits **outside** `AppLayout` so the whole page is the printable resume — don't wrap it in the sidebar shell. There is **no 404/catch-all route**.

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

`src/api/client.ts` is one big file (~700 lines), one method per backend endpoint, grouped into exported objects. Conventions:

- Base URL: `import.meta.env.VITE_API_BASE_URL` (code default `http://localhost:8000/api/v1`; the `.env`/`.env.example` use `127.0.0.1`). Exported as `API_BASE_URL`; the notifications WebSocket URL derives from it.
- Auth header pulled from `useAuthStore.getState().token` per request. `FormData` bodies pass through untouched (browser sets the multipart boundary) — used by all uploads + voice/audio.
- Errors throw `ApiError(status, detail, body)` — UI catches and surfaces `err.detail`.
- **Streaming:** `chatApi.streamMessage` uses raw `fetch` + `response.body.getReader()` + `TextDecoder`, delivering deltas to an `onChunk` callback (supports `AbortSignal`). Match this pattern for new streaming surfaces.
- All response shapes are typed in `src/types/` (one file per domain, barrel-exported from `src/types/index.ts`; each mirrors the matching `backend/app/schemas/*.py`). Add the type first, then the client method, then call it from the page. **Don't `fetch` directly from a component.**

Method groups (23): `authApi`, `enrollmentApi`, `subjectsApi`, `documentsApi`, `collegeDocumentsApi`, `knowledgeApi`, `chatApi`, `quizzesApi`, `dashboardApi`, `adminApi`, `announcementsApi`, `analyticsApi`, `bossBattlesApi`, `algorithmsApi`, `gamificationApi`, `publicProfileApi`, `jobsApi`, `communityApi`, `interviewsApi`, `confidenceApi`, `skillsApi`, `codingApi`, `resumeApi`.

## Component conventions

- **UI primitives:** `src/components/ui/` — `Button`, `Input`, `TextArea`, `Select`, `Card` (+ `CardHeader`, `CardTitle`, `CardLabel`), `Badge`, `Avatar`, `Modal`, `ProgressBar`, re-exported from `src/components/ui/index.ts`. `Disclosure` also lives here but is **not** in the barrel — import it directly. Check here before creating a new primitive.
- **Layout:** `src/components/layout/` — `AppLayout`, `Sidebar`, `TopBar`, `PageTransition`, `NotificationToasts`, `QuizGenerationChips`. The shell for all authenticated pages.
- **Dashboard / chat:** `src/components/dashboard/` (`StatCard`, `ScoreRing`, `TaskFeed`, `ActivityFeed`); `src/components/chat/` (`ChatLayout`, `ChatMessage`, `ChatInput`, `ModeSelector`, `markdownComponents`). Reuse these on new dashboard/chat pages.
- **Structured chat cards:** `src/components/chat/cards/` parses fenced blocks out of assistant markdown (` ```solved `, ` ```step `, etc.) via `FenceDispatcher` into `SolvedCard` / `UnsolvedCard` / `StepCard` / `AnswerBox` / `HintReveal` / `MermaidDiagram`. The Note Assistant, DSA Coach, and CollegeGPT all render through this — match it for new AI surfaces.
- **Coding platform:** `src/components/coding/` — `CodeEditor` (**lazy-loads `@monaco-editor/react`** so its ~3 MB chunk only ships on coding pages), `pyodideRunner.ts` (Pyodide WASM Python runner, exports `TestResult`), `TestResultPanel`, `ProblemDescription`, `DifficultyBadge`, `CoachChat`.
- **Knowledge Editor (admin):** `src/components/admin/` — `ChunkEditorList`, `ChunkCard`, `EditProposalCard` (word-diff via `src/utils/wordDiff.ts`), `QuickUpdateBar`, `KnowledgeChatDrawer`.
- **Errors:** `src/components/ErrorBoundary.tsx` wraps the routed page `<Outlet>` **inside `AppLayout`** (keyed `scope={location.pathname}`), so each authenticated page is error-isolated. Public pages (landing/login/signup/recruiter) are not wrapped. Keep new error UIs consistent with it.

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

The coding platform runs Python **entirely in the browser**: `CodeEditor` lazy-loads Monaco, and `pyodideRunner.ts` loads the Pyodide WASM runtime to execute submissions against test cases. Both are heavy — keep them lazy and off the critical path of non-coding pages. In tests, **mock `pyodide`** (`loadPyodide`) so jsdom never fetches the WASM bundle (see `coding-components.test.tsx`).

## Speech / confidence hooks

- `useBrowserSpeechRecognition` / `useBrowserSpeechSynthesis` — the free browser fallbacks for ASR/TTS when ElevenLabs keys are absent.
- `useMediaRecorder` — mic+camera capture (default `audio/webm;codecs=opus`) for voice interview + confidence recordings.
- `useConfidenceTracker` — eye-contact/posture scoring via **MediaPipe Tasks Vision** (`FaceLandmarker` + `PoseLandmarker`), lazy-loading WASM/models from CDN.

## lucide-react gotcha

Locked at `^1.7.0`. Verify an icon exists before importing — `Github` is **not** in this version; use `Code` or `GitBranch`. When in doubt:

```bash
node -e "const l = require('lucide-react'); console.log(typeof l.Github, typeof l.Code)"
```

## Markdown rendering

Assistant-side chat messages render through `react-markdown` + `remark-gfm` with shared overrides in `chat/markdownComponents.tsx`, plus the structured fence-card system above. When you build a new chat surface, render the same way so code blocks, lists, tables, and structured cards match the existing AI surfaces. Mermaid diagrams render lazily and skip while a message is still streaming.

## Tests

`src/__tests__/` — vitest + `@testing-library/react` (jsdom). Four real test files now (`api-client.test.ts`, `coding-components.test.tsx`, `note-assistant-cards.test.tsx`, `wordDiff.test.ts`) + `setup.ts`. Heavy deps are mocked (`pyodide`, `mermaid`). Tests use `fireEvent` — `@testing-library/user-event` is not installed. (`scripts/dress_rehearsal.spec.ts` is a Playwright demo spec, outside the vitest glob.)

## When verifying UI changes

The user runs the dev servers themselves; don't `npm run dev` in a foreground tool call. Either ask them to refresh, or use the Playwright MCP (`mcp__playwright__browser_navigate`, `browser_take_screenshot`) against `http://localhost:5173` if it's already running. Watch the browser console — a backend 5xx often surfaces as a CORS error there, because the error response can't carry CORS headers.
