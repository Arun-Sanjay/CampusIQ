/**
 * Confidence Coach types — mirror backend/app/schemas/confidence.py
 */

export interface ConfidenceSessionResponse {
  id: string
  prompt: string
  transcript: string | null
  eye_contact_score: number | null
  posture_score: number | null
  filler_word_count: number | null
  speaking_pace_wpm: number | null
  clarity_score: number | null
  overall_confidence_score: number | null
  detailed_feedback: {
    headline?: string
    strengths?: string[]
    improvements?: string[]
    recommended_drill?: string
    metrics?: Record<string, number | null>
  } | null
  recorded_at: string
}

export interface ConfidenceMetric {
  recorded_at: string
  overall_confidence_score: number | null
  eye_contact_score: number | null
  posture_score: number | null
  clarity_score: number | null
  speaking_pace_wpm: number | null
  filler_word_count: number | null
}

export interface ConfidenceTimelineResponse {
  sessions: ConfidenceMetric[]
  latest: ConfidenceSessionResponse | null
  next_prompts: string[]
}

export interface ConfidenceSubmitForm {
  audioBlob: Blob
  prompt: string
  durationSeconds: number
  eyeContactPct?: number | null
  posturePct?: number | null
  browserTranscript?: string | null
}
