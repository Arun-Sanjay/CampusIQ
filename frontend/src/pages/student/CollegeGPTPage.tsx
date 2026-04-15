import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Info, Loader2, Plus } from 'lucide-react'
import ChatLayout, { type ChatLayoutMessage } from '../../components/chat/ChatLayout'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { ApiError, chatApi } from '../../api/client'
import type { ChatMessage, ChatSession, SourceCitation } from '../../types'

const suggestedQuestions = [
  'What is the attendance rule for labs?',
  'Hostel rules for first years?',
  "What's the average package at major recruiters?",
  'Which elective is best for product roles?',
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

export default function CollegeGPTPage() {
  const [session, setSession] = useState<ChatSession | null>(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  const [messages, setMessages] = useState<ChatLayoutMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // ── Find or create the user's CollegeGPT session on mount ──
  useEffect(() => {
    let cancelled = false
    void (async () => {
      setSessionLoading(true)
      setChatError(null)
      try {
        const existing = await chatApi.listSessions('college_gpt')
        let s: ChatSession
        if (existing.length > 0) {
          s = existing[0]!
        } else {
          s = await chatApi.createSession({ chat_type: 'college_gpt' })
        }
        if (cancelled) return
        setSession(s)

        const fullSession = await chatApi.getSession(s.id)
        if (cancelled) return
        setMessages(fullSession.messages.map(backendMessageToLayout))
      } catch (err) {
        if (!cancelled) {
          setChatError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load CollegeGPT session',
          )
        }
      } finally {
        if (!cancelled) setSessionLoading(false)
      }
    })()
    return () => {
      cancelled = true
      abortRef.current?.abort()
    }
  }, [])

  const handleSend = async (text: string) => {
    if (!session || streaming) return
    setChatError(null)

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
        signal: controller.signal,
        onChunk: (delta) => {
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last && last.role === 'assistant') {
              next[next.length - 1] = { ...last, content: last.content + delta }
            }
            return next
          })
        },
      })

      // Refresh from server to pick up persisted citations
      const refreshed = await chatApi.getSession(session.id)
      setMessages(refreshed.messages.map(backendMessageToLayout))
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setChatError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Failed to send message',
      )
      setMessages((prev) => prev.filter((m) => !(m.role === 'assistant' && m.isStreaming)))
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const handleNewChat = async () => {
    if (sessionLoading) return
    setSessionLoading(true)
    setMessages([])
    setChatError(null)
    try {
      const s = await chatApi.createSession({ chat_type: 'college_gpt' })
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

  return (
    <div className="space-y-4 h-[calc(100vh-8rem)] flex flex-col">
      <Card className="flex items-center justify-between gap-3 py-3 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Info className="h-4 w-4 text-info shrink-0" />
          <span className="text-sm text-[var(--text-secondary)] truncate">
            CollegeGPT answers from your college's official documents (handbooks, timetables,
            placement records, hostel rules, faculty lists)
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon={Plus}
          onClick={() => void handleNewChat()}
          disabled={streaming || sessionLoading}
        >
          New chat
        </Button>
      </Card>

      {chatError && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger shrink-0">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{chatError}</span>
        </div>
      )}

      {sessionLoading && messages.length === 0 ? (
        <Card className="flex-1 flex items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-[var(--text-tertiary)]" />
        </Card>
      ) : (
        <div className="flex-1 min-h-0">
          <ChatLayout
            messages={messages}
            onSend={handleSend}
            placeholder="Ask about college rules, placements, faculty..."
            suggestedQuestions={messages.length === 0 ? suggestedQuestions : undefined}
            disabled={!session || streaming || sessionLoading}
            className="!h-full"
          />
        </div>
      )}
    </div>
  )
}
