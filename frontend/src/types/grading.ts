// Mirrors backend/app/schemas/grading.py

export type Leniency = 'strict' | 'moderate' | 'lenient'
export type ExamKind = 'quiz' | 'test' | 'experiential' | 'lab' | 'see'
export type ExamPart = 'theory' | 'lab'
export type SchemeStatus = 'pending' | 'parsing' | 'review' | 'ready' | 'failed'
export type AnswerSheetStatus =
  | 'uploaded' | 'ocr' | 'graded' | 'review' | 'finalized' | 'failed'

export interface ExamResponse {
  id: string
  subject_id: string
  title: string
  kind: ExamKind
  part: ExamPart
  component_key: string | null
  sequence: number | null
  max_marks: number
  co_mark_grid: Record<string, number> | null
  scheme_document_id: string | null
  scheme_status: SchemeStatus
  quiz_id: string | null
  leniency: Leniency
  custom_rules: string | null
  ignore_spelling: boolean
  award_partial_method: boolean
  confidence_review_threshold: number
  ocr_review_threshold: number
  is_published: boolean
  created_at: string
  question_count: number
  sheet_count: number
  graded_count: number
  review_count: number
}

export interface ExamQuestionResponse {
  id: string
  label: string
  parent_label: string | null
  part: ExamPart
  question_text: string
  model_answer: string | null
  max_marks: number
  co: string | null
  bloom: string | null
  order_index: number
}

export interface CourseOutcomeResponse {
  id: string
  code: string
  description: string | null
  order_index: number
}

export interface SchemeResponse {
  exam: ExamResponse
  questions: ExamQuestionResponse[]
  course_outcomes: CourseOutcomeResponse[]
  co_mark_grid: Record<string, number> | null
}

export interface AnswerSheetSummary {
  id: string
  exam_id: string
  student_id: string | null
  status: AnswerSheetStatus
  page_count: number
  detected_usn: string | null
  detected_name: string | null
  match_confidence: number | null
  match_source: string | null
  is_match_confirmed: boolean
  total_awarded: number | null
  total_max: number | null
  needs_review_count: number
  error_detail: string | null
  matched_student_name: string | null
  matched_student_usn: string | null
}

export interface QuestionGradeResponse {
  id: string
  exam_question_id: string
  label: string | null
  question_text: string | null
  model_answer: string | null
  extracted_answer: string | null
  awarded_marks: number
  max_marks: number
  effective_marks: number
  co: string | null
  confidence: number | null
  ocr_confidence: number | null
  rationale: string | null
  needs_review: boolean
  is_overridden: boolean
}

export interface AnswerSheetDetail extends AnswerSheetSummary {
  page_files: string[]
  grades: QuestionGradeResponse[]
}

export interface ReviewQueueItem {
  answer_sheet_id: string
  question_grade_id: string
  student_name: string | null
  label: string | null
  extracted_answer: string | null
  awarded_marks: number
  max_marks: number
  confidence: number | null
  rationale: string | null
}

export interface COAttainmentRow {
  co: string
  obtained: number
  max: number
  pct: number
}

export interface ExamAttainmentResponse {
  exam_id: string
  total_obtained: number
  total_max: number
  total_pct: number
  per_co: COAttainmentRow[]
  graded_students: number
}

export interface GradeConfigResponse {
  subject_id: string
  components: unknown[] | null
  cie_min_pct: number
  see_min_pct: number
  aggregate_min_pct: number
  cie_lab_min_pct: number | null
  see_lab_min_pct: number | null
  gate_lab_separately: boolean
  grade_bands: unknown[] | null
}

export interface ExamCreate {
  subject_id: string
  title: string
  kind?: ExamKind
  part?: ExamPart
  component_key?: string | null
  sequence?: number | null
  max_marks?: number
}

export interface ExamQuestionInput {
  label: string
  question_text: string
  model_answer?: string | null
  max_marks?: number
  co?: string | null
  bloom?: string | null
  parent_label?: string | null
  part?: ExamPart
  order_index?: number
}

// ── Auto Marks Assigner (cover-page scan) + manual results ──
export interface CoverScanResult {
  detected_usn: string | null
  detected_name: string | null
  student_id: string | null
  matched_student_name: string | null
  match_confidence: number | null
  total_obtained: number
  total_max: number
  per_co: Record<string, { obtained: number; max: number; pct: number }> | null
  saved: boolean
  message: string | null
}

export interface ManualResultEntry {
  student_id: string
  total_obtained: number
  per_co?: Record<string, { obtained: number; max: number; pct: number }> | null
}
