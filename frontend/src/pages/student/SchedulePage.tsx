import { useEffect, useMemo, useState } from 'react'
import { motion, type Variants } from 'framer-motion'
import {
  AlertCircle,
  Calendar,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import StatCard from '../../components/dashboard/StatCard'
import { ApiError, algorithmsApi } from '../../api/client'
import type { GenerateScheduleResponse, StudyTaskInput } from '../../types'

const stagger: Variants = { animate: { transition: { staggerChildren: 0.05 } } }
const fadeUp: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const HOURS = Array.from({ length: 14 }, (_, i) => i + 8) // 8 AM - 9 PM

const DEFAULT_TASKS: StudyTaskInput[] = [
  { topic: 'Arrays & Hashing', hours: 3, priority: 10, subject_code: 'DAA' },
  { topic: 'Trees + DFS/BFS', hours: 2, priority: 9, subject_code: 'DAA' },
  { topic: 'Dynamic Programming', hours: 4, priority: 8, subject_code: 'DAA' },
  { topic: 'TCP/UDP', hours: 2, priority: 7, subject_code: 'CN' },
  { topic: 'Mock Interview Prep', hours: 3, priority: 9, subject_code: null },
]

const SUBJECT_COLORS: Record<string, string> = {
  DAA: 'bg-info/15 border-info/40 text-info',
  CN: 'bg-purple/15 border-purple/40 text-purple',
  DMS: 'bg-success/15 border-success/40 text-success',
  OS: 'bg-warning/15 border-warning/40 text-warning',
}

export default function SchedulePage() {
  const [tasks, setTasks] = useState<StudyTaskInput[]>(DEFAULT_TASKS)
  const [days, setDays] = useState(3)
  const [result, setResult] = useState<GenerateScheduleResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-generate on mount
  useEffect(() => {
    void generate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const generate = async () => {
    if (tasks.length === 0) {
      setError('Add at least one task')
      return
    }
    setRunning(true)
    setError(null)
    try {
      const data = await algorithmsApi.generateSchedule({ tasks, days })
      setResult(data)
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Schedule generation failed',
      )
    } finally {
      setRunning(false)
    }
  }

  const addTask = () => {
    setTasks((prev) => [...prev, { topic: '', hours: 1, priority: 5, subject_code: null }])
  }

  const removeTask = (idx: number) => {
    setTasks((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateTask = (idx: number, patch: Partial<StudyTaskInput>) => {
    setTasks((prev) =>
      prev.map((t, i) => (i === idx ? { ...t, ...patch } : t)),
    )
  }

  // Build a 2D grid: dayIndex × hourIndex → ScheduleSlot
  const grid = useMemo(() => {
    if (!result) return null
    const map: Record<number, Record<number, (typeof result.slots)[number]>> = {}
    for (const slot of result.slots) {
      if (!map[slot.day_index]) map[slot.day_index] = {}
      map[slot.day_index]![slot.hour_index] = slot
    }
    return map
  }, [result])

  return (
    <motion.div className="space-y-4" variants={stagger} initial="initial" animate="animate">
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Study Schedule</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Branch-and-bound scheduler with priority-weighted task fitting (DAA Unit V)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min={1}
            max={14}
            value={String(days)}
            onChange={(e) => setDays(Math.max(1, Math.min(14, Number(e.target.value) || 3)))}
            className="w-16"
          />
          <span className="text-xs text-[var(--text-tertiary)]">days</span>
          <Button
            icon={running ? undefined : Sparkles}
            onClick={() => void generate()}
            disabled={running}
          >
            {running ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Generating…
              </>
            ) : (
              'Generate'
            )}
          </Button>
        </div>
      </motion.div>

      {error && (
        <motion.div
          variants={fadeUp}
          className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Tasks to Schedule</CardTitle>
          </CardHeader>
          <div className="space-y-2">
            {tasks.map((task, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                <Input
                  className="col-span-5"
                  placeholder="Topic"
                  value={task.topic}
                  onChange={(e) => updateTask(idx, { topic: e.target.value })}
                />
                <Input
                  className="col-span-2"
                  type="number"
                  min={1}
                  max={12}
                  placeholder="Hours"
                  value={String(task.hours)}
                  onChange={(e) => updateTask(idx, { hours: Number(e.target.value) || 1 })}
                />
                <Input
                  className="col-span-2"
                  type="number"
                  min={0}
                  step="0.5"
                  placeholder="Priority"
                  value={String(task.priority ?? 5)}
                  onChange={(e) => updateTask(idx, { priority: Number(e.target.value) || 5 })}
                />
                <Input
                  className="col-span-2"
                  placeholder="Subject"
                  value={task.subject_code ?? ''}
                  onChange={(e) => updateTask(idx, { subject_code: e.target.value || null })}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  icon={Trash2}
                  onClick={() => removeTask(idx)}
                  className="col-span-1"
                />
              </div>
            ))}
            <Button variant="secondary" size="sm" icon={Plus} onClick={addTask}>
              Add task
            </Button>
          </div>
        </Card>
      </motion.div>

      {result && (
        <>
          <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4">
            <StatCard
              label="SCHEDULED"
              value={`${result.scheduled_tasks.length}/${result.scheduled_tasks.length + result.skipped_tasks.length}`}
              icon={Calendar}
            />
            <StatCard label="HOURS USED" value={`${result.total_hours_scheduled}h`} />
            <StatCard label="TOTAL VALUE" value={result.total_value.toFixed(0)} />
            <StatCard label="NODES EXPLORED" value={result.explored_nodes.toLocaleString()} />
          </motion.div>

          {result.skipped_tasks.length > 0 && (
            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle>Skipped Tasks (didn't fit)</CardTitle>
                </CardHeader>
                <div className="flex flex-wrap gap-2">
                  {result.skipped_tasks.map((t) => (
                    <Badge key={t.topic} variant="warning" size="sm">
                      {t.topic} ({t.hours}h)
                    </Badge>
                  ))}
                </div>
              </Card>
            </motion.div>
          )}

          <motion.div variants={fadeUp}>
            <Card padding={false}>
              <div className="px-4 pt-4">
                <CardTitle>Weekly Grid</CardTitle>
              </div>
              <div className="overflow-x-auto p-4">
                <table className="w-full text-xs">
                  <thead>
                    <tr>
                      <th className="text-left p-1 text-[var(--text-tertiary)]"></th>
                      {Array.from({ length: days }).map((_, d) => (
                        <th
                          key={d}
                          className="p-1 text-center text-[var(--text-tertiary)] font-medium"
                        >
                          {DAY_LABELS[d % 7]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {HOURS.map((h) => (
                      <tr key={h}>
                        <td className="text-right pr-2 py-1 text-[var(--text-tertiary)] tabular-nums">
                          {h}:00
                        </td>
                        {Array.from({ length: days }).map((_, d) => {
                          const slot = grid?.[d]?.[h]
                          if (!slot) {
                            return (
                              <td
                                key={d}
                                className="border border-[var(--border-default)] p-1 align-top"
                                style={{ minWidth: 100, height: 40 }}
                              />
                            )
                          }
                          if (slot.is_locked) {
                            return (
                              <td
                                key={d}
                                className="border border-[var(--border-default)] p-1 align-top text-[var(--text-tertiary)] italic text-center"
                                style={{ minWidth: 100, height: 40 }}
                              >
                                {slot.topic}
                              </td>
                            )
                          }
                          if (slot.topic) {
                            const cls = slot.subject_code
                              ? SUBJECT_COLORS[slot.subject_code] ??
                                'bg-primary/15 border-primary/40 text-primary'
                              : 'bg-primary/15 border-primary/40 text-primary'
                            return (
                              <td
                                key={d}
                                className={`border p-1 align-top ${cls}`}
                                style={{ minWidth: 100, height: 40 }}
                              >
                                <div className="text-[10px] font-semibold leading-tight">
                                  {slot.topic}
                                </div>
                                {slot.subject_code && (
                                  <div className="text-[9px] opacity-70">{slot.subject_code}</div>
                                )}
                              </td>
                            )
                          }
                          return (
                            <td
                              key={d}
                              className="border border-[var(--border-default)] p-1 align-top"
                              style={{ minWidth: 100, height: 40 }}
                            />
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        </>
      )}
    </motion.div>
  )
}
