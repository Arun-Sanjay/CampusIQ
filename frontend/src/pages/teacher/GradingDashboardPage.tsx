import { useEffect, useState } from 'react'
import { BarChart3, AlertCircle } from 'lucide-react'
import { Card, Badge, Select, ResponsiveTable, type ResponsiveColumn } from '../../components/ui'
import { gradesApi, enrollmentApi } from '../../api/client'
import type { ClassGradeOverview, ClassGradeRow } from '../../types'

const GRADE_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  O: 'success', 'A+': 'success', A: 'success', 'B+': 'info', B: 'info', C: 'warning', P: 'warning', F: 'danger',
}

export default function GradingDashboardPage() {
  const [subjects, setSubjects] = useState<{ subject_id: string; code: string; name: string }[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [data, setData] = useState<ClassGradeOverview | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    enrollmentApi.mySubjects()
      .then((subs) => {
        const opts = subs.map((s) => ({ subject_id: s.subject_id, code: s.code, name: s.name }))
        setSubjects(opts)
        if (opts.length) setSubjectId(opts[0].subject_id)
      })
      .catch((e) => setErr(e.detail || 'Failed to load subjects'))
  }, [])

  useEffect(() => {
    if (!subjectId) return
    gradesApi.classOverview(subjectId).then(setData).catch((e) => setErr(e.detail || 'Failed to load grades'))
  }, [subjectId])

  const gradeColumns: ResponsiveColumn<ClassGradeRow>[] = [
    { key: 'student', header: 'Student', primary: true, render: (s) => s.student_name },
    {
      key: 'usn',
      header: 'USN',
      className: 'text-[var(--text-tertiary)]',
      render: (s) => s.usn || '—',
    },
    {
      key: 'cie',
      header: 'CIE',
      render: (s) => (s.cie_obtained != null ? `${s.cie_obtained}/${s.cie_max}` : '—'),
    },
    { key: 'see', header: 'SEE', render: (s) => (s.see_obtained != null ? s.see_obtained : '—') },
    { key: 'final', header: 'Final', render: (s) => (s.final_score != null ? s.final_score : '—') },
    {
      key: 'grade',
      header: 'Grade',
      render: (s) =>
        s.letter_grade ? (
          <Badge variant={GRADE_VARIANT[s.letter_grade] || 'default'}>{s.letter_grade}</Badge>
        ) : (
          <span className="text-[var(--text-tertiary)]">—</span>
        ),
    },
    { key: 'gp', header: 'GP', render: (s) => s.grade_point ?? '—' },
    {
      key: 'status',
      header: 'Status',
      render: (s) =>
        s.finalized ? (
          <Badge variant="success">final</Badge>
        ) : (
          <Badge variant="default">provisional</Badge>
        ),
    },
  ]

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-stat font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <BarChart3 className="h-6 w-6" /> Class Grades
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Final grades + class CO attainment, assembled from CIE (quizzes/tests/auto-graded) and SEE.
        </p>
      </div>

      {subjects.length > 0 && (
        <div className="max-w-xs">
          <Select label="Subject" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}
            options={subjects.map((s) => ({ value: s.subject_id, label: `${s.code} — ${s.name}` }))}
            placeholder="Select a subject" />
        </div>
      )}

      {err && (
        <div className="flex items-center gap-2 text-sm rounded-lg p-3" style={{ background: 'var(--bg-tertiary)', color: 'var(--danger,#e5484d)' }}>
          <AlertCircle className="h-4 w-4" /> {err}
        </div>
      )}

      {data && (
        <>
          {data.co_attainment.length > 0 && (
            <Card>
              <div className="font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Class CO attainment</div>
              <div className="space-y-2">
                {data.co_attainment.map((co) => (
                  <div key={co.co}>
                    <div className="flex justify-between text-sm mb-1" style={{ color: 'var(--text-primary)' }}>
                      <span>{co.co}</span><span>{co.obtained}/{co.max} · {co.pct}%</span>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
                      <div className="h-full rounded-full" style={{ width: `${Math.min(100, co.pct)}%`, background: 'var(--gradient-accent,#6e56cf)' }} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <div className="font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
              Students ({data.students.length})
            </div>
            <ResponsiveTable
              columns={gradeColumns}
              rows={data.students}
              rowKey={(s) => s.student_id}
              empty={
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No students enrolled yet.</p>
              }
            />
          </Card>
        </>
      )}
    </div>
  )
}
