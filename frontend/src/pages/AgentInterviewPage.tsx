import { createElement, useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Headphones,
  Mic,
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

const WIDGET_SRC = 'https://elevenlabs.io/convai-widget/index.js'
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

export default function AgentInterviewPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [details, setDetails] = useState<Record<string, ConversationDetail>>({})
  const [detailLoading, setDetailLoading] = useState<Record<string, boolean>>({})
  const [detailError, setDetailError] = useState<Record<string, string>>({})
  const pollRef = useRef<number | null>(null)

  // Inject the widget script once
  useEffect(() => {
    if (document.querySelector(`script[src="${WIDGET_SRC}"]`)) return
    const script = document.createElement('script')
    script.src = WIDGET_SRC
    script.async = true
    script.type = 'text/javascript'
    document.body.appendChild(script)
  }, [])

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

          {/* Widget + side panel */}
          <div className="grid md:grid-cols-[1.2fr_1fr] gap-5 mb-10">
            {/* Widget container */}
            <div
              className="rounded-2xl p-8 flex flex-col items-center justify-center min-h-[320px]"
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                boxShadow: 'var(--shadow-elevated)',
              }}
            >
              {createElement('elevenlabs-convai', { 'agent-id': AGENT_ID })}
              <div
                className="flex items-center gap-2 text-xs mt-6"
                style={{ color: 'var(--text-tertiary)' }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full"
                  style={{ background: '#2EA043' }}
                />
                Voice: Adam · ElevenLabs Turbo v2
              </div>
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
