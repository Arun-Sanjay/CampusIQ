import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, type Variants } from 'framer-motion'
import {
  ArrowLeft,
  AlertCircle,
  Loader2,
  Check,
  Circle,
  Clock,
  ExternalLink,
  MessageCircle,
  Star,
  Lightbulb,
} from 'lucide-react'
import { clsx } from 'clsx'
import { ApiError, codingApi } from '../../api/client'
import DifficultyBadge from '../../components/coding/DifficultyBadge'
import type { PatternProblemRow, PatternWithProblems, UserProblemStatus } from '../../types'

const fadeUp: Variants = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.25 } },
}

export default function CodingPatternPage() {
  const { slug } = useParams<{ slug: string }>()
  const [pattern, setPattern] = useState<PatternWithProblems | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) return
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const p = await codingApi.getPattern(slug)
        if (!cancelled) setPattern(p)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load this pattern.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [slug])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)] p-8">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading pattern…
      </div>
    )
  }

  if (error || !pattern) {
    return (
      <div className="space-y-3">
        <Link
          to="/student/coding"
          className="inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-4 w-4" /> Back to patterns
        </Link>
        <div className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error ?? 'Pattern not found.'}</span>
        </div>
      </div>
    )
  }

  const pct = pattern.problem_count > 0 ? (pattern.solved_count / pattern.problem_count) * 100 : 0

  return (
    <div className="space-y-5 max-w-4xl">
      <Link
        to="/student/coding"
        className="inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      >
        <ArrowLeft className="h-4 w-4" /> Patterns
      </Link>

      {/* Pattern header */}
      <header className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-5 space-y-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-[var(--text-tertiary)]">
              <span>Tier {pattern.tier}</span>
              <span>·</span>
              <span className="capitalize">{pattern.track}</span>
              <span>·</span>
              <span>{pattern.difficulty_span}</span>
            </div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)] m-0 leading-tight">{pattern.name}</h1>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {pattern.solved_count}
              <span className="text-sm text-[var(--text-tertiary)]"> / {pattern.problem_count}</span>
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">solved</div>
          </div>
        </div>

        <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{pattern.core_idea}</p>
        {pattern.recognize_when && (
          <div className="flex items-start gap-2 text-[12.5px] text-[var(--text-secondary)] rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] px-3 py-2">
            <Lightbulb className="h-3.5 w-3.5 mt-0.5 shrink-0 text-warning" />
            <span>
              <span className="font-medium text-[var(--text-primary)]">Recognize it when: </span>
              {pattern.recognize_when}
            </span>
          </div>
        )}

        <div className="h-1.5 rounded-full bg-[var(--bg-tertiary)] overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all',
              pct === 100 ? 'bg-success' : 'bg-primary dark:bg-white',
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </header>

      {/* Problem list */}
      <motion.div
        className="space-y-2"
        initial="initial"
        animate="animate"
        variants={{ animate: { transition: { staggerChildren: 0.025 } } }}
      >
        {pattern.problems.map((p, i) => (
          <motion.div key={p.id} variants={fadeUp}>
            <ProblemRow row={p} index={i + 1} />
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}


function ProblemRow({ row, index }: { row: PatternProblemRow; index: number }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] hover:border-[var(--border-strong)] transition-colors p-3">
      <span className="w-6 shrink-0 text-center text-[11px] tabular-nums text-[var(--text-tertiary)]">{index}</span>
      <StatusIcon status={row.user_status} />
      {/* Title → problem detail (coach + Open on LeetCode live there) */}
      <Link to={`/student/coding/${row.slug}`} className="min-w-0 flex-1 group">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--text-primary)] truncate group-hover:underline">
            {row.title}
          </span>
          {row.is_premium && (
            <span title="LeetCode Premium problem" className="shrink-0">
              <Star className="h-3 w-3 text-warning" />
            </span>
          )}
        </div>
        {row.also_appears_in && (
          <div className="text-[10.5px] text-[var(--text-tertiary)] truncate mt-0.5">
            also appears in {row.also_appears_in}
          </div>
        )}
      </Link>

      {row.priority && row.priority !== 'medium' && (
        <span
          className={clsx(
            'hidden md:inline text-[10px] font-medium uppercase tracking-wider',
            row.priority === 'high' ? 'text-success' : 'text-[var(--text-tertiary)]',
          )}
          title={`${row.priority} interview priority`}
        >
          {row.priority}
        </span>
      )}
      <DifficultyBadge difficulty={row.difficulty} size="sm" />
      <Link
        to={`/student/coding/${row.slug}`}
        className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium text-[var(--text-secondary)] border border-[var(--border-default)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-colors"
        title="Open the DSA coach for this problem"
      >
        <MessageCircle className="h-3 w-3" />
        Coach
      </Link>
      <a
        href={row.leetcode_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium text-[var(--text-secondary)] border border-[var(--border-default)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-colors"
        title="Open on LeetCode"
      >
        <ExternalLink className="h-3 w-3" />
        LeetCode
      </a>
    </div>
  )
}

function StatusIcon({ status }: { status: UserProblemStatus }) {
  if (status === 'solved') return <Check className="h-4 w-4 text-success shrink-0" />
  if (status === 'attempted') return <Clock className="h-4 w-4 text-warning shrink-0" />
  return <Circle className="h-4 w-4 text-[var(--text-tertiary)] shrink-0" />
}
