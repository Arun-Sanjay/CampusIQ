/**
 * Top-of-page input that turns a natural-language statement
 * ("lab attendance is 75%") into an AI-mediated edit suggestion.
 *
 * On submit we POST /college-documents/suggest. The response is either
 * an "update_existing" suggestion (chunk diff) or a "create_new" one
 * (proposed text + doc picker). Both render inside a Modal via
 * `EditProposalCard`.
 *
 * Apply is wired to the chunk-CRUD endpoints — same primitives as the
 * inline editor below. After apply we toast and call `onApplied(docId)`
 * so the parent can refetch the affected document's chunks.
 */
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Loader2 } from 'lucide-react'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Modal from '../ui/Modal'
import EditProposalCard from './EditProposalCard'
import {
  ApiError,
  collegeDocumentsApi,
  knowledgeApi,
} from '../../api/client'
import type {
  CollegeDocument,
  KnowledgeSuggestion,
} from '../../types'

export interface QuickUpdateBarProps {
  allDocuments: CollegeDocument[]
  onApplied: (documentId: string) => void
  pushToast: (title: string, body: string, isError?: boolean) => void
}

const placeholders = [
  'lab attendance is 75%',
  'hostel curfew is 11pm on weekends',
  'Infosys CGPA cutoff is now 7.5',
  'placement coordinator: Dr. Anita Rao, room 204',
]

export default function QuickUpdateBar({
  allDocuments,
  onApplied,
  pushToast,
}: QuickUpdateBarProps) {
  const [statement, setStatement] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState<KnowledgeSuggestion | null>(null)
  const [createTargetId, setCreateTargetId] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)
  const [applied, setApplied] = useState(false)
  const [placeholderIdx] = useState(() =>
    Math.floor(Math.random() * placeholders.length),
  )

  const closeModal = () => {
    setSuggestion(null)
    setCreateTargetId(null)
    setApplying(false)
    setApplied(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!statement.trim() || loading) return
    setLoading(true)
    try {
      const result = await knowledgeApi.suggest(statement.trim())
      setSuggestion(result)
      if (result.kind === 'create_new') {
        setCreateTargetId(result.candidate_documents[0]?.document_id ?? null)
      }
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not generate a suggestion. Try again or edit a chunk manually below.'
      pushToast('Quick update failed', detail, true)
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async (finalText: string) => {
    if (!suggestion) return
    setApplying(true)
    try {
      if (suggestion.kind === 'update_existing') {
        if (!suggestion.document_id || !suggestion.chunk_id) {
          throw new Error('Missing identifiers on suggestion')
        }
        await collegeDocumentsApi.updateChunk(
          suggestion.document_id,
          suggestion.chunk_id,
          { chunk_text: finalText },
        )
        setApplied(true)
        pushToast(
          'Knowledge updated',
          `${suggestion.document_category?.toUpperCase()} — ${suggestion.document_title} (chunk ${
            (suggestion.chunk_index ?? 0) + 1
          })`,
        )
        onApplied(suggestion.document_id)
      } else {
        const docId = createTargetId
        if (!docId) {
          pushToast(
            'Pick a document',
            'Select where to add this new entry before applying.',
            true,
          )
          setApplying(false)
          return
        }
        await collegeDocumentsApi.createChunk(docId, { chunk_text: finalText })
        setApplied(true)
        const dest = allDocuments.find((d) => d.id === docId)
        pushToast(
          'New entry added',
          dest
            ? `${dest.document_category.toUpperCase()} — ${dest.title}`
            : 'Chunk added.',
        )
        onApplied(docId)
      }
      setStatement('')
      // Close after a brief Applied-flash so the user sees the green check.
      setTimeout(closeModal, 700)
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Apply failed. Edit the text and try again.'
      pushToast('Apply failed', detail, true)
      setApplying(false)
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="rounded-card border p-4 space-y-2"
        style={{
          background: 'var(--bg-elevated)',
          borderColor: 'var(--border-default)',
        }}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" style={{ color: 'var(--gradient-accent, #A78BFA)' }} />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Quick update</h3>
        </div>
        <p className="text-xs text-[var(--text-tertiary)] leading-snug">
          Type a fact, rule, or correction. We'll find where it belongs in your
          documents and propose the rewrite.
        </p>
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <div className="flex-1">
            <Input
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              placeholder={placeholders[placeholderIdx]!}
              disabled={loading}
            />
          </div>
          <Button
            type="submit"
            icon={loading ? Loader2 : Sparkles}
            disabled={!statement.trim() || loading}
          >
            {loading ? 'Thinking…' : 'Apply update'}
          </Button>
        </form>
      </motion.div>

      <Modal
        isOpen={!!suggestion}
        onClose={closeModal}
        title={
          suggestion?.kind === 'update_existing'
            ? 'Review the proposed edit'
            : 'Add new entry'
        }
        size="lg"
      >
        {suggestion && (
          <EditProposalCard
            mode={suggestion.kind === 'update_existing' ? 'update' : 'create'}
            currentText={suggestion.current_chunk_text}
            proposedText={suggestion.proposed_chunk_text}
            documentTitle={suggestion.document_title}
            documentCategory={suggestion.document_category}
            chunkIndex={suggestion.chunk_index}
            similarity={suggestion.similarity}
            candidateDocuments={suggestion.candidate_documents}
            allDocuments={allDocuments}
            selectedDocumentId={createTargetId}
            onSelectDocument={setCreateTargetId}
            applying={applying}
            applied={applied}
            onApply={handleApply}
            onCancel={closeModal}
          />
        )}
      </Modal>
    </>
  )
}
