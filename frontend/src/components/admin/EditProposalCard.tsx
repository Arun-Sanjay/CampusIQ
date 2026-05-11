/**
 * Inline diff card for a proposed knowledge edit.
 *
 * Used in two places:
 *   1. The Quick Update modal (after `knowledgeApi.suggest` returns).
 *   2. Underneath assistant chat messages in `KnowledgeChatDrawer` when
 *      the message contains a fenced `edit-proposal` JSON block.
 *
 * The card has two modes:
 *   - `update` — render `current_chunk_text` vs `proposed_chunk_text` as
 *     a word-level diff (additions green, removals red strikethrough).
 *   - `create` — render the proposed text only, plus a document picker
 *     when no doc was preselected.
 *
 * Apply calls a parent-provided callback so the same component works
 * for the Quick Update flow (which calls PATCH/POST directly) and the
 * chat flow (which dispatches via the chat drawer).
 */
import { useMemo, useState } from 'react'
import { Check, Pencil, RotateCcw, Sparkles } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Select from '../ui/Select'
import TextArea from '../ui/TextArea'
import { wordDiff } from '../../utils/wordDiff'
import type {
  CollegeDocument,
  CollegeDocumentCategory,
  SuggestionCandidate,
} from '../../types'

export type EditMode = 'update' | 'create'

export interface EditProposalCardProps {
  mode: EditMode
  currentText?: string | null
  proposedText: string
  /** Used in `update` mode — labelled chip at the top showing the doc. */
  documentTitle?: string | null
  documentCategory?: CollegeDocumentCategory | null
  chunkIndex?: number | null
  similarity?: number | null
  /** Used in `create` mode — candidates ranked by similarity to seed the
   *  document picker; the highest one is preselected. */
  candidateDocuments?: SuggestionCandidate[]
  /** Pool of all docs the admin can target in `create` mode. */
  allDocuments?: CollegeDocument[]
  /** Selected destination doc id in `create` mode (controlled). */
  selectedDocumentId?: string | null
  onSelectDocument?: (documentId: string) => void
  applying?: boolean
  applied?: boolean
  /** Returns the final text the admin wants to commit. */
  onApply: (finalText: string) => void
  onCancel?: () => void
}

const formatPercent = (similarity: number) =>
  `${Math.round(similarity * 100)}% match`

export default function EditProposalCard({
  mode,
  currentText,
  proposedText,
  documentTitle,
  documentCategory,
  chunkIndex,
  similarity,
  candidateDocuments = [],
  allDocuments = [],
  selectedDocumentId,
  onSelectDocument,
  applying = false,
  applied = false,
  onApply,
  onCancel,
}: EditProposalCardProps) {
  // The admin can hand-edit the proposed text before applying.
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(proposedText)

  const docOptions = useMemo(() => {
    if (mode !== 'create') return []
    // Highlight candidate docs at the top; append the rest below.
    const candidateIds = new Set(candidateDocuments.map((c) => c.document_id))
    const top = candidateDocuments.map((c) => ({
      value: c.document_id,
      label: `${c.document_category.toUpperCase()} — ${c.document_title}  (${formatPercent(c.similarity)})`,
    }))
    const rest = allDocuments
      .filter((d) => !candidateIds.has(d.id))
      .map((d) => ({
        value: d.id,
        label: `${d.document_category.toUpperCase()} — ${d.title}`,
      }))
    return [{ value: '', label: 'Pick a document…' }, ...top, ...rest]
  }, [mode, candidateDocuments, allDocuments])

  const diffSegments = useMemo(() => {
    if (mode !== 'update') return []
    return wordDiff(currentText ?? '', editing ? draft : proposedText)
  }, [mode, currentText, proposedText, draft, editing])

  const handleApply = () => {
    if (applying || applied) return
    onApply(editing ? draft : proposedText)
  }

  const canApply =
    !applying &&
    !applied &&
    (mode === 'update' ? Boolean(currentText) : Boolean(selectedDocumentId))

  return (
    <div
      className="rounded-card border p-4 space-y-3"
      style={{
        background: 'var(--bg-elevated)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <Sparkles className="h-4 w-4" style={{ color: 'var(--gradient-accent, #A78BFA)' }} />
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            {mode === 'update' ? 'Update existing entry' : 'New entry'}
          </span>
          {documentCategory && (
            <Badge size="sm" variant="info">
              {documentCategory.toUpperCase()}
            </Badge>
          )}
          {documentTitle && (
            <span className="text-xs text-[var(--text-tertiary)] truncate max-w-[280px]">
              {documentTitle}
              {chunkIndex !== null && chunkIndex !== undefined
                ? ` · chunk ${chunkIndex + 1}`
                : ''}
            </span>
          )}
          {similarity !== null && similarity !== undefined && mode === 'update' && (
            <Badge size="sm">{formatPercent(similarity)}</Badge>
          )}
        </div>
      </div>

      {/* Body */}
      {mode === 'update' && !editing && (
        <div
          className="text-sm leading-relaxed rounded-md px-3 py-2 max-h-[280px] overflow-y-auto"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {diffSegments.map((seg, i) => {
            if (seg.op === 'same') {
              return (
                <span key={i} className="text-[var(--text-secondary)]">
                  {seg.text}
                </span>
              )
            }
            if (seg.op === 'add') {
              return (
                <span
                  key={i}
                  className="text-success font-medium"
                  style={{ background: 'rgba(34, 197, 94, 0.12)' }}
                >
                  {seg.text}
                </span>
              )
            }
            return (
              <span
                key={i}
                className="text-danger line-through"
                style={{ background: 'rgba(239, 68, 68, 0.12)' }}
              >
                {seg.text}
              </span>
            )
          })}
        </div>
      )}

      {mode === 'update' && editing && (
        <TextArea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={8}
          className="w-full"
        />
      )}

      {mode === 'create' && (
        <div className="space-y-2">
          {docOptions.length > 0 && (
            <Select
              label="Add to document"
              options={docOptions}
              value={selectedDocumentId ?? ''}
              onChange={(e) => onSelectDocument?.(e.target.value)}
            />
          )}
          <TextArea
            label="Proposed text"
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              if (!editing) setEditing(true)
            }}
            rows={6}
            className="w-full"
          />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-end gap-2 pt-1">
        {mode === 'update' && (
          <Button
            size="sm"
            variant="ghost"
            icon={editing ? RotateCcw : Pencil}
            onClick={() => {
              if (editing) setDraft(proposedText)
              setEditing((prev) => !prev)
            }}
          >
            {editing ? 'Reset' : 'Edit manually'}
          </Button>
        )}
        {onCancel && !applied && (
          <Button size="sm" variant="secondary" onClick={onCancel} disabled={applying}>
            Cancel
          </Button>
        )}
        <Button
          size="sm"
          variant={applied ? 'success' : 'primary'}
          icon={applied ? Check : undefined}
          onClick={handleApply}
          disabled={!canApply}
          loading={applying}
        >
          {applied ? 'Applied' : mode === 'update' ? 'Apply update' : 'Add to document'}
        </Button>
      </div>
    </div>
  )
}
