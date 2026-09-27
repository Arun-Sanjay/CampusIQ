import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Upload, CheckCircle2, AlertTriangle, RefreshCw, FileCheck, Users, ScanText,
  Pencil, Trash2, Plus,
} from 'lucide-react'
import { Button, Card, Badge, Modal, Select, Input, TextArea } from '../../../components/ui'
import AuthedImage from '../../../components/AuthedImage'
import { gradingApi, enrollmentApi } from '../../../api/client'
import type {
  AnswerSheetDetail, AnswerSheetSummary, CoverScanResult, ExamResponse, ExamAttainmentResponse,
  ReviewQueueItem, SchemeResponse,
} from '../../../types'

type Tab = 'scheme' | 'sheets' | 'cover' | 'review' | 'attainment'

const STATUS_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  uploaded: 'info', ocr: 'info', graded: 'success', review: 'warning', finalized: 'success', failed: 'danger',
}

export default function GradingWorkspacePage() {
  const { examId = '' } = useParams()
  const navigate = useNavigate()
  const [exam, setExam] = useState<ExamResponse | null>(null)
  const [scheme, setScheme] = useState<SchemeResponse | null>(null)
  const [sheets, setSheets] = useState<AnswerSheetSummary[]>([])
  const [roster, setRoster] = useState<{ student_id: string; full_name: string }[]>([])
  const [tab, setTab] = useState<Tab>('scheme')
  const [detail, setDetail] = useState<AnswerSheetDetail | null>(null)
  const [attainment, setAttainment] = useState<ExamAttainmentResponse | null>(null)
  const [reviewItems, setReviewItems] = useState<ReviewQueueItem[]>([])
  const [coverResults, setCoverResults] = useState<CoverScanResult[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const emptyQ = { label: '', question_text: '', model_answer: '', max_marks: 5, co: '', bloom: '' }
  const [qEdit, setQEdit] = useState<{ id?: string } | null>(null)
  const [qForm, setQForm] = useState(emptyQ)
  const schemeFileRef = useRef<HTMLInputElement>(null)
  const sheetsFileRef = useRef<HTMLInputElement>(null)
  const coverFileRef = useRef<HTMLInputElement>(null)

  const refreshExam = useCallback(async () => {
    const [e, s] = await Promise.all([gradingApi.getExam(examId), gradingApi.getScheme(examId)])
    setExam(e)
    setScheme(s)
  }, [examId])

  const refreshSheets = useCallback(async () => {
    setSheets(await gradingApi.listSheets(examId))
  }, [examId])

  useEffect(() => {
    refreshExam().catch((e) => setMsg(e.detail || 'Failed to load exam'))
  }, [refreshExam])

  useEffect(() => {
    if (!exam) return
    enrollmentApi.roster(exam.subject_id)
      .then((r) => setRoster(r.students.map((s) => ({ student_id: s.student_id, full_name: s.full_name }))))
      .catch(() => {})
  }, [exam])

  useEffect(() => {
    if (tab === 'sheets') refreshSheets().catch(() => {})
    if (tab === 'attainment') gradingApi.attainment(examId).then(setAttainment).catch(() => {})
    if (tab === 'review') gradingApi.reviewQueue(examId).then(setReviewItems).catch(() => {})
  }, [tab, examId, refreshSheets])

  // Poll while a scheme is parsing or any sheet is still being graded.
  useEffect(() => {
    const schemeParsing = exam && ['pending', 'parsing'].includes(exam.scheme_status) && exam.question_count === 0
    const gradingActive = sheets.some((s) => ['uploaded', 'ocr'].includes(s.status))
    if (!schemeParsing && !gradingActive) return
    const id = setInterval(() => {
      if (schemeParsing) refreshExam().catch(() => {})
      if (gradingActive) refreshSheets().catch(() => {})
    }, 3000)
    return () => clearInterval(id)
  }, [exam, sheets, refreshExam, refreshSheets])

  const onUploadScheme = async (file: File) => {
    setBusy(true); setMsg('Uploading scheme — AI is parsing it…')
    try { await gradingApi.uploadScheme(examId, file); await refreshExam() }
    catch (e) { setMsg((e as { detail?: string }).detail || 'Scheme upload failed') }
    finally { setBusy(false) }
  }

  const onConfirmScheme = async () => {
    setBusy(true)
    try { await gradingApi.confirmScheme(examId); await refreshExam(); setMsg('Scheme confirmed — ready to grade.'); setTab('sheets') }
    catch (e) { setMsg((e as { detail?: string }).detail || 'Confirm failed') }
    finally { setBusy(false) }
  }

  const onUploadSheets = async (files: FileList) => {
    setBusy(true); setMsg('Uploading & grading… this runs in the background.')
    try {
      await gradingApi.uploadBatch(examId, Array.from(files))
      await refreshSheets()
    } catch (e) { setMsg((e as { detail?: string }).detail || 'Upload failed') }
    finally { setBusy(false) }
  }

  const onScanCovers = async (files: FileList) => {
    setBusy(true); setMsg('Scanning cover pages with AI…')
    try {
      const res = await gradingApi.scanCover(examId, Array.from(files))
      setCoverResults(res)
      const saved = res.filter((r) => r.saved).length
      setMsg(`Scanned ${res.length} · saved ${saved} to students`
        + (saved < res.length ? ` · ${res.length - saved} need a student match` : ''))
    } catch (e) { setMsg((e as { detail?: string }).detail || 'Cover scan failed') }
    finally { setBusy(false) }
  }

  const assignCover = async (idx: number, studentId: string) => {
    const r = coverResults[idx]
    if (!studentId || !r) return
    try {
      await gradingApi.enterResults(examId, [{ student_id: studentId, total_obtained: r.total_obtained, per_co: r.per_co }])
      setCoverResults((prev) => prev.map((x, i) => i === idx
        ? { ...x, saved: true, student_id: studentId, message: null,
            matched_student_name: roster.find((s) => s.student_id === studentId)?.full_name || null }
        : x))
    } catch (e) { setMsg((e as { detail?: string }).detail || 'Save failed') }
  }

  const openSheet = async (id: string) => setDetail(await gradingApi.getSheet(id))

  const override = async (gradeId: string, marks: number) => {
    await gradingApi.overrideGrade(gradeId, marks)
    if (detail) setDetail(await gradingApi.getSheet(detail.id))
    await refreshSheets()
  }

  const matchStudent = async (sheetId: string, studentId: string) => {
    await gradingApi.setMatch(sheetId, studentId || null)
    if (detail) setDetail(await gradingApi.getSheet(sheetId))
    await refreshSheets()
  }

  const finalize = async (sheetId: string) => {
    try {
      await gradingApi.finalizeSheet(sheetId)
      if (detail) setDetail(await gradingApi.getSheet(sheetId))
      await refreshSheets()
    } catch (e) { setMsg((e as { detail?: string }).detail || 'Finalize failed') }
  }

  const openAddQuestion = () => { setQForm(emptyQ); setQEdit({}) }
  const openEditQuestion = (q: { id: string; label: string; question_text: string; model_answer: string | null; max_marks: number; co: string | null; bloom: string | null }) => {
    setQForm({ label: q.label, question_text: q.question_text, model_answer: q.model_answer || '', max_marks: q.max_marks, co: q.co || '', bloom: q.bloom || '' })
    setQEdit({ id: q.id })
  }
  const saveQuestion = async () => {
    if (!qForm.label.trim() || !qForm.question_text.trim()) return
    const payload = {
      label: qForm.label.trim(), question_text: qForm.question_text.trim(),
      model_answer: qForm.model_answer || null, max_marks: Number(qForm.max_marks) || 0,
      co: qForm.co || null, bloom: qForm.bloom || null,
    }
    try {
      if (qEdit?.id) await gradingApi.updateQuestion(examId, qEdit.id, payload)
      else await gradingApi.addQuestion(examId, payload)
      setQEdit(null)
      await refreshExam()
    } catch (e) { setMsg((e as { detail?: string }).detail || 'Save failed') }
  }
  const deleteQuestion = async (id: string) => {
    try { await gradingApi.deleteQuestion(examId, id); await refreshExam() }
    catch (e) { setMsg((e as { detail?: string }).detail || 'Delete failed') }
  }

  if (!exam) return <div className="p-6 text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading…</div>

  const tabs: { key: Tab; label: string }[] = [
    { key: 'scheme', label: 'Scheme' },
    { key: 'sheets', label: 'Answer Sheets' },
    { key: 'cover', label: 'Auto Marks' },
    { key: 'review', label: 'Review Queue' },
    { key: 'attainment', label: 'CO Attainment' },
  ]

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <button onClick={() => navigate('/teacher/grading')} className="flex items-center gap-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
        <ArrowLeft className="h-4 w-4" /> All exams
      </button>

      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-stat font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <ScanText className="h-6 w-6" /> {exam.title}
          </h1>
          <div className="flex gap-2 mt-2">
            <Badge variant="info">{exam.kind}</Badge>
            <Badge variant="default">{exam.max_marks} marks</Badge>
            <Badge variant={exam.scheme_status === 'ready' ? 'success' : 'warning'}>scheme: {exam.scheme_status}</Badge>
          </div>
        </div>
      </div>

      {msg && (
        <div className="text-sm rounded-lg p-3 flex items-center justify-between" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
          <span>{msg}</span>
          <button onClick={() => setMsg(null)} style={{ color: 'var(--text-tertiary)' }}>✕</button>
        </div>
      )}

      <div className="flex gap-1 border-b overflow-x-auto scroll-touch" style={{ borderColor: 'var(--border-default)' }}>
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className="px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap"
            style={{
              color: tab === t.key ? 'var(--text-primary)' : 'var(--text-tertiary)',
              borderBottom: tab === t.key ? '2px solid var(--text-primary)' : '2px solid transparent',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Scheme tab ── */}
      {tab === 'scheme' && (
        <div className="space-y-4">
          <Card>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>Marking scheme</div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Upload the question paper that includes the model answers + marks + CO tags. The AI parses it; review, then confirm.
                </p>
              </div>
              <div className="flex gap-2">
                <input ref={schemeFileRef} type="file" accept="application/pdf,image/*" className="hidden"
                  onChange={(e) => e.target.files?.[0] && onUploadScheme(e.target.files[0])} />
                <Button variant="secondary" onClick={() => schemeFileRef.current?.click()} disabled={busy}>
                  <Upload className="h-4 w-4" /> Upload scheme PDF
                </Button>
                <Button variant="ghost" onClick={() => refreshExam()}><RefreshCw className="h-4 w-4" /></Button>
              </div>
            </div>
          </Card>

          {(scheme?.questions.length ?? 0) === 0 ? (
            <Card className="text-center py-8">
              <p style={{ color: 'var(--text-secondary)' }}>
                {['pending', 'parsing'].includes(exam.scheme_status)
                  ? 'AI is parsing the scheme — this updates automatically…'
                  : exam.scheme_status === 'failed'
                    ? 'Parsing failed. Try a clearer PDF, or add questions manually below.'
                    : 'No questions yet. Upload a scheme PDF above, or add questions manually.'}
              </p>
              <div className="mt-3">
                <Button variant="secondary" onClick={openAddQuestion}><Plus className="h-4 w-4" /> Add question manually</Button>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="flex items-center justify-between mb-3">
                <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {scheme!.questions.length} questions · {exam.max_marks} marks
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={openAddQuestion}><Plus className="h-4 w-4" /> Add question</Button>
                  {exam.scheme_status !== 'ready' && (
                    <Button onClick={onConfirmScheme} disabled={busy}>
                      <CheckCircle2 className="h-4 w-4" /> Confirm scheme
                    </Button>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                {scheme!.questions.map((q) => (
                  <div key={q.id} className="rounded-lg p-3 text-sm" style={{ background: 'var(--bg-tertiary)' }}>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="default">{q.label}</Badge>
                      <Badge variant="info">{q.max_marks} m</Badge>
                      {q.co && <Badge variant="default">{q.co}</Badge>}
                      {q.bloom && <Badge variant="default">{q.bloom}</Badge>}
                      <div className="ml-auto flex gap-1">
                        <button title="Edit" onClick={() => openEditQuestion(q)} style={{ color: 'var(--text-tertiary)' }}><Pencil className="h-3.5 w-3.5" /></button>
                        <button title="Delete" onClick={() => deleteQuestion(q.id)} style={{ color: 'var(--danger, #e5484d)' }}><Trash2 className="h-3.5 w-3.5" /></button>
                      </div>
                    </div>
                    <div style={{ color: 'var(--text-primary)' }}>{q.question_text}</div>
                    {q.model_answer && (
                      <div className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>Ans: {q.model_answer}</div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Answer sheets tab ── */}
      {tab === 'sheets' && (
        <div className="space-y-4">
          {exam.scheme_status !== 'ready' ? (
            <Card className="text-center py-8">
              <AlertTriangle className="h-6 w-6 mx-auto mb-2" style={{ color: 'var(--warning, #f5a623)' }} />
              <p style={{ color: 'var(--text-secondary)' }}>Confirm the scheme before uploading answer sheets.</p>
            </Card>
          ) : (
            <>
              <Card>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    Upload all students' scripts (one image/PDF per student, or many at once). The AI grades each in the background.
                  </div>
                  <div className="flex gap-2">
                    <input ref={sheetsFileRef} type="file" accept="application/pdf,image/*" multiple className="hidden"
                      onChange={(e) => e.target.files?.length && onUploadSheets(e.target.files)} />
                    <Button onClick={() => sheetsFileRef.current?.click()} disabled={busy}>
                      <Upload className="h-4 w-4" /> Upload sheets
                    </Button>
                    <Button variant="ghost" onClick={() => refreshSheets()}><RefreshCw className="h-4 w-4" /></Button>
                  </div>
                </div>
              </Card>

              {sheets.length === 0 ? (
                <Card className="text-center py-8"><p style={{ color: 'var(--text-secondary)' }}>No sheets uploaded yet.</p></Card>
              ) : (
                <Card>
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>{sheets.length} sheets</div>
                    <Button variant="secondary" size="sm" onClick={async () => { await gradingApi.finalizeAll(examId); await refreshSheets() }}>
                      <FileCheck className="h-4 w-4" /> Finalize all graded
                    </Button>
                  </div>
                  <div className="space-y-1">
                    {sheets.map((s) => (
                      <button key={s.id} onClick={() => openSheet(s.id)}
                        className="w-full flex items-center gap-3 rounded-lg p-2 text-left text-sm hover:opacity-90"
                        style={{ background: 'var(--bg-tertiary)' }}>
                        <Badge variant={STATUS_VARIANT[s.status]}>{s.status}</Badge>
                        <span className="flex-1 truncate" style={{ color: 'var(--text-primary)' }}>
                          {s.matched_student_name || s.detected_name || s.detected_usn || 'Unmatched'}
                          {s.matched_student_usn && <span style={{ color: 'var(--text-tertiary)' }}> · {s.matched_student_usn}</span>}
                        </span>
                        {s.total_awarded != null && (
                          <span style={{ color: 'var(--text-secondary)' }}>{s.total_awarded}/{s.total_max}</span>
                        )}
                        {s.needs_review_count > 0 && <Badge variant="warning">{s.needs_review_count} review</Badge>}
                      </button>
                    ))}
                  </div>
                </Card>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Auto Marks Assigner (cover-page scan) ── */}
      {tab === 'cover' && (
        <div className="space-y-4">
          <Card>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="min-w-0">
                <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>Auto Marks Assigner</div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Upload the FRONT/cover page of each answer booklet. The AI reads the marks tally
                  already written on it and records the CO marks straight to the matched student —
                  no per-question grading. (No scheme needed.)
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <input ref={coverFileRef} type="file" accept="application/pdf,image/*" multiple className="hidden"
                  onChange={(e) => e.target.files?.length && onScanCovers(e.target.files)} />
                <Button onClick={() => coverFileRef.current?.click()} disabled={busy} className="whitespace-nowrap">
                  <ScanText className="h-4 w-4" /> Scan cover pages
                </Button>
              </div>
            </div>
          </Card>

          {coverResults.length > 0 && (
            <Card>
              <div className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>{coverResults.length} scanned</div>
              <div className="space-y-2">
                {coverResults.map((r, i) => (
                  <div key={i} className="rounded-lg p-3 text-sm" style={{ background: 'var(--bg-tertiary)' }}>
                    <div className="flex items-center gap-2 flex-wrap">
                      {r.saved ? <Badge variant="success">saved</Badge> : <Badge variant="warning">unmatched</Badge>}
                      <span style={{ color: 'var(--text-primary)' }}>
                        {r.matched_student_name || r.detected_name || r.detected_usn || 'Unknown student'}
                      </span>
                      {r.detected_usn && <span style={{ color: 'var(--text-tertiary)' }}>· {r.detected_usn}</span>}
                      <span className="ml-auto font-medium" style={{ color: 'var(--text-secondary)' }}>{r.total_obtained}/{r.total_max}</span>
                    </div>
                    {r.per_co && Object.keys(r.per_co).length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {Object.entries(r.per_co).map(([co, v]) => (
                          <Badge key={co} variant="default">{co}: {v.obtained}/{v.max}</Badge>
                        ))}
                      </div>
                    )}
                    {!r.saved && (
                      <div className="flex items-center gap-2 mt-2">
                        <Select className="!w-56" defaultValue="" placeholder="Pick student to save…"
                          onChange={(e) => assignCover(i, e.target.value)}
                          options={roster.map((s) => ({ value: s.student_id, label: s.full_name }))} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Review queue tab ── */}
      {tab === 'review' && (
        <Card>
          {reviewItems.length === 0 ? (
            <p className="text-center py-6" style={{ color: 'var(--text-secondary)' }}>Nothing flagged for review. 🎉</p>
          ) : (
            <div className="space-y-2">
              {reviewItems.map((r) => (
                <div key={r.question_grade_id} className="rounded-lg p-3 text-sm" style={{ background: 'var(--bg-tertiary)' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="warning">Q{r.label}</Badge>
                    <span style={{ color: 'var(--text-primary)' }}>{r.student_name || 'Unmatched'}</span>
                    <span className="ml-auto" style={{ color: 'var(--text-tertiary)' }}>
                      AI: {r.awarded_marks}/{r.max_marks} · conf {r.confidence ?? '—'}
                    </span>
                  </div>
                  {r.extracted_answer && <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.extracted_answer}</div>}
                  {r.rationale && <div className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>Why: {r.rationale}</div>}
                  <div className="flex items-center gap-2 mt-2">
                    <input type="number" min={0} max={r.max_marks} defaultValue={r.awarded_marks}
                      id={`rq-${r.question_grade_id}`} className="input-base w-20" />
                    <Button size="sm" onClick={async () => {
                      const el = document.getElementById(`rq-${r.question_grade_id}`) as HTMLInputElement
                      await gradingApi.overrideGrade(r.question_grade_id, Number(el.value))
                      setReviewItems(await gradingApi.reviewQueue(examId))
                    }}>Approve</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* ── Attainment tab ── */}
      {tab === 'attainment' && (
        <Card>
          {!attainment ? (
            <p style={{ color: 'var(--text-tertiary)' }}>Loading…</p>
          ) : attainment.graded_students === 0 ? (
            <p className="text-center py-6" style={{ color: 'var(--text-secondary)' }}>No graded results yet.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <Users className="h-4 w-4" /> {attainment.graded_students} students · class total {attainment.total_obtained}/{attainment.total_max} ({attainment.total_pct}%)
              </div>
              {attainment.per_co.map((co) => (
                <div key={co.co}>
                  <div className="flex justify-between text-sm mb-1" style={{ color: 'var(--text-primary)' }}>
                    <span>{co.co}</span>
                    <span>{co.obtained}/{co.max} · {co.pct}%</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
                    <div className="h-full rounded-full" style={{ width: `${Math.min(100, co.pct)}%`, background: 'var(--gradient-accent, #6e56cf)' }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* ── Per-student detail modal ── */}
      <Modal isOpen={!!detail} onClose={() => setDetail(null)} title={detail?.matched_student_name || 'Answer sheet'} size="xl">
        {detail && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={STATUS_VARIANT[detail.status]}>{detail.status}</Badge>
              <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{detail.total_awarded}/{detail.total_max}</span>
              <div className="ml-auto flex items-center gap-2">
                <Select className="!w-48" value={detail.student_id || ''}
                  onChange={(e) => matchStudent(detail.id, e.target.value)}
                  placeholder="Match student…"
                  options={roster.map((r) => ({ value: r.student_id, label: r.full_name }))} />
                <Button size="sm" onClick={() => finalize(detail.id)}>
                  <FileCheck className="h-4 w-4" /> Finalize
                </Button>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                {detail.page_files.map((_, i) => (
                  <AuthedImage key={i} url={gradingApi.pageUrl(detail.id, i)} className="w-full rounded-lg border" />
                ))}
              </div>
              <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                {detail.grades.map((g) => (
                  <div key={g.id} className="rounded-lg p-3 text-sm" style={{ background: 'var(--bg-tertiary)' }}>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="default">Q{g.label}</Badge>
                      {g.co && <Badge variant="default">{g.co}</Badge>}
                      {g.needs_review && <Badge variant="warning">review</Badge>}
                      {g.is_overridden && <Badge variant="success">overridden</Badge>}
                    </div>
                    {g.extracted_answer && <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{g.extracted_answer}</div>}
                    {g.rationale && <div className="text-xs mb-2" style={{ color: 'var(--text-tertiary)' }}>Why: {g.rationale}</div>}
                    <div className="flex items-center gap-2">
                      <input type="number" min={0} max={g.max_marks} defaultValue={g.effective_marks}
                        id={`g-${g.id}`} className="input-base w-20" />
                      <span style={{ color: 'var(--text-tertiary)' }}>/ {g.max_marks}</span>
                      <Button size="sm" variant="secondary" onClick={() => {
                        const el = document.getElementById(`g-${g.id}`) as HTMLInputElement
                        override(g.id, Number(el.value))
                      }}>Save</Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Add / edit question modal ── */}
      <Modal isOpen={!!qEdit} onClose={() => setQEdit(null)} title={qEdit?.id ? 'Edit question' : 'Add question'}>
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Input label="Label" value={qForm.label} onChange={(e) => setQForm({ ...qForm, label: e.target.value })} />
            <Input label="Marks" type="number" value={String(qForm.max_marks)} onChange={(e) => setQForm({ ...qForm, max_marks: Number(e.target.value) || 0 })} />
            <Input label="CO" placeholder="CO1" value={qForm.co} onChange={(e) => setQForm({ ...qForm, co: e.target.value })} />
          </div>
          <TextArea label="Question" value={qForm.question_text} onChange={(e) => setQForm({ ...qForm, question_text: e.target.value })} />
          <TextArea label="Model answer" value={qForm.model_answer} onChange={(e) => setQForm({ ...qForm, model_answer: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setQEdit(null)}>Cancel</Button>
            <Button onClick={saveQuestion} disabled={!qForm.label.trim() || !qForm.question_text.trim()}>Save</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
