/**
 * Editable card for one chunk of a college document. Used in the
 * Knowledge Editor's main right-pane list. Holds its own dirty + draft
 * state so the admin can revert.
 */
import { useEffect, useState } from 'react'
import { Check, Loader2, RotateCcw, Trash2 } from 'lucide-react'
import Button from '../ui/Button'
import TextArea from '../ui/TextArea'
import type { DocumentChunkPreview } from '../../types'

export interface ChunkCardProps {
  chunk: DocumentChunkPreview
  saving?: boolean
  /** Briefly true after a successful save (~1s). */
  justSaved?: boolean
  /** Surface backend errors inline. */
  errorMessage?: string | null
  onSave: (newText: string) => void
  onDelete: () => void
}

export default function ChunkCard({
  chunk,
  saving = false,
  justSaved = false,
  errorMessage,
  onSave,
  onDelete,
}: ChunkCardProps) {
  const [draft, setDraft] = useState(chunk.chunk_text)

  // Re-sync local draft whenever the server-side text changes (e.g. an
  // edit was applied via the chat drawer and parent refetched).
  useEffect(() => {
    setDraft(chunk.chunk_text)
  }, [chunk.id, chunk.chunk_text])

  const dirty = draft !== chunk.chunk_text
  const empty = draft.trim().length < 10

  return (
    <div
      className="rounded-card border p-4 space-y-2"
      style={{
        background: 'var(--bg-elevated)',
        borderColor: 'var(--border-default)',
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
          <span className="font-mono">Chunk #{chunk.chunk_index + 1}</span>
          {chunk.compression_ratio !== null && (
            <span>{chunk.compression_ratio.toFixed(0)}% compressed</span>
          )}
        </div>
        <button
          onClick={onDelete}
          className="text-[var(--text-tertiary)] hover:text-danger transition-colors p-1 rounded-md hover:bg-[var(--bg-tertiary)]"
          title="Delete chunk"
          aria-label="Delete chunk"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <TextArea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={Math.max(4, Math.min(12, Math.ceil(draft.length / 90)))}
        className="w-full font-sans text-sm"
      />

      {errorMessage && (
        <p className="text-xs text-danger" role="alert">
          {errorMessage}
        </p>
      )}

      <div className="flex items-center justify-end gap-2">
        {justSaved && !dirty && (
          <span className="inline-flex items-center gap-1 text-xs text-success">
            <Check className="h-3.5 w-3.5" />
            Saved
          </span>
        )}
        {dirty && (
          <Button
            size="sm"
            variant="ghost"
            icon={RotateCcw}
            onClick={() => setDraft(chunk.chunk_text)}
            disabled={saving}
          >
            Revert
          </Button>
        )}
        <Button
          size="sm"
          onClick={() => onSave(draft.trim())}
          disabled={!dirty || empty || saving}
          icon={saving ? Loader2 : undefined}
        >
          {saving ? 'Saving…' : 'Save'}
        </Button>
      </div>
    </div>
  )
}
