/**
 * Quiz types — mirror backend Pydantic schemas in
 * backend/app/schemas/quiz.py
 */

export type Difficulty = 'easy' | 'medium' | 'hard'
export type QuestionType = 'mcq' | 'short_answer'
export type QuizMode = 'practice' | 'test'
export type CIEComponent = 'quiz_1' | 'quiz_2' | 'test_1' | 'test_2'

export interface QuestionStudentView {
  id: string
  order_index: number
  question_text: string
  question_type: QuestionType
  options: string[] | null
  difficulty: Difficulty
  topic: string | null
  marks: number
  co: string | null
  bloom: string | null
}

export interface QuestionTeacherView extends QuestionStudentView {
  correct_answer: string
  explanation: string | null
}

export interface QuizSummary {
  id: string
  subject_id: string
  document_id: string | null
  created_by_id: string
  title: string
  description: string | null
  difficulty: Difficulty
  time_limit_minutes: number | null
  is_published: boolean
  is_ai_generated: boolean
  created_at: string
  question_count: number
  attempt_count: number
  avg_score: number | null
  subject_code: string | null
  subject_name: string | null
  mode: QuizMode
  max_attempts: number
  requires_proctoring: boolean
  available_from: string | null
  available_until: string | null
  cie_component: CIEComponent | null
  total_marks: number | null
  attempts_used: number
  can_attempt: boolean
}

export interface QuizForStudent extends QuizSummary {
  questions: QuestionStudentView[]
}

export interface QuizForTeacher extends QuizSummary {
  questions: QuestionTeacherView[]
}

export interface QuizGenerateRequest {
  subject_id: string
  document_id?: string | null
  topic_hint?: string | null
  num_questions?: number
  difficulty?: Difficulty
  mode?: QuizMode
  total_marks_target?: number | null
  cie_component?: CIEComponent | null
  requires_proctoring?: boolean | null
  time_limit_minutes?: number | null
}

export interface QuestionUpdate {
  id?: string | null
  question_text: string
  question_type?: QuestionType
  options?: string[] | null
  correct_answer: string
  explanation?: string | null
  difficulty?: Difficulty
  topic?: string | null
  order_index?: number
}

export interface QuizUpdate {
  title?: string
  description?: string
  difficulty?: Difficulty
  time_limit_minutes?: number
  is_published?: boolean
  questions?: QuestionUpdate[]
}

export interface QuestionAnswer {
  question_id: string
  student_answer: string
}

export interface ProctorSummary {
  tab_switch_count: number
  fullscreen_exits: number
  copy_paste_attempts: number
  face_absent_seconds: number
  face_multiple_seconds: number
  auto_submitted: boolean
}

export interface QuizAttemptCreate {
  answers: QuestionAnswer[]
  time_taken_seconds?: number | null
  started_attempt_id?: string | null
  proctor?: ProctorSummary | null
  violations?: Record<string, unknown>[] | null
}

export interface GradedAnswer {
  question_id: string
  question_text: string
  student_answer: string
  correct_answer: string
  is_correct: boolean
  topic: string | null
  difficulty: Difficulty
  explanation: string | null
  marks_awarded: number
  marks_possible: number
  co: string | null
}

export interface QuizCOAttainmentRow {
  co: string
  obtained: number
  possible: number
  pct: number
}

export interface QuizAttemptResponse {
  id: string
  quiz_id: string
  student_id: string
  score: number
  total_questions: number
  correct_count: number
  time_taken_seconds: number | null
  completed_at: string
  graded_answers: GradedAnswer[]
  weak_topics: string[]
  next_difficulty_recommendation: Difficulty | null
  mode: QuizMode
  marks_obtained: number | null
  marks_possible: number | null
  is_proctored: boolean
  auto_submitted: boolean
  co_attainment: QuizCOAttainmentRow[]
}

export interface StartAttemptResponse {
  attempt_id: string
  started_at: string
  server_now: string
  time_limit_seconds: number | null
  requires_proctoring: boolean
  mode: QuizMode
}

export interface ProctorEventIn {
  type:
    | 'tab_switch' | 'blur' | 'fullscreen_exit' | 'copy' | 'paste'
    | 'contextmenu' | 'face_absent' | 'face_multiple' | 'resume' | 'devtools'
  seconds?: number | null
  detail?: Record<string, unknown> | null
}

export interface ProctorReportRow {
  attempt_id: string
  student_id: string
  student_name: string
  marks_obtained: number | null
  marks_possible: number | null
  score: number
  tab_switch_count: number
  fullscreen_exits: number
  copy_paste_attempts: number
  face_absent_seconds: number
  face_multiple_seconds: number
  auto_submitted: boolean
  violations: Record<string, unknown>[]
  completed_at: string
}

export interface ProctorReport {
  quiz_id: string
  quiz_title: string
  rows: ProctorReportRow[]
}

export interface AttemptHistoryRow {
  id: string
  quiz_id: string
  quiz_title: string
  subject_code: string
  subject_name: string
  score: number
  total_questions: number
  correct_count: number
  time_taken_seconds: number | null
  difficulty: Difficulty
  completed_at: string
}

export interface WeakAreaResponse {
  topic: string
  subject_code: string | null
  subject_name: string | null
  score_percent: number
  attempts_count: number
  suggestion: string
}
