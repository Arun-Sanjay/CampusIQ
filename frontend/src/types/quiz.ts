/**
 * Quiz types — mirror backend Pydantic schemas in
 * backend/app/schemas/quiz.py
 */

export type Difficulty = 'easy' | 'medium' | 'hard'
export type QuestionType = 'mcq' | 'short_answer'

export interface QuestionStudentView {
  id: string
  order_index: number
  question_text: string
  question_type: QuestionType
  options: string[] | null
  difficulty: Difficulty
  topic: string | null
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

export interface QuizAttemptCreate {
  answers: QuestionAnswer[]
  time_taken_seconds?: number | null
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
