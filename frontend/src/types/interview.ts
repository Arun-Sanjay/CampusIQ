/**
 * Mock Interview types — mirror backend Pydantic schemas in
 * backend/app/schemas/mock_interview.py
 */

export type InterviewMode = 'text' | 'voice'
export type InterviewPersona = 'friendly' | 'tough' | 'rapid_fire' | 'unpredictable'
export type InterviewStatus = 'in_progress' | 'completed' | 'abandoned'
export type RoundStatus = 'locked' | 'active' | 'completed'
export type HireVerdict = 'strong_hire' | 'hire' | 'leaning_no' | 'no_hire'

export interface InterviewTranscriptTurn {
  role: 'assistant' | 'user'
  content: string
  round_number: number
  score: number | null
  score_reason: string | null
  is_round_transition: boolean
}

export interface RoundSummary {
  round_number: number
  name: string
  questions_asked: number
  avg_score: number | null
  status: RoundStatus
}

export interface InterviewFeedbackReport {
  hire_verdict: HireVerdict
  headline: string
  strengths: string[]
  improvements: string[]
  standout_answer: string
  biggest_gap: string
  round_averages: Record<string, number>
  overall_score: number
}

export interface InterviewSessionResponse {
  id: string
  company_target: string | null
  role_target: string | null
  interviewer_persona: InterviewPersona
  mode: InterviewMode
  current_round: number
  is_full_simulator: boolean
  status: InterviewStatus
  overall_score: number | null
  started_at: string
  completed_at: string | null
  transcript: InterviewTranscriptTurn[]
  round_summaries: RoundSummary[]
  feedback_report: InterviewFeedbackReport | null
}

export interface InterviewStartRequest {
  company_target: string
  role_target?: string
  interviewer_persona?: InterviewPersona
  mode?: InterviewMode
}

export interface InterviewMessageRequest {
  content: string
}

export interface InterviewTurnResponse {
  session: InterviewSessionResponse
  assistant_message: string
  round_transitioned: boolean
  interview_completed: boolean
}

export interface InterviewSessionListRow {
  id: string
  company_target: string | null
  role_target: string | null
  interviewer_persona: InterviewPersona
  status: InterviewStatus
  overall_score: number | null
  started_at: string
  completed_at: string | null
}

// ── Voice mode (Phase 20, F9 voice + F11) ──

export interface InterviewVoiceTurnResponse {
  session: InterviewSessionResponse
  assistant_message: string
  round_transitioned: boolean
  interview_completed: boolean
  transcribed_text: string
  assistant_audio_url: string | null
  assistant_voice_id: string | null
}

export interface VoiceCapabilitiesResponse {
  asr_available: boolean      // Whisper configured on the server
  tts_available: boolean      // ElevenLabs configured on the server
  voice_by_round: Record<string, string>  // round → voice id
}
