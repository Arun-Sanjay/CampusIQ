/**
 * Peer Doubt Community types — mirror backend Pydantic schemas in
 * backend/app/schemas/community.py
 */

export interface DoubtAnswerResponse {
  id: string
  doubt_id: string
  answered_by_id: string | null
  answered_by_name: string | null
  answer_text: string
  is_ai_generated: boolean
  is_accepted: boolean
  upvote_count: number
  created_at: string
}

export interface DoubtResponse {
  id: string
  student_id: string
  student_name: string | null
  subject_id: string | null
  subject_code: string | null
  title: string
  body: string
  tags: string[]
  is_resolved: boolean
  upvote_count: number
  view_count: number
  answer_count: number
  has_ai_answer: boolean
  created_at: string
}

export interface DoubtDetailResponse extends DoubtResponse {
  answers: DoubtAnswerResponse[]
}

export interface DoubtCreate {
  title: string
  body: string
  tags?: string[]
  subject_id?: string | null
}

export interface DoubtAnswerCreate {
  answer_text: string
}
