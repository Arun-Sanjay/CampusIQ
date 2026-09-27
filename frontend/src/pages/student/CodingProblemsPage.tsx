import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, type Variants } from 'framer-motion'
import { AlertCircle, Loader2, ChevronRight } from 'lucide-react'
import { clsx } from 'clsx'
import { ApiError, codingApi } from '../../api/client'
import type { CodingStatsResponse, CodingTrack, PatternListItem } from '../../types'

const fadeUp: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

const TIER_LABELS: Record<number, string> = {
  1: 'Foundations',
  2: 'Data Structures',
  3: 'Graphs',
  4: 'Dynamic Programming',
  5: 'Polish',
  6: 'Advanced',
}

export default function CodingProblemsPage() {
  const [patterns, setPatterns] = useState<PatternListItem[]>([])
  const [stats, setStats] = useState<CodingStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [track, setTrack] = useState<CodingTrack>('core')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const [pats, st] = await Promise.all([codingApi.listPatterns(), codingApi.getStats()])
        if (cancelled) return
        setPatterns(pats)
        setStats(st)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load the coding curriculum.',
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

  const counts = useMemo(() => {
    const core = patterns.filter((p) => p.track === 'core').length
    const advanced = patterns.filter((p) => p.track === 'advanced').length
    return { core, advanced }
  }, [patterns])

  // Patterns of the active track, grouped by tier (API already sorts by order).
  const tiers = useMemo(() => {
    const inTrack = patterns.filter((p) => p.track === track)
    const byTier = new Map<number, PatternListItem[]>()
    for (const p of inTrack) {
      const list = byTier.get(p.tier) ?? []
      list.push(p)
      byTier.set(p.tier, list)
    }
    return [...byTier.entries()].sort((a, b) => a[0] - b[0])
  }, [patterns, track])

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold text-[var(--text-primary)] m-0">Coding</h1>
        <p className="text-sm text-[var(--text-secondary)] max-w-2xl">
          A pattern-first DSA track. Pick a pattern, work its problems easy→hard on
          LeetCode, and lean on the Socratic coach when you're stuck — it nudges you
          toward the insight instead of handing over the answer.
        </p>
      </header>

      {error && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {stats && <StatsBanner stats={stats} />}

      <TrackToggle track={track} onChange={setTrack} coreCount={counts.core} advancedCount={counts.advanced} />

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)]">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading patterns…
        </div>
      ) : (
        <div className="space-y-8">
          {tiers.map(([tier, pats]) => (
            <section key={tier} className="space-y-3">
              <div className="flex items-baseline gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                  Tier {tier} · {TIER_LABELS[tier] ?? ''}
                </h2>
                <span className="text-[11px] text-[var(--text-tertiary)]">{pats.length} patterns</span>
              </div>
              <motion.div
                className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3"
                initial="initial"
                animate="animate"
                variants={{ animate: { transition: { staggerChildren: 0.03 } } }}
              >
                {pats.map((p) => (
                  <motion.div key={p.slug} variants={fadeUp}>
                    <PatternBox pattern={p} />
                  </motion.div>
                ))}
              </motion.div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}


function PatternBox({ pattern }: { pattern: PatternListItem }) {
  const pct = pattern.problem_count > 0 ? (pattern.solved_count / pattern.problem_count) * 100 : 0
  const complete = pattern.problem_count > 0 && pattern.solved_count === pattern.problem_count
  return (
    <Link
      to={`/student/coding/pattern/${pattern.slug}`}
      className="group flex flex-col h-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-4 hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-card-hover)] transition-all"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] leading-snug group-hover:text-[var(--gradient-accent)] transition-colors">
          {pattern.name}
        </h3>
        <span className="shrink-0 text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded border border-[var(--border-default)] text-[var(--text-tertiary)]">
          {pattern.difficulty_span}
        </span>
      </div>
      <p className="text-[12.5px] text-[var(--text-secondary)] mt-1.5 leading-snug line-clamp-2 flex-1">
        {pattern.core_idea}
      </p>
      <div className="mt-3 space-y-1.5">
        <div className="h-1.5 rounded-full bg-[var(--bg-tertiary)] overflow-hidden">
          <div
            className={clsx('h-full rounded-full transition-all', complete ? 'bg-success' : 'bg-primary dark:bg-white')}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-[var(--text-tertiary)]">
            {pattern.solved_count} / {pattern.problem_count} solved
          </span>
          <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]">
            Open
            <ChevronRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
          </span>
        </div>
      </div>
    </Link>
  )
}


function TrackToggle({
  track,
  onChange,
  coreCount,
  advancedCount,
}: {
  track: CodingTrack
  onChange: (t: CodingTrack) => void
  coreCount: number
  advancedCount: number
}) {
  const opts: { key: CodingTrack; label: string; count: number }[] = [
    { key: 'core', label: 'Core', count: coreCount },
    { key: 'advanced', label: 'Advanced', count: advancedCount },
  ]
  return (
    <div className="inline-flex items-center gap-1 p-1 rounded-lg border border-[var(--border-default)] bg-[var(--bg-secondary)]">
      {opts.map(({ key, label, count }) => {
        const active = key === track
        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={clsx(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              active
                ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
            )}
          >
            {label}
            <span className="text-[10px] text-[var(--text-tertiary)]">{count}</span>
          </button>
        )
      })}
    </div>
  )
}


function StatsBanner({ stats }: { stats: CodingStatsResponse }) {
  const solvedTotal = stats.solved_easy + stats.solved_medium + stats.solved_hard
  const items = [
    { label: 'Solved', value: `${solvedTotal} / ${stats.total_problems}`, sub: `${stats.total_submissions} attempts` },
    { label: 'Easy', value: stats.solved_easy, sub: null, colour: 'text-success' },
    { label: 'Medium', value: stats.solved_medium, sub: null, colour: 'text-warning' },
    { label: 'Hard', value: stats.solved_hard, sub: null, colour: 'text-danger' },
    { label: 'Streak', value: stats.streak_days, sub: stats.streak_days === 1 ? 'day' : 'days' },
  ]
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {items.map((it) => (
        <div key={it.label} className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
            {it.label}
          </div>
          <div className={clsx('text-xl font-bold mt-1', it.colour ?? 'text-[var(--text-primary)]')}>{it.value}</div>
          {it.sub && <div className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{it.sub}</div>}
        </div>
      ))}
    </div>
  )
}
