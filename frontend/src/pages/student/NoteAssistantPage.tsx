import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, type Variants } from 'framer-motion'
import {
  FileText,
  BookOpen,
  Loader2,
  AlertCircle,
  Plus,
  Upload,
  Trash2,
  CheckCircle2,
  Clock,
  XCircle,
} from 'lucide-react'
import ChatLayout, { type ChatLayoutMessage } from '../../components/chat/ChatLayout'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { ApiError, chatApi, documentsApi, subjectsApi } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import type {
  ChatMessage,
  ChatSession,
  DocumentWithSubject,
  SourceCitation,
  Subject,
} from '../../types'

const fadeUp: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

const suggestedQuestions = [
  'Explain the concept in simple terms',
  'Give me a worked example',
  'How does this connect to other topics?',
]

const ACCEPTED_FILE_TYPES =
  '.pdf,.doc,.docx,.ppt,.pptx,.txt,.md,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.ms-powerpoint,text/plain,text/markdown'

const MAX_FILE_BYTES = 25 * 1024 * 1024

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
  const currentUserId = useAuthStore((s) => s.user?.id ?? null)

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

  // Personal notes the student has uploaded for the active subject.
  const [myNotes, setMyNotes] = useState<DocumentWithSubject[]>([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null)

  // Used to abort an in-flight stream when switching subjects
  const abortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  // Polling timer that watches pending notes finish processing.
  const pollRef = useRef<number | null>(null)

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

  // ── Load personal notes for the active subject ──
  const reloadMyNotes = async () => {
    if (!activeSubjectId || !currentUserId) {
      setMyNotes([])
      return
    }
    setNotesError(null)
    try {
      const docs = await documentsApi.list(activeSubjectId)
      const mine = docs.filter((d) => d.owner_student_id === currentUserId)
      setMyNotes(mine)
    } catch (err) {
      setNotesError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not load your notes',
      )
    }
  }

  useEffect(() => {
    let cancelled = false
    setMyNotes([])
    setNotesLoading(true)
    void (async () => {
      await reloadMyNotes()
      if (!cancelled) setNotesLoading(false)
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSubjectId, currentUserId])

  // While any of the student's notes is still processing, poll until it
  // resolves. Stop polling when everything is `ready` or `failed`.
  useEffect(() => {
    const hasPending = myNotes.some(
      (n) => n.processing_status === 'pending' || n.processing_status === 'processing',
    )
    if (!hasPending) {
      if (pollRef.current != null) {
        window.clearTimeout(pollRef.current)
        pollRef.current = null
      }
      return
    }
    pollRef.current = window.setTimeout(() => {
      void reloadMyNotes()
    }, 3500)
    return () => {
      if (pollRef.current != null) {
        window.clearTimeout(pollRef.current)
        pollRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myNotes])

  const openFilePicker = () => {
    if (uploading) return
    setUploadFeedback(null)
    fileInputRef.current?.click()
  }

  const handleFileChosen = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    // Clear the input value so picking the same file twice still fires onChange
    e.target.value = ''
    if (!file || !activeSubjectId) return
    if (file.size > MAX_FILE_BYTES) {
      setUploadFeedback(`That file is over ${Math.round(MAX_FILE_BYTES / (1024 * 1024))} MB.`)
      return
    }
    setUploading(true)
    setUploadFeedback(`Uploading ${file.name}…`)
    try {
      await documentsApi.upload({
        file,
        subjectId: activeSubjectId,
      })
      setUploadFeedback(`Uploaded — processing ${file.name} in the background.`)
      await reloadMyNotes()
    } catch (err) {
      setUploadFeedback(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : `Could not upload ${file.name}.`,
      )
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteNote = async (note: DocumentWithSubject) => {
    if (!window.confirm(`Remove "${note.title}" from your notes?`)) return
    try {
      await documentsApi.delete(note.id)
      setMyNotes((prev) => prev.filter((n) => n.id !== note.id))
      setUploadFeedback(`Removed ${note.title}.`)
    } catch (err) {
      setUploadFeedback(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : `Could not remove ${note.title}.`,
      )
    }
  }

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

  // ── Left panel: subject list + your notes ──
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
        <>
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

          {/* Personal notes (NotebookLM-style) */}
          <div className="pt-3 border-t border-[var(--border-default)] mt-3">
            <div className="flex items-center justify-between gap-2 px-2 mb-2">
              <span className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
                Your notes
              </span>
              <span className="text-[10px] text-[var(--text-tertiary)]">
                Private · only you
              </span>
            </div>

            <Button
              variant="ghost"
              size="sm"
              icon={Upload}
              className="w-full justify-start"
              onClick={openFilePicker}
              disabled={uploading || streaming}
            >
              {uploading ? 'Uploading…' : 'Upload notes'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_FILE_TYPES}
              className="hidden"
              onChange={handleFileChosen}
            />

            {uploadFeedback && (
              <p className="px-3 py-1.5 text-[11px] text-[var(--text-tertiary)] leading-snug">
                {uploadFeedback}
              </p>
            )}

            {notesError && (
              <div className="flex items-start gap-2 px-3 py-2 text-xs text-danger">
                <AlertCircle className="h-3 w-3 mt-0.5 shrink-0" /> {notesError}
              </div>
            )}

            {notesLoading && myNotes.length === 0 && (
              <div className="flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-tertiary)]">
                <Loader2 className="h-3 w-3 animate-spin" /> Loading…
              </div>
            )}

            {!notesLoading && myNotes.length === 0 && (
              <p className="px-3 py-2 text-[11px] text-[var(--text-tertiary)] leading-snug">
                Drop a PDF or doc here — it joins this subject's RAG context for
                you only.
              </p>
            )}

            <div className="space-y-1">
              {myNotes.map((note) => (
                <div
                  key={note.id}
                  className="group flex items-center justify-between gap-2 px-3 py-2 rounded-lg hover:bg-[var(--bg-tertiary)]"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <ProcessingIcon status={note.processing_status} />
                    <span
                      className="text-xs text-[var(--text-secondary)] truncate"
                      title={note.title}
                    >
                      {note.title}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDeleteNote(note)}
                    className="opacity-0 group-hover:opacity-100 text-[var(--text-tertiary)] hover:text-danger transition-opacity"
                    aria-label={`Remove ${note.title}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </>
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

function ProcessingIcon({ status }: { status: string }) {
  if (status === 'ready') {
    return <CheckCircle2 className="h-3 w-3 text-success shrink-0" />
  }
  if (status === 'failed') {
    return <XCircle className="h-3 w-3 text-danger shrink-0" />
  }
  return <Clock className="h-3 w-3 text-warning shrink-0 animate-pulse" />
}
