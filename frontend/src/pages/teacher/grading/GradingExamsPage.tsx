import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScanText, Plus, FileText, AlertCircle } from 'lucide-react'
import { Button, Card, Badge, Modal, Input, Select } from '../../../components/ui'
import { gradingApi, enrollmentApi } from '../../../api/client'
import type { ExamResponse, ExamKind } from '../../../types'

interface SubjectOpt { subject_id: string; code: string; name: string }

const SCHEME_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  pending: 'default', parsing: 'info', review: 'warning', ready: 'success', failed: 'danger',
}

export default function GradingExamsPage() {
  const navigate = useNavigate()
  const [subjects, setSubjects] = useState<SubjectOpt[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [exams, setExams] = useState<ExamResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ title: '', kind: 'test' as ExamKind, max_marks: 50 })

  useEffect(() => {
    enrollmentApi.mySubjects()
      .then((subs) => {
        const opts = subs.map((s) => ({ subject_id: s.subject_id, code: s.code, name: s.name }))
        setSubjects(opts)
        if (opts.length) setSubjectId(opts[0].subject_id)
        else setLoading(false)
      })
      .catch((e) => { setErr(e.detail || 'Failed to load subjects'); setLoading(false) })
  }, [])

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    gradingApi.listExams(subjectId)
      .then(setExams)
      .catch((e) => setErr(e.detail || 'Failed to load exams'))
      .finally(() => setLoading(false))
  }, [subjectId])

  const createExam = async () => {
    if (!form.title.trim() || !subjectId) return
    setCreating(true)
    try {
      const exam = await gradingApi.createExam({
        subject_id: subjectId, title: form.title.trim(), kind: form.kind, max_marks: form.max_marks,
      })
      setShowCreate(false)
      setForm({ title: '', kind: 'test', max_marks: 50 })
      navigate(`/teacher/grading/${exam.id}`)
    } catch (e) {
      setErr((e as { detail?: string }).detail || 'Failed to create exam')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-stat font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <ScanText className="h-6 w-6" /> AI Auto-Grader
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Upload an answer-key scheme + students' handwritten scripts; the AI OCRs and grades them per question and CO.
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} disabled={!subjectId}>
          <Plus className="h-4 w-4" /> New exam
        </Button>
      </div>

      {subjects.length > 0 && (
        <div className="max-w-xs">
          <Select
            label="Subject"
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            options={subjects.map((s) => ({ value: s.subject_id, label: `${s.code} — ${s.name}` }))}
            placeholder="Select a subject"
          />
        </div>
      )}

      {err && (
        <div className="flex items-center gap-2 text-sm rounded-lg p-3" style={{ background: 'var(--bg-tertiary)', color: 'var(--danger, #e5484d)' }}>
          <AlertCircle className="h-4 w-4" /> {err}
        </div>
      )}

      {loading ? (
        <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading…</div>
      ) : subjects.length === 0 ? (
        <Card className="text-center py-10">
          <p style={{ color: 'var(--text-secondary)' }}>You have no subjects yet. Create one under "My Subjects" first.</p>
        </Card>
      ) : exams.length === 0 ? (
        <Card className="text-center py-10">
          <FileText className="h-8 w-8 mx-auto mb-2" style={{ color: 'var(--text-tertiary)' }} />
          <p style={{ color: 'var(--text-secondary)' }}>No exams yet for this subject. Create one to start grading.</p>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {exams.map((exam) => (
            <Card
              key={exam.id}
              className="cursor-pointer hover:shadow-[var(--shadow-card-hover)] transition-shadow"
              onClick={() => navigate(`/teacher/grading/${exam.id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>{exam.title}</div>
                <Badge variant={SCHEME_VARIANT[exam.scheme_status]}>{exam.scheme_status}</Badge>
              </div>
              <div className="flex gap-2 mt-2">
                <Badge variant="info">{exam.kind}</Badge>
                <Badge variant="default">{exam.max_marks} marks</Badge>
              </div>
              <div className="flex gap-4 mt-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                <span>{exam.question_count} questions</span>
                <span>{exam.sheet_count} sheets</span>
                <span>{exam.graded_count} graded</span>
                {exam.review_count > 0 && (
                  <span style={{ color: 'var(--warning, #f5a623)' }}>{exam.review_count} need review</span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New exam">
        <div className="space-y-4">
          <Input label="Title" placeholder="e.g. CIE-2 Test"
            value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <Select label="Type" value={form.kind}
            onChange={(e) => setForm({ ...form, kind: e.target.value as ExamKind })}
            options={[
              { value: 'test', label: 'Test' }, { value: 'quiz', label: 'Quiz' },
              { value: 'experiential', label: 'Experiential' }, { value: 'lab', label: 'Lab' },
              { value: 'see', label: 'SEE' },
            ]} />
          <Input label="Total marks" type="number" value={String(form.max_marks)}
            onChange={(e) => setForm({ ...form, max_marks: Number(e.target.value) || 0 })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={createExam} disabled={creating || !form.title.trim()}>
              {creating ? 'Creating…' : 'Create'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
