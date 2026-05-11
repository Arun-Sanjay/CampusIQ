/**
 * Right-side drawer wrapping the existing ChatLayout for the admin
 * Knowledge Editor's "Knowledge Assistant" chat.
 *
 * Each assistant message is parsed for a fenced `edit-proposal` JSON
 * block; if present we render an inline `EditProposalCard` below the
 * message with diff + Apply. Applying calls the same chunk-CRUD
 * endpoints as the Quick Update bar.
 *
 * Open via a floating button on the page. Drawer is a portalled fixed
 * panel so it sits above the chunk editor without affecting layout.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, MessageSquare, Plus, X } from 'lucide-react'
import ChatLayout, { type ChatLayoutMessage } from '../chat/ChatLayout'
import Button from '../ui/Button'
import EditProposalCard from './EditProposalCard'
import {
  ApiError,
  chatApi,
  collegeDocumentsApi,
} from '../../api/client'
import type {
  ChatMessage,
  ChatSession,
  CollegeDocument,
  SourceCitation,
} from '../../types'

export interface ParsedEditProposal {
  action: 'update' | 'create'
  document_id: string
  chunk_id: string | null
  chunk_index: number | null
  proposed_text: string
  reasoning?: string
}

export interface KnowledgeChatDrawerProps {
  open: boolean
  onClose: () => void
  documents: CollegeDocument[]
  onApplied: (documentId: string) => void
  pushToast: (title: string, body: string, isError?: boolean) => void
}

const suggestedQuestions = [
  'Update the hostel curfew to 11pm on weekends',
  'Add a note that lab attendance is 75%',
  'What does the placement record say about Infosys?',
]

const EDIT_PROPOSAL_REGEX = /```edit-proposal\s*\n([\s\S]*?)\n```/

function citationLabel(c: SourceCitation): string {
  return `${c.subject_code} · ${c.document_title} · chunk ${c.chunk_index + 1}`
}

function parseEditProposal(content: string): ParsedEditProposal | null {
  const match = EDIT_PROPOSAL_REGEX.exec(content)
  if (!match) return null
  try {
    const parsed = JSON.parse(match[1]!)
    if (parsed && (parsed.action === 'update' || parsed.action === 'create')) {
      return parsed as ParsedEditProposal
    }
  } catch {
    // Malformed JSON — stream may have been interrupted; skip silently.
  }
  return null
}

function stripProposalBlock(content: string): string {
  return content.replace(EDIT_PROPOSAL_REGEX, '').trim()
}

interface ProposalState {
  applying: boolean
  applied: boolean
}

export default function KnowledgeChatDrawer({
  open,
  onClose,
  documents,
  onApplied,
  pushToast,
}: KnowledgeChatDrawerProps) {
  const [session, setSession] = useState<ChatSession | null>(null)
  const [sessionLoading, setSessionLoading] = useState(false)
  const [serverMessages, setServerMessages] = useState<ChatMessage[]>([])
  const [streamingContent, setStreamingContent] = useState<string | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [proposalStates, setProposalStates] = useState<
    Record<string, ProposalState>
  >({})
  const abortRef = useRef<AbortController | null>(null)

  const bootstrappedRef = useRef(false)

  // ── Bootstrap session the first time the drawer opens. We can't put
  // `session` in the dep array — setting it from inside the effect would
  // trigger the cleanup and abort the rest of the bootstrap. ──
  useEffect(() => {
    if (!open || bootstrappedRef.current) return
    bootstrappedRef.current = true
    let cancelled = false
    void (async () => {
      setSessionLoading(true)
      try {
        const existing = await chatApi.listSessions('admin_knowledge')
        let s: ChatSession
        if (existing.length > 0) {
          s = existing[0]!
        } else {
          s = await chatApi.createSession({ chat_type: 'admin_knowledge' })
        }
        if (cancelled) return
        setSession(s)
        const full = await chatApi.getSession(s.id)
        if (!cancelled) setServerMessages(full.messages)
      } catch (err) {
        if (!cancelled) {
          const detail =
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not start Knowledge Assistant'
          pushToast('Chat unavailable', detail, true)
          bootstrappedRef.current = false  // allow retry on next open
        }
      } finally {
        if (!cancelled) setSessionLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, pushToast])

  // Abort in-flight streams when the drawer closes.
  useEffect(() => {
    if (!open) abortRef.current?.abort()
  }, [open])

  const handleApplyProposal = useCallback(
    async (messageId: string, proposal: ParsedEditProposal) => {
      setProposalStates((prev) => ({
        ...prev,
        [messageId]: { applying: true, applied: false },
      }))
      try {
        if (proposal.action === 'update') {
          if (!proposal.chunk_id) {
            throw new Error('chunk_id missing on update proposal')
          }
          await collegeDocumentsApi.updateChunk(
            proposal.document_id,
            proposal.chunk_id,
            { chunk_text: proposal.proposed_text },
          )
        } else {
          await collegeDocumentsApi.createChunk(proposal.document_id, {
            chunk_text: proposal.proposed_text,
          })
        }
        setProposalStates((prev) => ({
          ...prev,
          [messageId]: { applying: false, applied: true },
        }))
        const targetDoc = documents.find((d) => d.id === proposal.document_id)
        pushToast(
          proposal.action === 'update' ? 'Knowledge updated' : 'Entry added',
          targetDoc
            ? `${targetDoc.document_category.toUpperCase()} — ${targetDoc.title}`
            : 'Applied to college documents.',
        )
        onApplied(proposal.document_id)
      } catch (err) {
        setProposalStates((prev) => ({
          ...prev,
          [messageId]: { applying: false, applied: false },
        }))
        const detail =
          err instanceof ApiError && typeof err.detail === 'string'
            ? err.detail
            : 'Apply failed.'
        pushToast('Apply failed', detail, true)
      }
    },
    [documents, onApplied, pushToast],
  )

  // ── Build the message list the ChatLayout actually renders ──
  const layoutMessages = useMemo<ChatLayoutMessage[]>(() => {
    const items: ChatLayoutMessage[] = []
    for (const m of serverMessages) {
      const proposal =
        m.role === 'assistant' ? parseEditProposal(m.content) : null
      const display =
        m.role === 'assistant' && proposal
          ? stripProposalBlock(m.content)
          : m.content
      items.push({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: display,
        sources: m.source_citations?.map(citationLabel),
        footer: proposal
          ? (() => {
              const state = proposalStates[m.id] ?? {
                applying: false,
                applied: false,
              }
              const targetDoc = documents.find(
                (d) => d.id === proposal.document_id,
              )
              return (
                <EditProposalCard
                  mode={proposal.action}
                  proposedText={proposal.proposed_text}
                  documentTitle={targetDoc?.title ?? null}
                  documentCategory={targetDoc?.document_category ?? null}
                  chunkIndex={proposal.chunk_index}
                  applying={state.applying}
                  applied={state.applied}
                  selectedDocumentId={proposal.document_id}
                  candidateDocuments={
                    proposal.action === 'create' && targetDoc
                      ? [
                          {
                            document_id: targetDoc.id,
                            document_title: targetDoc.title,
                            document_category: targetDoc.document_category,
                            similarity: 1,
                          },
                        ]
                      : []
                  }
                  allDocuments={documents}
                  onApply={() =>
                    void handleApplyProposal(m.id, proposal)
                  }
                />
              )
            })()
          : undefined,
      })
    }
    // Streaming placeholder
    if (streamingContent !== null) {
      items.push({
        role: 'assistant',
        content: streamingContent,
        isStreaming: true,
      })
    }
    return items
  }, [serverMessages, streamingContent, proposalStates, documents, handleApplyProposal])

  const refetchSession = async (sessionId: string) => {
    const full = await chatApi.getSession(sessionId)
    setServerMessages(full.messages)
  }

  const handleSend = async (text: string) => {
    if (!session || streaming) return
    setStreaming(true)
    setStreamingContent('')

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await chatApi.streamMessage({
        sessionId: session.id,
        content: text,
        signal: controller.signal,
        onChunk: (delta) => {
          setStreamingContent((prev) => (prev ?? '') + delta)
        },
      })
      await refetchSession(session.id)
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Failed to send message'
      pushToast('Chat error', detail, true)
    } finally {
      setStreaming(false)
      setStreamingContent(null)
      abortRef.current = null
    }
  }

  const handleNewConversation = async () => {
    if (streaming) return
    setSessionLoading(true)
    setServerMessages([])
    setProposalStates({})
    try {
      const s = await chatApi.createSession({ chat_type: 'admin_knowledge' })
      setSession(s)
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not start a new conversation'
      pushToast('New chat failed', detail, true)
    } finally {
      setSessionLoading(false)
    }
  }

  if (typeof document === 'undefined') return null

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px]"
            onClick={onClose}
          />
          {/* Drawer panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-[480px] flex flex-col"
            style={{
              background: 'var(--bg-elevated)',
              borderLeft: '1px solid var(--border-default)',
              boxShadow: 'var(--shadow-elevated)',
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between gap-2 px-4 py-3 border-b"
              style={{ borderColor: 'var(--border-default)' }}
            >
              <div className="flex items-center gap-2 min-w-0">
                <MessageSquare
                  className="h-4 w-4 shrink-0"
                  style={{ color: 'var(--gradient-accent, #A78BFA)' }}
                />
                <span className="text-sm font-semibold text-[var(--text-primary)] truncate">
                  Knowledge Assistant
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  icon={Plus}
                  onClick={() => void handleNewConversation()}
                  disabled={streaming || sessionLoading}
                >
                  New
                </Button>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                  aria-label="Close drawer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 min-h-0 px-3 py-2">
              {sessionLoading && layoutMessages.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="h-5 w-5 animate-spin text-[var(--text-tertiary)]" />
                </div>
              ) : (
                <ChatLayout
                  messages={layoutMessages}
                  onSend={handleSend}
                  placeholder="Describe an update or ask about the docs…"
                  suggestedQuestions={
                    layoutMessages.length === 0 ? suggestedQuestions : undefined
                  }
                  disabled={!session || streaming || sessionLoading}
                  className="!h-full"
                />
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}
