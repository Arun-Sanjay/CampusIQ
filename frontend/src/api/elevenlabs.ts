/**
 * Typed client for the ElevenLabs Conversational AI REST API.
 *
 * Routes through the Vite dev-server proxy at /api/elevenlabs/* so the
 * xi-api-key header is injected server-side. The browser never sees the key.
 * Configured in vite.config.ts.
 */

const BASE = '/api/elevenlabs'
export const AGENT_ID = 'agent_7901kragqncxf64tny6d59n2tnxm'

export interface ConversationListItem {
  agent_id: string
  agent_name?: string | null
  conversation_id: string
  start_time_unix_secs: number
  call_duration_secs: number | null
  message_count: number | null
  status: string
  call_successful?: string | null
}

export interface ConversationListResponse {
  conversations: ConversationListItem[]
  next_cursor: string | null
  has_more: boolean
}

export interface TranscriptTurn {
  role: 'agent' | 'user'
  message: string | null
  time_in_call_secs: number
  source_medium?: string | null
  // ElevenLabs may include scoring/feedback fields per turn in some payloads
  feedback?: unknown
}

export interface ConversationDetail {
  agent_id: string
  conversation_id: string
  status: string
  transcript: TranscriptTurn[]
  metadata: {
    start_time_unix_secs: number
    call_duration_secs: number
    cost?: number | null
    main_language?: string | null
    [key: string]: unknown
  }
  analysis?: {
    call_successful?: string | null
    transcript_summary?: string | null
    evaluation_criteria_results?: Record<string, unknown> | null
    data_collection_results?: Record<string, unknown> | null
  } | null
}

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${window.location.origin}${BASE}${path}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }
  const res = await fetch(url.pathname + url.search, { credentials: 'omit' })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`ElevenLabs ${path} → ${res.status}: ${text.slice(0, 200)}`)
  }
  return (await res.json()) as T
}

export const elevenlabs = {
  listConversations: (agentId: string = AGENT_ID, pageSize = 10) =>
    get<ConversationListResponse>('/convai/conversations', {
      agent_id: agentId,
      page_size: pageSize,
    }),

  getConversation: (conversationId: string) =>
    get<ConversationDetail>(`/convai/conversations/${conversationId}`),

  audioUrl: (conversationId: string): string =>
    `${BASE}/convai/conversations/${conversationId}/audio`,
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds < 0) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function formatStartedAt(unixSecs: number | null | undefined): string {
  if (!unixSecs) return '—'
  const d = new Date(unixSecs * 1000)
  const today = new Date()
  const isToday =
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  if (isToday) {
    return `Today, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
