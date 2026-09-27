import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { motion, type Variants } from 'framer-motion'
import { AlertCircle, Loader2, UserPlus, Trash2, Users, Info } from 'lucide-react'
import { clsx } from 'clsx'
import { ApiError, enrollmentApi } from '../../api/client'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Avatar from '../../components/ui/Avatar'
import type { EnrolledStudent, SubjectRoster, TeacherSubjectCount } from '../../types'

const fadeUp: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

export default function EnrollmentPage() {
  const [subjects, setSubjects] = useState<TeacherSubjectCount[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [roster, setRoster] = useState<SubjectRoster | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingRoster, setLoadingRoster] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [username, setUsername] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)

  // Load the teacher's subjects (with counts).
  const loadSubjects = async (keepSelection = true) => {
    const rows = await enrollmentApi.mySubjects()
    setSubjects(rows)
    if (!keepSelection || !selectedId) {
      setSelectedId((prev) => prev || (rows[0]?.subject_id ?? ''))
    }
    return rows
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const rows = await enrollmentApi.mySubjects()
        if (cancelled) return
        setSubjects(rows)
        setSelectedId(rows[0]?.subject_id ?? '')
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load your subjects.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Load the roster whenever the selected subject changes.
  useEffect(() => {
    if (!selectedId) {
      setRoster(null)
      return
    }
    let cancelled = false
    setLoadingRoster(true)
    setAddError(null)
    setNotice(null)
    void (async () => {
      try {
        const r = await enrollmentApi.roster(selectedId)
        if (!cancelled) setRoster(r)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load the class roster.',
          )
        }
      } finally {
        if (!cancelled) setLoadingRoster(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const subjectOptions = useMemo(
    () =>
      subjects.map((s) => ({
        value: s.subject_id,
        label: `${s.code} — ${s.name} (${s.student_count})`,
      })),
    [subjects],
  )

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    const handle = username.trim().toLowerCase()
    if (!handle || !selectedId || adding) return
    setAdding(true)
    setAddError(null)
    setNotice(null)
    try {
      const added: EnrolledStudent = await enrollmentApi.enroll(selectedId, handle)
      setUsername('')
      setNotice(`Added @${added.username} — ${added.full_name}`)
      // Refresh roster + the per-subject counts.
      const [r] = await Promise.all([enrollmentApi.roster(selectedId), loadSubjects()])
      setRoster(r)
    } catch (err) {
      setAddError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not add that student.',
      )
    } finally {
      setAdding(false)
    }
  }

  const handleRemove = async (student: EnrolledStudent) => {
    if (!selectedId || removingId) return
    setRemovingId(student.student_id)
    setNotice(null)
    try {
      await enrollmentApi.unenroll(selectedId, student.student_id)
      const [r] = await Promise.all([enrollmentApi.roster(selectedId), loadSubjects()])
      setRoster(r)
    } catch {
      setAddError('Could not remove that student.')
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold text-[var(--text-primary)] m-0">My Students</h1>
        <p className="text-sm text-[var(--text-secondary)] max-w-2xl">
          Add students to a subject by their username. Only enrolled students see that
          subject's quizzes and announcements — everyone else can't.
        </p>
      </header>

      {error && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)]">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading your subjects…
        </div>
      ) : subjects.length === 0 ? (
        <Card>
          <div className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
            <Info className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              You don't have any subjects yet. Create one under{' '}
              <span className="font-medium text-[var(--text-primary)]">My Subjects</span>, then come
              back here to enroll students.
            </span>
          </div>
        </Card>
      ) : (
        <>
          <Select
            label="Subject"
            options={subjectOptions}
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
          />

          {/* Add a student */}
          <Card>
            <form onSubmit={handleAdd} className="space-y-2">
              <label className="label">Add a student by username</label>
              <div className="flex items-start gap-2">
                <div className="flex-1">
                  <Input
                    placeholder="e.g. arjun.rao"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={adding}
                  />
                </div>
                <Button
                  type="submit"
                  icon={UserPlus}
                  loading={adding}
                  disabled={!username.trim() || adding}
                >
                  Add
                </Button>
              </div>
              {addError && (
                <p className="text-xs text-danger flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" /> {addError}
                </p>
              )}
              {notice && <p className="text-xs text-success">{notice}</p>}
            </form>
          </Card>

          {/* Roster */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <Users className="h-4 w-4 text-[var(--text-tertiary)]" />
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Enrolled students
              </h2>
              <span className="text-xs text-[var(--text-tertiary)]">
                {roster ? roster.students.length : 0}
              </span>
            </div>

            {loadingRoster ? (
              <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)] py-4">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading roster…
              </div>
            ) : !roster || roster.students.length === 0 ? (
              <p className="text-sm text-[var(--text-tertiary)] py-3">
                No students enrolled yet. Add one above.
              </p>
            ) : (
              <motion.div
                className="space-y-2"
                initial="initial"
                animate="animate"
                variants={{ animate: { transition: { staggerChildren: 0.03 } } }}
              >
                {roster.students.map((s) => (
                  <motion.div
                    key={s.student_id}
                    variants={fadeUp}
                    className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-secondary)] p-2.5"
                  >
                    <Avatar name={s.full_name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-[var(--text-primary)] truncate">
                        {s.full_name}
                        <span className="text-[var(--text-tertiary)] font-normal ml-2">
                          @{s.username}
                        </span>
                      </div>
                      <div className="text-[11px] text-[var(--text-tertiary)]">
                        {[s.branch, s.semester ? `Sem ${s.semester}` : null]
                          .filter(Boolean)
                          .join(' · ') || s.email}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemove(s)}
                      disabled={removingId === s.student_id}
                      title="Remove from this subject"
                      className={clsx(
                        'p-1.5 rounded-md text-[var(--text-tertiary)] hover:text-danger hover:bg-danger/10 transition-colors',
                        removingId === s.student_id && 'opacity-50 cursor-not-allowed',
                      )}
                    >
                      {removingId === s.student_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
