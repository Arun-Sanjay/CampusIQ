import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, type Variants } from 'framer-motion'
import { FileText, BookOpen, Loader2, AlertCircle, Plus } from 'lucide-react'
import ChatLayout, { type ChatLayoutMessage } from '../../components/chat/ChatLayout'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ApiError, chatApi, subjectsApi } from '../../api/client'
import type { ChatMessage, ChatSession, SourceCitation, Subject } from '../../types'

const fadeUp: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

const suggestedQuestions = [
  'Explain the concept in simple terms',
  'Give me a worked example',
  'How does this connect to other topics?',
]

function citationLabel(c: SourceCitation): string {
  return `${c.subject_code} · ${c.document_title} · chunk ${c.chunk_index + 1}`
}

function backendMessageToLayout(m: ChatMessage): ChatLayoutMessage {
  return {
    role: m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
    sources: m.source_citations?.map(citationLabel),
  }
}

export default function NoteAssistantPage() {
  // Subjects fetched from /subjects/
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [subjectsLoading, setSubjectsLoading] = useState(true)
  const [subjectsError, setSubjectsError] = useState<string | null>(null)

  const [activeSubjectId, setActiveSubjectId] = useState<string | null>(null)
  const [session, setSession] = useState<ChatSession | null>(null)
  const [sessionLoading, setSessionLoading] = useState(false)

  // Messages currently displayed (mix of persisted + currently-streaming)
  const [messages, setMessages] = useState<ChatLayoutMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)

  // Used to abort an in-flight stream when switching subjects
  const abortRef = useRef<AbortController | null>(null)

  // ── Load subjects on mount ──
  useEffect(() => {
    let cancelled = false
    void (async () => {
      setSubjectsLoading(true)
      setSubjectsError(null)
      try {
        const data = await subjectsApi.list()
        if (cancelled) return
        setSubjects(data)
        if (data.length > 0 && !activeSubjectId) {
          setActiveSubjectId(data[0]!.id)
        }
      } catch (err) {
        if (!cancelled) {
          setSubjectsError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load subjects',
          )
        }
      } finally {
        if (!cancelled) setSubjectsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── When subject changes, find or create the session for it ──
  useEffect(() => {
    if (!activeSubjectId) return
    let cancelled = false

    // Cancel any in-flight stream from the previous subject
    abortRef.current?.abort()
    abortRef.current = null

    void (async () => {
      setSessionLoading(true)
      setMessages([])
      setSession(null)
      setChatError(null)

      try {
        // Look for an existing session for this subject
        const existing = await chatApi.listSessions('note_assistant', activeSubjectId)
        let s: ChatSession
        if (existing.length > 0) {
          s = existing[0]!
        } else {
          // Create a fresh one
          s = await chatApi.createSession({
            chat_type: 'note_assistant',
            subject_id: activeSubjectId,
          })
        }
        if (cancelled) return
        setSession(s)

        // Load full message history
        const fullSession = await chatApi.getSession(s.id)
        if (cancelled) return
        setMessages(fullSession.messages.map(backendMessageToLayout))
      } catch (err) {
        if (!cancelled) {
          setChatError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load chat session',
          )
        }
      } finally {
        if (!cancelled) setSessionLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [activeSubjectId])

  const handleSend = async (text: string) => {
    if (!session || streaming) return
    setChatError(null)

    // Optimistic user message + placeholder streaming assistant message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', isStreaming: true },
    ])
    setStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await chatApi.streamMessage({
        sessionId: session.id,
        content: text,
        subjectId: activeSubjectId ?? undefined,
        signal: controller.signal,
        onChunk: (delta) => {
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last && last.role === 'assistant') {
              next[next.length - 1] = {
                ...last,
                content: last.content + delta,
              }
            }
            return next
          })
        },
      })

      // After the stream finishes, refresh from the server so we pick up
      // the persisted source_citations
      const refreshed = await chatApi.getSession(session.id)
      setMessages(refreshed.messages.map(backendMessageToLayout))
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        // user switched away — silently drop
        return
      }
      setChatError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Failed to send message',
      )
      // Remove the placeholder so the user can retry
      setMessages((prev) => prev.filter((m) => !(m.role === 'assistant' && m.isStreaming)))
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const handleNewChat = async () => {
    if (!activeSubjectId || sessionLoading) return
    setSessionLoading(true)
    setMessages([])
    setChatError(null)
    try {
      const s = await chatApi.createSession({
        chat_type: 'note_assistant',
        subject_id: activeSubjectId,
      })
      setSession(s)
    } catch (err) {
      setChatError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not start a new chat',
      )
    } finally {
      setSessionLoading(false)
    }
  }

  const activeSubject = useMemo(
    () => subjects.find((s) => s.id === activeSubjectId) ?? null,
    [subjects, activeSubjectId],
  )

  // ── Left panel: subject list ──
  const leftPanel = (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-3 px-2">
        <BookOpen className="h-4 w-4 text-[var(--text-tertiary)]" />
        <span className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
          Subjects
        </span>
      </div>

      {subjectsLoading && (
        <div className="flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-tertiary)]">
          <Loader2 className="h-3 w-3 animate-spin" /> Loading…
        </div>
      )}

      {subjectsError && (
        <div className="flex items-start gap-2 px-3 py-2 text-xs text-danger">
          <AlertCircle className="h-3 w-3 mt-0.5 shrink-0" /> {subjectsError}
        </div>
      )}

      {!subjectsLoading && !subjectsError && subjects.length === 0 && (
        <div className="px-3 py-3 text-xs text-[var(--text-tertiary)]">
          No subjects yet. Ask a teacher to upload course material.
        </div>
      )}

      {subjects.map((subject) => {
        const isActive = subject.id === activeSubjectId
        return (
          <motion.button
            key={subject.id}
            variants={fadeUp}
            initial="initial"
            animate="animate"
            onClick={() => setActiveSubjectId(subject.id)}
            disabled={streaming}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors disabled:cursor-not-allowed ${
              isActive
                ? 'bg-primary/10 text-[var(--text-primary)]'
                : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <FileText className="h-3.5 w-3.5 shrink-0" />
              <div className="min-w-0">
                <span className="text-sm font-medium block">{subject.code}</span>
                <span className="text-[10px] text-[var(--text-tertiary)] truncate block">
                  {subject.name}
                </span>
              </div>
            </div>
            <Badge size="sm" variant={isActive ? 'primary' : 'default'}>
              {subject.document_count}
            </Badge>
          </motion.button>
        )
      })}

      {activeSubject && (
        <div className="pt-3">
          <Button
            variant="ghost"
            size="sm"
            icon={Plus}
            className="w-full justify-start"
            onClick={() => void handleNewChat()}
            disabled={streaming || sessionLoading}
          >
            New chat
          </Button>
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-3">
      {chatError && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{chatError}</span>
        </div>
      )}
      <ChatLayout
        messages={messages}
        onSend={handleSend}
        placeholder={
          activeSubject
            ? `Ask about ${activeSubject.code} notes...`
            : 'Select a subject to start chatting'
        }
        leftPanel={leftPanel}
        suggestedQuestions={messages.length === 0 ? suggestedQuestions : undefined}
        disabled={!session || streaming || sessionLoading}
      />
    </div>
  )
}
