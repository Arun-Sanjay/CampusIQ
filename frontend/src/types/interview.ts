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

// ── Live voice mode — ElevenLabs Conversational AI (Agents) ──

export interface VoiceCapabilitiesResponse {
  asr_available: boolean      // Scribe / Whisper configured on the server
  tts_available: boolean      // ElevenLabs TTS configured on the server
  agent_available: boolean    // ElevenLabs Conversational AI agent configured
  voice_by_round: Record<string, string>  // round → voice id
}

/** Everything the browser needs to open a round's live agent session. */
export interface LiveRoundStartResponse {
  round_number: number
  round_name: string
  signed_url: string
  voice_id: string
  language: string
  system_prompt: string   // → overrides.agent.prompt.prompt
  first_message: string   // → overrides.agent.firstMessage
}

export interface LiveRoundFinalizeResponse {
  round_number: number
  grading: boolean              // a background grade is in flight
  interview_completing: boolean // final round — debrief is being generated
  session: InterviewSessionResponse
}
