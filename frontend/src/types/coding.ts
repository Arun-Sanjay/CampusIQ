/**
 * Coding-practice platform types — mirrors backend/app/schemas/coding.py.
 */

export type CodingDifficulty = 'easy' | 'medium' | 'hard'
export type CodingLanguage = 'python' | 'cpp' | 'java'
export type CodingSubmissionStatus = 'passed' | 'failed' | 'error'
export type UserProblemStatus = 'solved' | 'attempted' | 'unsolved'

export interface ProblemExample {
  input: string
  output: string
  explanation?: string | null
}

export interface CodingTestCase {
  /** Positional arguments passed to the user's function. */
  input: unknown[]
  expected: unknown
}

export interface FunctionSignature {
  params: { name: string; type: string }[]
  returns?: string | null
}

export interface ProblemListItem {
  id: string
  slug: string
  title: string
  difficulty: CodingDifficulty
  topic_tags: string[]
  leetcode_url: string
  user_status: UserProblemStatus
}

export interface ProblemDetail {
  id: string
  slug: string
  title: string
  description: string
  difficulty: CodingDifficulty
  function_name: string
  function_signature: FunctionSignature
  examples: ProblemExample[]
  hints: string[]
  starter_code: Record<string, string>
  reference_solution: Record<string, string> | null
  visible_test_cases: CodingTestCase[]
  comparator: string
  topic_tags: string[]
  skill_node_names: string[]
  leetcode_url: string
  user_status: UserProblemStatus
  // Phase 2 curriculum context. `has_editor` is false for LeetCode-only
  // curriculum problems (the in-app Pyodide editor toggle is hidden for those).
  source: string
  has_editor: boolean
  lc_number: number | null
  priority: string | null
  is_premium: boolean
  pattern_slug: string | null
  pattern_name: string | null
}

export interface ProblemRunnerPayload {
  function_name: string
  visible_test_cases: CodingTestCase[]
  hidden_test_cases: CodingTestCase[]
  comparator: string
}

export interface SubmitRequest {
  language: CodingLanguage
  code: string
  status: CodingSubmissionStatus
  passed_count: number
  total_count: number
  runtime_ms?: number | null
  error_message?: string | null
}

export interface SubmissionResponse {
  id: string
  problem_id: string
  language: CodingLanguage
  code: string
  status: CodingSubmissionStatus
  passed_count: number
  total_count: number
  runtime_ms?: number | null
  error_message?: string | null
  submitted_at: string
}

export interface SubmitResultResponse {
  submission: SubmissionResponse
  first_solve: boolean
  xp_earned: number
  new_level?: number | null
  leveled_up: boolean
}

export interface CodingStatsResponse {
  solved_easy: number
  solved_medium: number
  solved_hard: number
  total_problems: number
  total_submissions: number
  streak_days: number
}

export interface MarkSolvedResponse {
  slug: string
  user_status: UserProblemStatus
  first_solve: boolean
  xp_earned: number
  new_level?: number | null
  leveled_up: boolean
}

// ── Phase 2: pattern curriculum ──────────────────────────────────────────────

export type CodingTrack = 'core' | 'advanced'

export interface PatternListItem {
  slug: string
  name: string
  track: CodingTrack
  tier: number
  order_num: number
  core_idea: string
  recognize_when: string
  difficulty_span: string
  problem_count: number
  solved_count: number
}

export interface PatternProblemRow {
  id: string
  slug: string
  title: string
  difficulty: CodingDifficulty
  seq: number | null
  lc_number: number | null
  priority: string | null
  is_premium: boolean
  also_appears_in: string | null
  leetcode_url: string
  has_editor: boolean
  user_status: UserProblemStatus
}

export interface PatternWithProblems {
  slug: string
  name: string
  track: CodingTrack
  tier: number
  core_idea: string
  recognize_when: string
  difficulty_span: string
  problem_count: number
  solved_count: number
  problems: PatternProblemRow[]
}

export interface ListProblemsOptions {
  difficulty?: CodingDifficulty
  topic?: string
  userStatus?: UserProblemStatus
}
