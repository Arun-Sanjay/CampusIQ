/**
 * Two-pane chunk editor for the Knowledge Editor.
 *
 *   ┌── Left rail ──┐ ┌── Right pane ─────────────────────┐
 *   │ Search…       │ │ doc header + actions              │
 *   │ ▾ HANDBOOK    │ │ ┌─────────────────────────────┐  │
 *   │   • Handbook  │ │ │ Chunk #1   [textarea]       │  │
 *   │ ▾ TIMETABLE   │ │ │ Save · Revert · Delete      │  │
 *   │   • Spring'26 │ │ └─────────────────────────────┘  │
 *   │ ▸ PLACEMENT…  │ │ … more chunks …                  │
 *   │               │ │ [+ Add new chunk]                │
 *   └───────────────┘ └───────────────────────────────────┘
 *
 * Selection is local state; the parent only passes the doc pool and an
 * `onApplied` callback (fires when QuickUpdateBar / chat applies an
 * edit to a doc, so this pane can refetch chunks for that doc).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ChevronRight,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import TextArea from '../ui/TextArea'
import ChunkCard from './ChunkCard'
import { ApiError, collegeDocumentsApi } from '../../api/client'
import type {
  CollegeDocument,
  CollegeDocumentCategory,
  DocumentChunkPreview,
} from '../../types'

const CATEGORY_ORDER: CollegeDocumentCategory[] = [
  'handbook',
  'timetable',
  'placement_record',
  'faculty_list',
  'hostel_rules',
  'other',
]

const CATEGORY_LABEL: Record<CollegeDocumentCategory, string> = {
  handbook: 'Handbook',
  timetable: 'Timetable',
  placement_record: 'Placement Records',
  faculty_list: 'Faculty List',
  hostel_rules: 'Hostel Rules',
  other: 'Other',
}

export interface ChunkEditorListProps {
  documents: CollegeDocument[]
  pushToast: (title: string, body: string, isError?: boolean) => void
  /** Token whose value changes whenever an external action (QuickUpdate /
   *  chat) applied an edit; we use it to refetch the active doc's chunks. */
  refreshKey: number
  refreshDocumentId: string | null
  onReprocess: (documentId: string) => void
}

interface ChunkSaveState {
  saving: boolean
  justSaved: boolean
  error: string | null
}

export default function ChunkEditorList({
  documents,
  pushToast,
  refreshKey,
  refreshDocumentId,
  onReprocess,
}: ChunkEditorListProps) {
  const [search, setSearch] = useState('')
  const [openCategories, setOpenCategories] = useState<
    Record<CollegeDocumentCategory, boolean>
  >({
    handbook: true,
    timetable: true,
    placement_record: true,
    faculty_list: false,
    hostel_rules: false,
    other: false,
  })
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [chunks, setChunks] = useState<DocumentChunkPreview[]>([])
  const [loadingChunks, setLoadingChunks] = useState(false)
  const [saveStates, setSaveStates] = useState<Record<string, ChunkSaveState>>({})
  const [addingChunk, setAddingChunk] = useState(false)
  const [newChunkDraft, setNewChunkDraft] = useState('')
  const [creatingChunk, setCreatingChunk] = useState(false)
  const savedTimers = useRef<Record<string, number>>({})

  const docsByCategory = useMemo(() => {
    const grouped: Record<CollegeDocumentCategory, CollegeDocument[]> = {
      handbook: [],
      timetable: [],
      placement_record: [],
      faculty_list: [],
      hostel_rules: [],
      other: [],
    }
    const filter = search.trim().toLowerCase()
    for (const d of documents) {
      if (filter && !d.title.toLowerCase().includes(filter)) continue
      grouped[d.document_category].push(d)
    }
    return grouped
  }, [documents, search])

  const fetchChunks = useCallback(async (docId: string) => {
    setLoadingChunks(true)
    try {
      const list = await collegeDocumentsApi.listChunks(docId)
      setChunks(list)
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not load chunks.'
      pushToast('Failed to load chunks', detail, true)
    } finally {
      setLoadingChunks(false)
    }
  }, [pushToast])

  useEffect(() => {
    if (selectedDocId) void fetchChunks(selectedDocId)
    else setChunks([])
  }, [selectedDocId, fetchChunks])

  // External refresh signal (QuickUpdate / chat applied a change to a
  // specific doc — refetch if it's the one we're viewing).
  useEffect(() => {
    if (
      refreshKey > 0 &&
      selectedDocId &&
      refreshDocumentId === selectedDocId
    ) {
      void fetchChunks(selectedDocId)
    }
  }, [refreshKey, refreshDocumentId, selectedDocId, fetchChunks])

  const setSaveState = (chunkId: string, state: ChunkSaveState) =>
    setSaveStates((prev) => ({ ...prev, [chunkId]: state }))

  const handleChunkSave = async (chunk: DocumentChunkPreview, newText: string) => {
    if (!selectedDocId) return
    setSaveState(chunk.id, { saving: true, justSaved: false, error: null })
    try {
      const updated = await collegeDocumentsApi.updateChunk(
        selectedDocId,
        chunk.id,
        { chunk_text: newText },
      )
      setChunks((prev) => prev.map((c) => (c.id === chunk.id ? updated : c)))
      setSaveState(chunk.id, { saving: false, justSaved: true, error: null })
      // Clear the green check after a short delay.
      if (savedTimers.current[chunk.id]) {
        window.clearTimeout(savedTimers.current[chunk.id])
      }
      savedTimers.current[chunk.id] = window.setTimeout(() => {
        setSaveState(chunk.id, { saving: false, justSaved: false, error: null })
      }, 1500)
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Save failed.'
      setSaveState(chunk.id, { saving: false, justSaved: false, error: detail })
    }
  }

  const handleChunkDelete = async (chunk: DocumentChunkPreview) => {
    if (!selectedDocId) return
    if (
      !window.confirm(
        `Delete chunk #${chunk.chunk_index + 1}? This removes it from CollegeGPT immediately.`,
      )
    ) {
      return
    }
    try {
      await collegeDocumentsApi.deleteChunk(selectedDocId, chunk.id)
      setChunks((prev) => prev.filter((c) => c.id !== chunk.id))
      pushToast('Chunk deleted', `Chunk #${chunk.chunk_index + 1} removed.`)
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Delete failed.'
      pushToast('Delete failed', detail, true)
    }
  }

  const handleCreateChunk = async () => {
    if (!selectedDocId) return
    const trimmed = newChunkDraft.trim()
    if (trimmed.length < 10) {
      pushToast('Too short', 'Add at least 10 characters before saving.', true)
      return
    }
    setCreatingChunk(true)
    try {
      const created = await collegeDocumentsApi.createChunk(selectedDocId, {
        chunk_text: trimmed,
      })
      setChunks((prev) => [...prev, created])
      setNewChunkDraft('')
      setAddingChunk(false)
      pushToast('Chunk added', `Chunk #${created.chunk_index + 1} created.`)
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not add chunk.'
      pushToast('Add failed', detail, true)
    } finally {
      setCreatingChunk(false)
    }
  }

  const activeDoc = useMemo(
    () => documents.find((d) => d.id === selectedDocId) ?? null,
    [documents, selectedDocId],
  )

  return (
    <div className="grid grid-cols-[16rem_1fr] gap-4 min-h-[480px]">
      {/* Left rail */}
      <aside
        className="rounded-card border p-3 space-y-3 max-h-[calc(100vh-260px)] overflow-y-auto"
        style={{
          background: 'var(--bg-elevated)',
          borderColor: 'var(--border-default)',
        }}
      >
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--text-tertiary)]" />
          <input
            className="input-base w-full pl-8 pr-2 py-1.5 text-xs"
            placeholder="Filter docs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {CATEGORY_ORDER.map((cat) => {
          const items = docsByCategory[cat]
          if (items.length === 0) return null
          const isOpen = openCategories[cat]
          return (
            <div key={cat}>
              <button
                onClick={() =>
                  setOpenCategories((prev) => ({ ...prev, [cat]: !isOpen }))
                }
                className="w-full flex items-center justify-between text-[10.5px] uppercase tracking-wider text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] py-1"
              >
                <span className="flex items-center gap-1.5">
                  <ChevronRight
                    className={`h-3 w-3 transition-transform ${
                      isOpen ? 'rotate-90' : ''
                    }`}
                  />
                  {CATEGORY_LABEL[cat]}
                </span>
                <span>{items.length}</span>
              </button>
              {isOpen && (
                <div className="space-y-0.5 ml-3">
                  {items.map((d) => {
                    const active = d.id === selectedDocId
                    return (
                      <button
                        key={d.id}
                        onClick={() => setSelectedDocId(d.id)}
                        className={`w-full text-left text-xs px-2 py-1.5 rounded-md transition-colors truncate ${
                          active
                            ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] font-medium'
                            : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
                        }`}
                        title={d.title}
                      >
                        {d.title}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {documents.length === 0 && (
          <p className="text-xs text-[var(--text-tertiary)] py-4 text-center">
            No college documents yet — upload one on the College Documents page.
          </p>
        )}
      </aside>

      {/* Right pane */}
      <section className="space-y-3">
        {!activeDoc && (
          <div
            className="rounded-card border p-12 text-center"
            style={{
              background: 'var(--bg-elevated)',
              borderColor: 'var(--border-default)',
            }}
          >
            <p className="text-sm text-[var(--text-tertiary)]">
              Select a document on the left to edit its facts.
            </p>
          </div>
        )}

        {activeDoc && (
          <>
            <motion.div
              key={activeDoc.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="rounded-card border p-3 flex items-center justify-between gap-2"
              style={{
                background: 'var(--bg-elevated)',
                borderColor: 'var(--border-default)',
              }}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">
                    {activeDoc.title}
                  </h3>
                  <Badge size="sm" variant="info">
                    {activeDoc.document_category.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-[var(--text-tertiary)]">
                    {chunks.length} chunks
                  </span>
                </div>
                <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">
                  Edits update CollegeGPT instantly. The original PDF stays as
                  a historical upload artifact.
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                icon={RefreshCw}
                onClick={() => {
                  if (
                    window.confirm(
                      'Reprocessing rebuilds chunks from the original file. All manual edits to this document will be lost. Continue?',
                    )
                  ) {
                    onReprocess(activeDoc.id)
                  }
                }}
              >
                Reprocess
              </Button>
            </motion.div>

            {loadingChunks && (
              <div className="space-y-3">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="rounded-card border p-4 animate-pulse h-32"
                    style={{
                      background: 'var(--bg-elevated)',
                      borderColor: 'var(--border-default)',
                    }}
                  />
                ))}
              </div>
            )}

            {!loadingChunks && chunks.length === 0 && (
              <div
                className="rounded-card border p-8 text-center space-y-2"
                style={{
                  background: 'var(--bg-elevated)',
                  borderColor: 'var(--border-default)',
                }}
              >
                <p className="text-sm text-[var(--text-tertiary)]">
                  No chunks yet — try reprocessing the document or add one
                  manually below.
                </p>
              </div>
            )}

            {!loadingChunks &&
              chunks.map((chunk) => {
                const state = saveStates[chunk.id] ?? {
                  saving: false,
                  justSaved: false,
                  error: null,
                }
                return (
                  <ChunkCard
                    key={chunk.id}
                    chunk={chunk}
                    saving={state.saving}
                    justSaved={state.justSaved}
                    errorMessage={state.error}
                    onSave={(newText) => void handleChunkSave(chunk, newText)}
                    onDelete={() => void handleChunkDelete(chunk)}
                  />
                )
              })}

            {/* Add-new-chunk tile */}
            {!loadingChunks && !addingChunk && (
              <button
                onClick={() => setAddingChunk(true)}
                className="w-full rounded-card border-2 border-dashed py-5 text-sm flex items-center justify-center gap-2 transition-colors text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                style={{ borderColor: 'var(--border-default)' }}
              >
                <Plus className="h-4 w-4" />
                Add new chunk
              </button>
            )}

            {addingChunk && (
              <div
                className="rounded-card border p-4 space-y-2"
                style={{
                  background: 'var(--bg-elevated)',
                  borderColor: 'var(--border-default)',
                }}
              >
                <TextArea
                  label="New chunk text"
                  value={newChunkDraft}
                  onChange={(e) => setNewChunkDraft(e.target.value)}
                  rows={6}
                  placeholder="Add a self-contained paragraph that will be embedded for CollegeGPT retrieval."
                />
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setAddingChunk(false)
                      setNewChunkDraft('')
                    }}
                    disabled={creatingChunk}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => void handleCreateChunk()}
                    loading={creatingChunk}
                    disabled={newChunkDraft.trim().length < 10}
                  >
                    Save chunk
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
