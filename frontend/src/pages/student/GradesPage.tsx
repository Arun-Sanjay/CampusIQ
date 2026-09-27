import { useEffect, useState } from 'react'
import { Award, GraduationCap, AlertCircle } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { gradesApi } from '../../api/client'
import type { TranscriptResponse, SubjectGradeRow } from '../../types'

const GRADE_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  O: 'success', 'A+': 'success', A: 'success', 'B+': 'info', B: 'info', C: 'warning', P: 'warning', F: 'danger',
}

function SubjectRow({ s }: { s: SubjectGradeRow }) {
  return (
    <div className="rounded-lg p-3" style={{ background: 'var(--bg-tertiary)' }}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{s.subject_code}</span>
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{s.subject_name}</span>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>· {s.credits} cr</span>
        <div className="ml-auto flex items-center gap-2">
          {s.letter_grade ? (
            <>
              <Badge variant={GRADE_VARIANT[s.letter_grade] || 'default'}>{s.letter_grade}</Badge>
              <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>GP {s.grade_point}</span>
            </>
          ) : (
            <Badge variant="default">in progress</Badge>
          )}
        </div>
      </div>
      <div className="flex gap-4 mt-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
        {s.cie_obtained != null && <span>CIE {s.cie_obtained}/{s.cie_max}</span>}
        {s.see_obtained != null && <span>SEE {s.see_obtained}/{s.see_max}</span>}
        {s.final_rounded != null && <span>Final {s.final_rounded}/100</span>}
        {!s.passed && s.gate_failed !== 'none' && (
          <span style={{ color: 'var(--danger,#e5484d)' }}>failed gate: {s.gate_failed}</span>
        )}
      </div>
      {s.per_co.length > 0 && (
        <div className="mt-2 space-y-1">
          {s.per_co.map((co) => (
            <div key={co.co}>
              <div className="flex justify-between text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
                <span>{co.co}</span><span>{co.obtained}/{co.max} · {co.pct}%</span>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                <div className="h-full rounded-full" style={{ width: `${Math.min(100, co.pct)}%`, background: 'var(--gradient-accent,#6e56cf)' }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function GradesPage() {
  const [data, setData] = useState<TranscriptResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    gradesApi.me()
      .then(setData)
      .catch((e) => setErr(e.detail || 'Failed to load grades'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-stat font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <GraduationCap className="h-6 w-6" /> My Grades
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Your CIE/SEE marks, per-CO attainment, grade points, SGPA and CGPA.
        </p>
      </div>

      {err && (
        <div className="flex items-center gap-2 text-sm rounded-lg p-3" style={{ background: 'var(--bg-tertiary)', color: 'var(--danger,#e5484d)' }}>
          <AlertCircle className="h-4 w-4" /> {err}
        </div>
      )}

      {loading ? (
        <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading…</div>
      ) : !data || data.semesters.length === 0 ? (
        <Card className="text-center py-10">
          <Award className="h-8 w-8 mx-auto mb-2" style={{ color: 'var(--text-tertiary)' }} />
          <p style={{ color: 'var(--text-secondary)' }}>No finalized grades yet. They appear here once your teachers publish them.</p>
        </Card>
      ) : (
        <>
          {/* CGPA hero */}
          <Card>
            <div className="flex items-center gap-4 sm:gap-6">
              <div className="text-center">
                <div className="text-4xl font-bold" style={{ color: 'var(--text-primary)' }}>{data.cgpa.toFixed(2)}</div>
                <div className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>CGPA</div>
              </div>
              <div className="h-10 w-px" style={{ background: 'var(--border-default)' }} />
              <div className="text-center">
                <div className="text-2xl font-semibold" style={{ color: 'var(--text-secondary)' }}>{data.percentage.toFixed(1)}%</div>
                <div className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Equivalent</div>
              </div>
            </div>
          </Card>

          {data.semesters.map((sem) => (
            <Card key={sem.semester}>
              <div className="flex items-center justify-between mb-3">
                <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>Semester {sem.semester}</div>
                <Badge variant="info">SGPA {sem.sgpa.toFixed(2)}</Badge>
              </div>
              <div className="space-y-2">
                {sem.subjects.map((s) => <SubjectRow key={s.subject_id} s={s} />)}
              </div>
            </Card>
          ))}
        </>
      )}
    </div>
  )
}
