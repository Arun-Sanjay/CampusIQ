import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ConversationProvider, useConversation } from '@elevenlabs/react'
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Headphones,
  Loader2,
  Mic,
  PhoneOff,
  RefreshCw,
  Sparkles,
  User,
} from 'lucide-react'
import {
  AGENT_ID,
  elevenlabs,
  formatDuration,
  formatStartedAt,
  type ConversationDetail,
  type ConversationListItem,
} from '../api/elevenlabs'

const POLL_INTERVAL_MS = 8_000

const rounds = [
  { num: 1, label: 'Intro / Background', detail: 'Tell me about yourself' },
  { num: 2, label: 'Technical', detail: 'DSA or coding walkthrough' },
  { num: 3, label: 'System Design', detail: 'New-grad scope, trade-offs' },
  { num: 4, label: 'Project Deep-dive', detail: 'Something you built' },
  { num: 5, label: 'Wrap-up', detail: 'Next steps + close' },
]

function statusBadge(status: string, callSuccessful?: string | null): { label: string; bg: string; color: string } {
  const norm = (status || '').toLowerCase()
  const success = (callSuccessful || '').toLowerCase()
  if (norm === 'done' && success === 'success') {
    return { label: 'Completed', bg: 'rgba(46, 160, 67, 0.12)', color: '#2EA043' }
  }
  if (norm === 'done') {
    return { label: 'Ended', bg: 'rgba(100, 116, 139, 0.18)', color: 'var(--text-secondary)' }
  }
  if (norm === 'in-progress' || norm === 'in_progress' || norm === 'initiated' || norm === 'processing') {
    return { label: 'Live', bg: 'rgba(124, 58, 237, 0.18)', color: '#7C3AED' }
  }
  if (norm === 'failed' || success === 'failure') {
    return { label: 'Failed', bg: 'rgba(220, 38, 38, 0.12)', color: '#DC2626' }
  }
  return { label: norm || 'Unknown', bg: 'rgba(100, 116, 139, 0.18)', color: 'var(--text-secondary)' }
}

// ═════════════════════════════════════════════════════════════════
// Call controls — uses @elevenlabs/react useConversation hook
// ═════════════════════════════════════════════════════════════════

interface CallControlsProps {
  onCallEnded: () => void
}

interface LiveMessage {
  role: 'agent' | 'user'
  text: string
  timestamp: number
}

function CallControls({ onCallEnded }: CallControlsProps) {
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [messages, setMessages] = useState<LiveMessage[]>([])
  const transcriptRef = useRef<HTMLDivElement>(null)

  const conversation = useConversation({
    onConnect: () => setError(null),
    onDisconnect: () => {
      // Trigger an immediate refresh of past interviews after a call ends
      onCallEnded()
    },
    onError: (e) => {
      setError(typeof e === 'string' ? e : 'Connection error — try again')
    },
    onMessage: ({ message, source }) => {
      if (!message || !message.trim()) return
      setMessages((prev) => [
        ...prev,
        {
          role: source === 'ai' ? 'agent' : 'user',
          text: message,
          timestamp: Date.now(),
        },
      ])
    },
  })

  // Auto-scroll the live transcript to the bottom as new lines arrive
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [messages.length])

  const status = conversation.status
  const isIdle = status === 'disconnected' || status === 'error'
  const isConnecting = status === 'connecting' || starting
  const isLive = status === 'connected'
  const isAgentSpeaking = isLive && conversation.isSpeaking
  const isListening = isLive && !conversation.isSpeaking

  const handleStart = useCallback(async () => {
    setError(null)
    setStarting(true)
    setMessages([])
    try {
      // Pre-request mic so the prompt isn't buried inside the SDK call
      await navigator.mediaDevices.getUserMedia({ audio: true })
      conversation.startSession({ agentId: AGENT_ID, connectionType: 'websocket' })
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message.includes('Permission')
            ? 'Microphone permission denied — allow access in your browser to continue.'
            : e.message
          : 'Could not start the interview',
      )
    } finally {
      setStarting(false)
    }
  }, [conversation])

  const handleEnd = useCallback(() => {
    try {
      conversation.endSession()
    } catch {
      // already disconnected
    }
  }, [conversation])

  // ── Idle state ─────────────────────────────────────────────────
  if (isIdle && !isConnecting) {
    return (
      <div className="flex flex-col items-center justify-center w-full">
        <motion.button
          type="button"
          onClick={() => void handleStart()}
          className="group relative inline-flex items-center gap-3 px-8 py-4 rounded-full font-semibold text-base text-white shadow-lg transition-transform"
          style={{
            background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
            boxShadow: '0 10px 30px -10px rgba(124, 58, 237, 0.5)',
          }}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Mic className="h-5 w-5" />
          Start Interview
        </motion.button>
        <p
          className="text-xs mt-4 text-center"
          style={{ color: 'var(--text-tertiary)' }}
        >
          Click to begin. You'll be asked for microphone access.
        </p>
        {error && (
          <div
            className="mt-4 rounded-lg px-3 py-2 text-sm text-center max-w-sm"
            style={{
              background: 'rgba(220, 38, 38, 0.08)',
              border: '1px solid rgba(220, 38, 38, 0.25)',
              color: '#DC2626',
            }}
          >
            {error}
          </div>
        )}
      </div>
    )
  }

  // ── Connecting state ───────────────────────────────────────────
  if (isConnecting) {
    return (
      <div className="flex flex-col items-center justify-center w-full">
        <div
          className="w-24 h-24 rounded-full flex items-center justify-center"
          style={{
            background: 'rgba(124, 58, 237, 0.12)',
            border: '2px solid rgba(124, 58, 237, 0.3)',
          }}
        >
          <Loader2 className="h-10 w-10 animate-spin" style={{ color: '#7C3AED' }} />
        </div>
        <p
          className="text-sm mt-5 font-medium"
          style={{ color: 'var(--text-primary)' }}
        >
          Connecting to your interviewer…
        </p>
      </div>
    )
  }

  // ── Live call state ────────────────────────────────────────────
  return (
    <div className="flex flex-col items-center justify-center w-full">
      <div className="relative w-32 h-32 flex items-center justify-center mb-4">
        {/* Pulsing rings while agent speaks */}
        {isAgentSpeaking && (
          <>
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{ background: 'rgba(124, 58, 237, 0.35)' }}
              animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
            />
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{ background: 'rgba(124, 58, 237, 0.25)' }}
              animate={{ scale: [1, 1.8, 1], opacity: [0.4, 0, 0.4] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut', delay: 0.4 }}
            />
          </>
        )}
        {/* Listening pulse */}
        {isListening && (
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{ background: 'rgba(46, 160, 67, 0.25)' }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.4, 0.1, 0.4] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
        {/* Core orb */}
        <div
          className="relative w-24 h-24 rounded-full flex items-center justify-center"
          style={{
            background: isAgentSpeaking
              ? 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)'
              : 'linear-gradient(135deg, rgba(124, 58, 237, 0.15) 0%, rgba(91, 33, 182, 0.12) 100%)',
            border: isAgentSpeaking
              ? '2px solid rgba(255, 255, 255, 0.2)'
              : '2px solid rgba(124, 58, 237, 0.3)',
            boxShadow: isAgentSpeaking ? '0 0 40px rgba(124, 58, 237, 0.5)' : 'none',
            transition: 'all 0.3s ease',
          }}
        >
          {isAgentSpeaking ? (
            <Bot className="h-10 w-10 text-white" />
          ) : (
            <Mic className="h-10 w-10" style={{ color: '#7C3AED' }} />
          )}
        </div>
      </div>

      <div className="text-center mb-4">
        <p
          className="text-sm font-medium"
          style={{ color: 'var(--text-primary)' }}
        >
          {isAgentSpeaking ? 'Adam is speaking…' : 'Listening — your turn'}
        </p>
        <p
          className="text-xs mt-1"
          style={{ color: 'var(--text-tertiary)' }}
        >
          {isAgentSpeaking
            ? 'You can interrupt at any time'
            : 'Speak naturally — pause when done'}
        </p>
      </div>

      {/* Live transcript — appears once the first message arrives */}
      <div
        ref={transcriptRef}
        className="w-full max-w-md rounded-xl px-3 py-3 mb-4 overflow-y-auto space-y-2 transition-opacity"
        style={{
          maxHeight: 220,
          minHeight: messages.length > 0 ? 80 : 0,
          opacity: messages.length > 0 ? 1 : 0,
          background: 'var(--bg-secondary)',
          border: messages.length > 0 ? '1px solid var(--border-default)' : '1px solid transparent',
        }}
      >
        {messages.map((m, i) => {
          const isAgent = m.role === 'agent'
          return (
            <div key={i} className={`flex gap-2 ${isAgent ? '' : 'justify-end'}`}>
              <div
                className="max-w-[88%] rounded-lg px-2.5 py-1.5 text-xs leading-relaxed"
                style={
                  isAgent
                    ? {
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-primary)',
                      }
                    : {
                        background: '#7C3AED',
                        color: 'white',
                      }
                }
              >
                <div
                  className="text-[9px] uppercase tracking-wider mb-0.5 opacity-70 font-semibold"
                  style={isAgent ? { color: 'var(--text-tertiary)' } : { color: 'rgba(255,255,255,0.85)' }}
                >
                  {isAgent ? 'Adam' : 'You'}
                </div>
                {m.text}
              </div>
            </div>
          )
        })}
      </div>

      <motion.button
        type="button"
        onClick={() => void handleEnd()}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-colors"
        style={{
          background: 'rgba(220, 38, 38, 0.1)',
          border: '1px solid rgba(220, 38, 38, 0.3)',
          color: '#DC2626',
        }}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
      >
        <PhoneOff className="h-4 w-4" />
        End Interview
      </motion.button>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════
// Transcript card — shown when a past interview row is expanded
// ═════════════════════════════════════════════════════════════════

interface TranscriptCardProps {
  conversation: ConversationListItem
  detail: ConversationDetail | null
  loading: boolean
  error: string | null
}

function TranscriptCard({ conversation, detail, loading, error }: TranscriptCardProps) {
  if (loading) {
    return (
      <div className="px-4 py-6 text-sm" style={{ color: 'var(--text-tertiary)' }}>
        Loading transcript…
      </div>
    )
  }
  if (error) {
    return (
      <div className="px-4 py-6 text-sm" style={{ color: '#DC2626' }}>
        Could not load transcript: {error}
      </div>
    )
  }
  if (!detail || !detail.transcript || detail.transcript.length === 0) {
    return (
      <div className="px-4 py-6 text-sm" style={{ color: 'var(--text-tertiary)' }}>
        No transcript yet — ElevenLabs may still be processing this call. Hit refresh in a few seconds.
      </div>
    )
  }
  return (
    <div className="px-4 pb-4 pt-2 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <audio
          src={elevenlabs.audioUrl(conversation.conversation_id)}
          controls
          preload="none"
          style={{ height: 36 }}
        />
        <a
          href={`https://elevenlabs.io/app/conversational-ai/history/${conversation.conversation_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border hover:bg-[var(--bg-tertiary)] transition-colors"
          style={{ borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }}
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open in ElevenLabs
        </a>
      </div>

      {detail.analysis?.transcript_summary && (
        <div
          className="rounded-lg p-3 text-sm"
          style={{
            background: 'rgba(124, 58, 237, 0.06)',
            border: '1px solid rgba(124, 58, 237, 0.2)',
            color: 'var(--text-secondary)',
          }}
        >
          <div
            className="text-[10px] uppercase tracking-wider mb-1 font-semibold"
            style={{ color: '#7C3AED' }}
          >
            ElevenLabs summary
          </div>
          {detail.analysis.transcript_summary}
        </div>
      )}

      <div className="space-y-3">
        {detail.transcript.map((turn, i) => {
          const isAgent = turn.role === 'agent'
          if (!turn.message) return null
          return (
            <div key={i} className={`flex gap-2 ${isAgent ? '' : 'justify-end'}`}>
              {isAgent && (
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: 'rgba(124, 58, 237, 0.12)' }}
                >
                  <Bot className="h-3.5 w-3.5" style={{ color: '#7C3AED' }} />
                </div>
              )}
              <div
                className="max-w-[78%] rounded-lg px-3 py-2 text-sm leading-relaxed"
                style={
                  isAgent
                    ? {
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-primary)',
                      }
                    : {
                        background: '#7C3AED',
                        color: 'white',
                      }
                }
              >
                <div
                  className="text-[10px] uppercase tracking-wider mb-1 opacity-70 font-semibold"
                  style={isAgent ? { color: 'var(--text-tertiary)' } : { color: 'rgba(255,255,255,0.8)' }}
                >
                  {isAgent ? 'Adam' : 'You'} · {formatDuration(turn.time_in_call_secs)}
                </div>
                {turn.message}
              </div>
              {!isAgent && (
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: 'var(--bg-tertiary)' }}
                >
                  <User className="h-3.5 w-3.5" style={{ color: 'var(--text-secondary)' }} />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════
// Page
// ═════════════════════════════════════════════════════════════════

export default function AgentInterviewPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [details, setDetails] = useState<Record<string, ConversationDetail>>({})
  const [detailLoading, setDetailLoading] = useState<Record<string, boolean>>({})
  const [detailError, setDetailError] = useState<Record<string, string>>({})
  const pollRef = useRef<number | null>(null)

  const fetchList = useCallback(async () => {
    try {
      const data = await elevenlabs.listConversations(AGENT_ID, 10)
      setConversations(data.conversations || [])
      setListError(null)
    } catch (err) {
      setListError(err instanceof Error ? err.message : 'Failed to load past interviews')
    } finally {
      setListLoading(false)
    }
  }, [])

  // Initial load + polling so new calls appear automatically after they end
  useEffect(() => {
    fetchList()
    pollRef.current = window.setInterval(fetchList, POLL_INTERVAL_MS)
    return () => {
      if (pollRef.current != null) window.clearInterval(pollRef.current)
    }
  }, [fetchList])

  // After a call ends, give ElevenLabs a moment to finalize then refresh.
  const handleCallEnded = useCallback(() => {
    window.setTimeout(() => void fetchList(), 1_500)
    window.setTimeout(() => void fetchList(), 5_000)
  }, [fetchList])

  const loadDetail = useCallback(
    async (conversationId: string) => {
      if (details[conversationId] || detailLoading[conversationId]) return
      setDetailLoading((s) => ({ ...s, [conversationId]: true }))
      try {
        const data = await elevenlabs.getConversation(conversationId)
        setDetails((s) => ({ ...s, [conversationId]: data }))
        setDetailError((s) => {
          const next = { ...s }
          delete next[conversationId]
          return next
        })
      } catch (err) {
        setDetailError((s) => ({
          ...s,
          [conversationId]: err instanceof Error ? err.message : 'Failed to load',
        }))
      } finally {
        setDetailLoading((s) => ({ ...s, [conversationId]: false }))
      }
    },
    [details, detailLoading],
  )

  const toggleExpand = useCallback(
    (id: string) => {
      if (expandedId === id) {
        setExpandedId(null)
      } else {
        setExpandedId(id)
        void loadDetail(id)
      }
    },
    [expandedId, loadDetail],
  )

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        background:
          'radial-gradient(ellipse at top, rgba(124, 58, 237, 0.18), transparent 60%), var(--bg-primary)',
      }}
    >
      <header className="px-6 py-4 flex items-center justify-between border-b border-[var(--border-subtle)]">
        <Link
          to="/student"
          className="inline-flex items-center gap-2 text-sm transition-colors hover:opacity-80"
          style={{ color: 'var(--text-secondary)' }}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
        <div
          className="flex items-center gap-2 text-xs"
          style={{ color: 'var(--text-tertiary)' }}
        >
          <Sparkles className="h-3.5 w-3.5" />
          CampusIQ · Voice Interview
        </div>
      </header>

      <main className="flex-1 px-6 py-10 max-w-6xl mx-auto w-full">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          {/* Hero */}
          <div className="text-center mb-10">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mb-5"
              style={{
                background: 'rgba(124, 58, 237, 0.12)',
                color: 'var(--text-primary)',
                border: '1px solid rgba(124, 58, 237, 0.25)',
              }}
            >
              <Mic className="h-3 w-3" />
              Live · ElevenLabs Conversational AI
            </div>
            <h1
              className="text-4xl md:text-5xl font-semibold tracking-tight mb-3"
              style={{ color: 'var(--text-primary)' }}
            >
              Google · Software Engineer
            </h1>
            <p
              className="text-base max-w-xl mx-auto"
              style={{ color: 'var(--text-secondary)' }}
            >
              A live, voice-first mock interview with a Google search infrastructure engineer.
              Five to seven minutes — background, technical, light system design.
            </p>
          </div>

          {/* Call panel + side panel */}
          <div className="grid md:grid-cols-[1.2fr_1fr] gap-5 mb-10">
            {/* Call container */}
            <div
              className="rounded-2xl p-10 flex items-center justify-center min-h-[360px]"
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                boxShadow: 'var(--shadow-elevated)',
              }}
            >
              <ConversationProvider>
                <CallControls onCallEnded={handleCallEnded} />
              </ConversationProvider>
            </div>

            {/* Side panel — pre-flight + structure */}
            <div className="space-y-4">
              <div
                className="rounded-2xl p-5"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-default)',
                }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <Headphones className="h-4 w-4" style={{ color: 'var(--text-primary)' }} />
                  <h3
                    className="text-sm font-semibold"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    Before you begin
                  </h3>
                </div>
                <ul
                  className="text-sm space-y-1.5"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  <li>· Headphones recommended (stops echo)</li>
                  <li>· Speak naturally, pause when done</li>
                  <li>· You can interrupt — it'll stop politely</li>
                  <li>· Allow mic on first click</li>
                </ul>
              </div>

              <div
                className="rounded-2xl p-5"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-default)',
                }}
              >
                <h3
                  className="text-sm font-semibold mb-3"
                  style={{ color: 'var(--text-primary)' }}
                >
                  Interview shape
                </h3>
                <ol className="space-y-2">
                  {rounds.map((r) => (
                    <li key={r.num} className="flex items-start gap-2.5 text-sm">
                      <span
                        className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
                        style={{
                          background: 'rgba(124, 58, 237, 0.12)',
                          color: '#7C3AED',
                        }}
                      >
                        {r.num}
                      </span>
                      <div className="flex-1">
                        <div
                          className="font-medium"
                          style={{ color: 'var(--text-primary)' }}
                        >
                          {r.label}
                        </div>
                        <div
                          className="text-xs"
                          style={{ color: 'var(--text-tertiary)' }}
                        >
                          {r.detail}
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>

          {/* Past interviews */}
          <div className="mb-3 flex items-center justify-between">
            <h2
              className="text-lg font-semibold"
              style={{ color: 'var(--text-primary)' }}
            >
              Past interviews
            </h2>
            <button
              type="button"
              onClick={() => {
                setListLoading(true)
                void fetchList()
              }}
              disabled={listLoading}
              className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border transition-colors hover:bg-[var(--bg-tertiary)] disabled:opacity-50"
              style={{
                borderColor: 'var(--border-default)',
                color: 'var(--text-secondary)',
              }}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${listLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          <p
            className="text-xs mb-4"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Auto-refreshes every 8 seconds — new calls appear here once ElevenLabs finishes processing them.
          </p>

          {listError && (
            <div
              className="rounded-lg p-3 text-sm mb-4"
              style={{
                background: 'rgba(220, 38, 38, 0.08)',
                border: '1px solid rgba(220, 38, 38, 0.25)',
                color: '#DC2626',
              }}
            >
              {listError}
            </div>
          )}

          {conversations.length === 0 && !listLoading && !listError && (
            <div
              className="rounded-2xl p-8 text-center"
              style={{
                background: 'var(--bg-secondary)',
                border: '1px dashed var(--border-default)',
                color: 'var(--text-tertiary)',
              }}
            >
              <div className="text-sm mb-1">No past interviews yet.</div>
              <div className="text-xs">Start one above — it'll appear here automatically.</div>
            </div>
          )}

          <div className="space-y-3">
            {conversations.map((c) => {
              const badge = statusBadge(c.status, c.call_successful)
              const isExpanded = expandedId === c.conversation_id
              return (
                <motion.div
                  key={c.conversation_id}
                  layout
                  className="rounded-xl overflow-hidden"
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-default)',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => toggleExpand(c.conversation_id)}
                    className="w-full px-4 py-3 flex items-center gap-4 text-left transition-colors hover:bg-[var(--bg-tertiary)]"
                  >
                    <div className="flex-1 min-w-0">
                      <div
                        className="text-sm font-medium truncate"
                        style={{ color: 'var(--text-primary)' }}
                      >
                        {formatStartedAt(c.start_time_unix_secs)}
                      </div>
                      <div
                        className="text-xs flex items-center gap-3 mt-0.5"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        <span>
                          {formatDuration(c.call_duration_secs)} · {c.message_count ?? 0} messages
                        </span>
                        <span className="font-mono text-[10px] opacity-70">
                          {c.conversation_id.slice(0, 18)}…
                        </span>
                      </div>
                    </div>
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider shrink-0"
                      style={{ background: badge.bg, color: badge.color }}
                    >
                      {badge.label}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                    ) : (
                      <ChevronDown className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                    )}
                  </button>
                  <AnimatePresence initial={false}>
                    {isExpanded && (
                      <motion.div
                        key="body"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{ overflow: 'hidden', borderTop: '1px solid var(--border-default)' }}
                      >
                        <TranscriptCard
                          conversation={c}
                          detail={details[c.conversation_id] ?? null}
                          loading={detailLoading[c.conversation_id] ?? false}
                          error={detailError[c.conversation_id] ?? null}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      </main>

      <footer
        className="px-6 py-4 text-center text-xs"
        style={{ color: 'var(--text-tertiary)' }}
      >
        CampusIQ phase 2 — voice interview prototype. Full structured scoring + debrief lands in phase 3.
      </footer>
    </div>
  )
}
