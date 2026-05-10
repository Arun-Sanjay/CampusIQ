import { useEffect, useMemo, useState } from 'react'
import { motion, type Variants } from 'framer-motion'
import {
  AlertCircle,
  CalendarRange,
  ChevronDown,
  Clock,
  Loader2,
  Lock,
  Minus,
  Plus,
  Sparkles,
  Target,
  Trash2,
  Zap,
} from 'lucide-react'
import { clsx } from 'clsx'
import { ApiError, algorithmsApi } from '../../api/client'
import type {
  GenerateScheduleResponse,
  ScheduleSlotResponse,
  StudyTaskInput,
} from '../../types'

const stagger: Variants = { animate: { transition: { staggerChildren: 0.05 } } }
const fadeUp: Variants = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

// ── Domain ──────────────────────────────────────────────────────

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const DAY_OPTIONS = [2, 3, 5, 7]

const SUBJECT_OPTIONS = ['DAA', 'CN', 'DMS', 'OS']

// Each subject gets a soft accent that works in every theme — flat hex so we
// don't depend on Tailwind tokens (`bg-info/15`, `text-purple`) that aren't
// guaranteed to exist in the current config.
type Tone = { tint: string; ring: string; text: string }
const SUBJECT_TONES: Record<string, Tone> = {
  DAA: { tint: 'rgba(99, 102, 241, 0.14)', ring: '#6366F1', text: '#A5B4FC' },
  CN: { tint: 'rgba(168, 85, 247, 0.14)', ring: '#A855F7', text: '#C4B5FD' },
  DMS: { tint: 'rgba(16, 185, 129, 0.14)', ring: '#10B981', text: '#6EE7B7' },
  OS: { tint: 'rgba(245, 158, 11, 0.14)', ring: '#F59E0B', text: '#FCD34D' },
}
const DEFAULT_TONE: Tone = {
  tint: 'rgba(56, 189, 248, 0.14)',
  ring: '#38BDF8',
  text: '#7DD3FC',
}
const LOCKED_TONE: Tone = {
  tint: 'rgba(255, 255, 255, 0.04)',
  ring: 'rgba(255, 255, 255, 0.2)',
  text: 'var(--text-tertiary)',
}

const toneFor = (subject?: string | null, locked?: boolean): Tone => {
  if (locked) return LOCKED_TONE
  if (!subject) return DEFAULT_TONE
  return SUBJECT_TONES[subject] ?? DEFAULT_TONE
}

const DEFAULT_TASKS: StudyTaskInput[] = [
  { topic: 'Arrays & Hashing', hours: 3, priority: 10, subject_code: 'DAA' },
  { topic: 'Trees + DFS/BFS', hours: 2, priority: 9, subject_code: 'DAA' },
  { topic: 'Dynamic Programming', hours: 4, priority: 8, subject_code: 'DAA' },
  { topic: 'TCP / UDP', hours: 2, priority: 7, subject_code: 'CN' },
  { topic: 'Mock Interview Prep', hours: 3, priority: 9, subject_code: null },
]

// ── Block grouping ──────────────────────────────────────────────

interface Block {
  dayIndex: number
  startHour: number
  endHour: number // exclusive
  topic: string
  subjectCode: string | null
  isLocked: boolean
}

function groupSlotsIntoBlocks(slots: ScheduleSlotResponse[]): Block[] {
  // Bucket by day.
  const byDay = new Map<number, ScheduleSlotResponse[]>()
  for (const s of slots) {
    if (!s.topic) continue
    if (!byDay.has(s.day_index)) byDay.set(s.day_index, [])
    byDay.get(s.day_index)!.push(s)
  }
  const blocks: Block[] = []
  for (const [day, daySlots] of byDay) {
    daySlots.sort((a, b) => a.hour_index - b.hour_index)
    let current: Block | null = null
    for (const s of daySlots) {
      if (
        current &&
        s.hour_index === current.endHour &&
        s.topic === current.topic &&
        (s.subject_code ?? null) === current.subjectCode &&
        s.is_locked === current.isLocked
      ) {
        // Extend the current block by one hour.
        current.endHour += 1
      } else {
        if (current) blocks.push(current)
        current = {
          dayIndex: day,
          startHour: s.hour_index,
          endHour: s.hour_index + 1,
          topic: s.topic!,
          subjectCode: s.subject_code ?? null,
          isLocked: s.is_locked,
        }
      }
    }
    if (current) blocks.push(current)
  }
  return blocks
}

const formatHour = (h: number): string => {
  const hour = ((h % 24) + 24) % 24
  if (hour === 0) return '12 AM'
  if (hour === 12) return '12 PM'
  return hour < 12 ? `${hour} AM` : `${hour - 12} PM`
}

// ── Page ────────────────────────────────────────────────────────

export default function SchedulePage() {
  const [tasks, setTasks] = useState<StudyTaskInput[]>(DEFAULT_TASKS)
  const [days, setDays] = useState(3)
  const [result, setResult] = useState<GenerateScheduleResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-generate on first mount with the default deck so the page is never empty.
  useEffect(() => {
    void generate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const generate = async () => {
    const trimmed = tasks
      .map((t) => ({ ...t, topic: t.topic.trim() }))
      .filter((t) => t.topic.length > 0 && t.hours > 0)
    if (trimmed.length === 0) {
      setError('Add at least one task with a topic and hours.')
      return
    }
    setRunning(true)
    setError(null)
    try {
      const data = await algorithmsApi.generateSchedule({ tasks: trimmed, days })
      setResult(data)
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Schedule generation failed.',
      )
    } finally {
      setRunning(false)
    }
  }

  const addTask = () => {
    setTasks((prev) => [
      ...prev,
      { topic: '', hours: 1, priority: 5, subject_code: null },
    ])
  }
  const removeTask = (idx: number) =>
    setTasks((prev) => prev.filter((_, i) => i !== idx))
  const updateTask = (idx: number, patch: Partial<StudyTaskInput>) =>
    setTasks((prev) => prev.map((t, i) => (i === idx ? { ...t, ...patch } : t)))

  // ── Weekly view computation ───────────────────────────────────
  const blocks = useMemo(
    () => (result ? groupSlotsIntoBlocks(result.slots) : []),
    [result],
  )

  // Auto-compute the hour window from the slots — gives a tight, content-shaped
  // grid instead of always showing 8 AM → 9 PM.
  const { hourStart, hourEnd } = useMemo(() => {
    if (!result || result.slots.length === 0) {
      return { hourStart: 8, hourEnd: 22 }
    }
    let minH = Infinity
    let maxH = -Infinity
    for (const s of result.slots) {
      if (!s.topic) continue
      if (s.hour_index < minH) minH = s.hour_index
      if (s.hour_index + 1 > maxH) maxH = s.hour_index + 1
    }
    // Pad by one hour on each side so blocks aren't flush against the edge.
    return {
      hourStart: Math.max(0, Math.min(minH - 1, 8)),
      hourEnd: Math.min(24, Math.max(maxH + 1, 18)),
    }
  }, [result])

  const hourCount = hourEnd - hourStart

  return (
    <motion.div
      className="space-y-4"
      variants={stagger}
      initial="initial"
      animate="animate"
    >
      {/* ── Header ───────────────────────────────────────────── */}
      <motion.div
        variants={fadeUp}
        className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3"
      >
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Study Schedule
          </h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1 max-w-xl">
            Branch-and-bound scheduler with priority-weighted task fitting (DAA Unit V).
            Pick your topics, hit Generate, and the engine packs them into your week.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <DayCountPicker value={days} onChange={setDays} />
          <button
            type="button"
            onClick={() => void generate()}
            disabled={running}
            className={clsx(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              'bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-60',
            )}
          >
            {running ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate
              </>
            )}
          </button>
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

      {/* ── KPI row ──────────────────────────────────────────── */}
      {result && (
        <motion.div
          variants={fadeUp}
          className="grid grid-cols-2 lg:grid-cols-4 gap-3"
        >
          <KpiCard
            icon={CalendarRange}
            label="Scheduled"
            value={`${result.scheduled_tasks.length} / ${
              result.scheduled_tasks.length + result.skipped_tasks.length
            }`}
            sub="tasks placed"
          />
          <KpiCard
            icon={Clock}
            label="Hours used"
            value={`${result.total_hours_scheduled}h`}
            sub={`across ${days} day${days === 1 ? '' : 's'}`}
          />
          <KpiCard
            icon={Target}
            label="Value packed"
            value={result.total_value.toFixed(0)}
            sub="priority × fit"
          />
          <KpiCard
            icon={Zap}
            label="Nodes explored"
            value={result.explored_nodes.toLocaleString()}
            sub="branch-and-bound search"
          />
        </motion.div>
      )}

      {/* ── Task editor ──────────────────────────────────────── */}
      <motion.div variants={fadeUp}>
        <SectionCard
          title="Topics to fit"
          subtitle="Each one becomes a candidate block. Priority breaks ties when budget is tight."
        >
          <div className="space-y-2">
            {tasks.map((task, idx) => (
              <TaskRow
                key={idx}
                task={task}
                onChange={(patch) => updateTask(idx, patch)}
                onRemove={() => removeTask(idx)}
                disabled={running}
              />
            ))}
            <button
              type="button"
              onClick={addTask}
              disabled={running}
              className="inline-flex items-center gap-1.5 text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors px-2 py-1.5 disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              Add topic
            </button>
          </div>
        </SectionCard>
      </motion.div>

      {/* ── Weekly grid ──────────────────────────────────────── */}
      {result && (
        <motion.div variants={fadeUp}>
          <SectionCard
            title="Weekly plan"
            subtitle="Grouped blocks · subject-coded by accent · locked meals greyed."
            padding="tight"
          >
            <WeeklyGrid
              days={days}
              hourStart={hourStart}
              hourCount={hourCount}
              blocks={blocks}
            />
            <Legend />
          </SectionCard>
        </motion.div>
      )}

      {/* ── Skipped tasks ────────────────────────────────────── */}
      {result && result.skipped_tasks.length > 0 && (
        <motion.div variants={fadeUp}>
          <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-warning/20 bg-warning/5">
            <span className="text-xs font-semibold text-warning uppercase tracking-wider mr-1">
              Couldn't fit:
            </span>
            {result.skipped_tasks.map((t) => (
              <span
                key={t.topic}
                className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-default)]"
              >
                {t.topic}
                <span className="text-[var(--text-tertiary)]">· {t.hours}h</span>
              </span>
            ))}
            <span className="ml-auto text-[11px] text-[var(--text-tertiary)]">
              Try fewer hours per topic or more days, then re-generate.
            </span>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

// ── Sub-components ──────────────────────────────────────────────

function SectionCard({
  title,
  subtitle,
  children,
  padding = 'normal',
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  padding?: 'normal' | 'tight'
}) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)]',
        padding === 'normal' ? 'p-4 sm:p-5' : 'p-3 sm:p-4',
      )}
    >
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
          {title}
        </h2>
        {subtitle && (
          <p className="text-xs text-[var(--text-tertiary)] mt-0.5 leading-snug">
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </div>
  )
}

function KpiCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof CalendarRange
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-3.5 flex items-center gap-3">
      <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)] font-medium">
          {label}
        </div>
        <div className="text-lg font-semibold text-[var(--text-primary)] leading-tight">
          {value}
        </div>
        {sub && (
          <div className="text-[10px] text-[var(--text-tertiary)] truncate">
            {sub}
          </div>
        )}
      </div>
    </div>
  )
}

function DayCountPicker({
  value,
  onChange,
}: {
  value: number
  onChange: (n: number) => void
}) {
  return (
    <div
      role="group"
      aria-label="Day count"
      className="inline-flex items-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] p-1"
    >
      {DAY_OPTIONS.map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={clsx(
            'text-xs px-2.5 py-1 rounded-md transition-colors',
            value === n
              ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm'
              : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]',
          )}
        >
          {n} days
        </button>
      ))}
    </div>
  )
}

function TaskRow({
  task,
  onChange,
  onRemove,
  disabled,
}: {
  task: StudyTaskInput
  onChange: (patch: Partial<StudyTaskInput>) => void
  onRemove: () => void
  disabled?: boolean
}) {
  const tone = toneFor(task.subject_code, false)
  return (
    <div
      className="grid items-center gap-2 p-2 pl-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)]/40 transition-colors"
      style={{
        gridTemplateColumns: 'auto minmax(0, 1fr) 132px 84px 96px 32px',
      }}
    >
      <span
        className="h-2.5 w-2.5 rounded-full shrink-0"
        style={{ background: tone.ring }}
        aria-hidden
      />
      <input
        type="text"
        placeholder="Topic name"
        value={task.topic}
        onChange={(e) => onChange({ topic: e.target.value })}
        disabled={disabled}
        className="bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none px-1.5 py-1 min-w-0"
      />
      <SubjectSelect
        value={task.subject_code ?? ''}
        onChange={(v) => onChange({ subject_code: v || null })}
        disabled={disabled}
      />
      <Stepper
        label="hr"
        value={task.hours}
        onChange={(v) => onChange({ hours: Math.max(1, Math.min(12, v)) })}
        min={1}
        max={12}
        disabled={disabled}
      />
      <Stepper
        label="pri"
        value={task.priority ?? 5}
        onChange={(v) => onChange({ priority: Math.max(1, Math.min(10, v)) })}
        min={1}
        max={10}
        disabled={disabled}
      />
      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        className="h-7 w-7 rounded-md text-[var(--text-tertiary)] hover:text-danger hover:bg-danger/10 transition-colors flex items-center justify-center disabled:opacity-50"
        aria-label="Remove topic"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function SubjectSelect({
  value,
  onChange,
  disabled,
}: {
  value: string
  onChange: (v: string) => void
  disabled?: boolean
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full text-xs bg-[var(--bg-tertiary)] border border-[var(--border-default)] text-[var(--text-secondary)] rounded-md pl-2.5 pr-7 py-1.5 appearance-none focus:outline-none focus:border-primary/60 disabled:opacity-50 cursor-pointer"
      >
        <option value="">No subject</option>
        {SUBJECT_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <ChevronDown className="h-3 w-3 absolute right-1.5 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] pointer-events-none" />
    </div>
  )
}

function Stepper({
  label,
  value,
  onChange,
  min,
  max,
  disabled,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min: number
  max: number
  disabled?: boolean
}) {
  return (
    <div className="inline-flex items-center rounded-md border border-[var(--border-default)] bg-[var(--bg-tertiary)] overflow-hidden">
      <button
        type="button"
        onClick={() => onChange(value - 1)}
        disabled={disabled || value <= min}
        className="h-7 w-6 inline-flex items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] disabled:opacity-40 transition-colors"
        aria-label={`Decrease ${label}`}
      >
        <Minus className="h-3 w-3" />
      </button>
      <span className="text-xs font-medium tabular-nums text-[var(--text-secondary)] w-7 text-center select-none">
        {value}
        <span className="text-[8px] uppercase tracking-wider text-[var(--text-tertiary)] ml-0.5">
          {label}
        </span>
      </span>
      <button
        type="button"
        onClick={() => onChange(value + 1)}
        disabled={disabled || value >= max}
        className="h-7 w-6 inline-flex items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] disabled:opacity-40 transition-colors"
        aria-label={`Increase ${label}`}
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  )
}

function WeeklyGrid({
  days,
  hourStart,
  hourCount,
  blocks,
}: {
  days: number
  hourStart: number
  hourCount: number
  blocks: Block[]
}) {
  const ROW_HEIGHT = 36 // px per hour
  return (
    <div className="overflow-x-auto -mx-1 px-1">
      <div
        className="relative grid gap-px bg-[var(--border-subtle)] rounded-lg overflow-hidden border border-[var(--border-default)]"
        style={{
          gridTemplateColumns: `64px repeat(${days}, minmax(120px, 1fr))`,
          gridTemplateRows: `28px repeat(${hourCount}, ${ROW_HEIGHT}px)`,
        }}
      >
        {/* Corner cell */}
        <div className="bg-[var(--bg-elevated)]" />
        {/* Day headers */}
        {Array.from({ length: days }).map((_, d) => (
          <div
            key={`day-${d}`}
            className="bg-[var(--bg-elevated)] flex items-center justify-center text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]"
          >
            {DAY_LABELS[d % 7]}
          </div>
        ))}

        {/* Hour rows: label column + per-day backdrop cells */}
        {Array.from({ length: hourCount }).map((_, i) => {
          const hour = hourStart + i
          return (
            <ContextRow key={`row-${i}`} hour={hour} days={days} />
          )
        })}

        {/* Blocks overlaid on the grid via grid-row/column positioning */}
        {blocks.map((b, i) => {
          const top = b.startHour - hourStart
          const span = b.endHour - b.startHour
          if (top < 0 || top + span > hourCount) return null
          const tone = toneFor(b.subjectCode, b.isLocked)
          return (
            <div
              key={`b-${i}`}
              className="relative m-0.5 rounded-md px-2 py-1 flex flex-col justify-between overflow-hidden"
              style={{
                gridColumn: `${b.dayIndex + 2}`,
                // +2 because row 1 is the header; +span for the end line
                gridRow: `${top + 2} / span ${span}`,
                background: tone.tint,
                borderLeft: `3px solid ${tone.ring}`,
              }}
            >
              <div className="flex items-center justify-between gap-2 min-w-0">
                <span
                  className={clsx(
                    'text-[11px] font-semibold leading-tight truncate',
                    b.isLocked && 'italic',
                  )}
                  style={{ color: b.isLocked ? 'var(--text-secondary)' : 'var(--text-primary)' }}
                  title={b.topic}
                >
                  {b.isLocked && (
                    <Lock className="inline h-2.5 w-2.5 mr-0.5 align-[-1px]" />
                  )}
                  {b.topic}
                </span>
                {b.subjectCode && !b.isLocked && (
                  <span
                    className="text-[9px] font-mono uppercase tracking-wider px-1 rounded shrink-0"
                    style={{ color: tone.text, background: tone.tint }}
                  >
                    {b.subjectCode}
                  </span>
                )}
              </div>
              <div
                className="text-[9px] uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                {formatHour(b.startHour)} – {formatHour(b.endHour)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ContextRow({ hour, days }: { hour: number; days: number }) {
  return (
    <>
      <div className="bg-[var(--bg-elevated)] text-[10px] text-[var(--text-tertiary)] flex items-start justify-end pr-2 pt-1 tabular-nums">
        {formatHour(hour)}
      </div>
      {Array.from({ length: days }).map((_, d) => (
        <div key={`bg-${hour}-${d}`} className="bg-[var(--bg-elevated)]" />
      ))}
    </>
  )
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-3 pt-3 mt-3 border-t border-[var(--border-default)] text-[11px] text-[var(--text-tertiary)]">
      <span className="font-semibold text-[var(--text-secondary)]">Legend</span>
      {Object.entries(SUBJECT_TONES).map(([code, tone]) => (
        <span key={code} className="inline-flex items-center gap-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: tone.ring }}
          />
          {code}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <span
          className="h-2 w-2 rounded-full"
          style={{ background: DEFAULT_TONE.ring }}
        />
        Other
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Lock className="h-2.5 w-2.5" />
        Meals (locked)
      </span>
    </div>
  )
}
