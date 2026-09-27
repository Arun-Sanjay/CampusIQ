import { useEffect, useState } from 'react'
import { motion, type Variants } from 'framer-motion'
import { clsx } from 'clsx'
import { AlertCircle, Loader2, Trophy, Users, Zap } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import type { BadgeVariant } from '../../components/ui/Badge'
import Avatar from '../../components/ui/Avatar'
import { ResponsiveTable, type ResponsiveColumn } from '../../components/ui'
import { ApiError, gamificationApi } from '../../api/client'
import type { LeaderboardResponse, LeaderboardRowResponse, Tier } from '../../types'

const stagger: Variants = { animate: { transition: { staggerChildren: 0.05 } } }
const fadeUp: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const TIER_META: Record<Tier, { label: string; variant: BadgeVariant }> = {
  diamond: { label: 'Diamond', variant: 'info' },
  platinum: { label: 'Platinum', variant: 'success' },
  gold: { label: 'Gold', variant: 'warning' },
  silver: { label: 'Silver', variant: 'default' },
  bronze: { label: 'Bronze', variant: 'default' },
}

export default function LeaderboardPage() {
  const [data, setData] = useState<LeaderboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const result = await gamificationApi.leaderboard(50)
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load leaderboard',
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

  if (loading) {
    return (
      <Card className="flex items-center gap-2 justify-center py-10 text-[var(--text-tertiary)]">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading leaderboard…
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="flex items-start gap-2 text-danger py-4">
        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
        <span className="text-sm">{error}</span>
      </Card>
    )
  }

  if (!data || data.rows.length === 0) {
    return (
      <Card>
        <p className="text-sm text-[var(--text-tertiary)] text-center py-6">
          No leaderboard data yet. Take quizzes, finish mock interviews, and update your profile
          to appear here.
        </p>
      </Card>
    )
  }

  const top3 = data.rows.slice(0, 3)
  const rest = data.rows.slice(3)
  const myRow = data.my_row

  const rankColumns: ResponsiveColumn<LeaderboardRowResponse>[] = [
    {
      key: 'rank',
      header: 'Rank',
      headerClassName: 'w-12',
      className: 'font-semibold text-[var(--text-primary)]',
      render: (row) => `#${row.rank}`,
    },
    {
      key: 'name',
      header: 'Name',
      primary: true,
      render: (row) => (
        <div className="flex items-center gap-2">
          <Avatar name={row.name} size="sm" />
          <span className="text-[var(--text-primary)] font-medium">
            {row.name}
            {row.is_current_user && <span className="ml-2 text-xs text-primary">(you)</span>}
          </span>
        </div>
      ),
    },
    {
      key: 'score',
      header: 'Score',
      headerClassName: 'text-right',
      className: 'text-right tabular-nums font-semibold text-[var(--text-primary)]',
      render: (row) => row.total_score.toFixed(1),
    },
    {
      key: 'level',
      header: 'Level',
      headerClassName: 'text-right',
      className: 'text-right tabular-nums text-[var(--text-secondary)]',
      render: (row) => (
        <span className="inline-flex items-center gap-1">
          <Zap className="h-3 w-3" />
          {row.current_level}
        </span>
      ),
    },
    {
      key: 'xp',
      header: 'XP',
      headerClassName: 'text-right',
      className: 'text-right tabular-nums text-[var(--text-secondary)]',
      render: (row) => row.xp_total.toLocaleString(),
    },
    {
      key: 'tier',
      header: 'Tier',
      headerClassName: 'text-center',
      className: 'text-center',
      render: (row) => (
        <Badge variant={TIER_META[row.tier].variant} size="sm">
          {TIER_META[row.tier].label}
        </Badge>
      ),
    },
  ]

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      <motion.div variants={fadeUp} className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Leaderboard</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            {data.total_students} student{data.total_students === 1 ? '' : 's'} competing — ranked
            by CampusIQ score
          </p>
        </div>
        {myRow && (
          <div className="text-right">
            <p className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">Your Rank</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="stat-value text-2xl">#{myRow.rank}</span>
              <Badge variant={TIER_META[myRow.tier].variant} size="lg">
                {TIER_META[myRow.tier].label}
              </Badge>
            </div>
          </div>
        )}
      </motion.div>

      {/* Top-3 podium */}
      {top3.length > 0 && (
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader>
              <CardTitle>Top {top3.length}</CardTitle>
            </CardHeader>
            <div className="flex items-end justify-center gap-3 sm:gap-6 pt-6">
              {top3.length >= 2 && <PodiumBlock row={top3[1]!} height="md" place={2} />}
              {top3[0] && <PodiumBlock row={top3[0]} height="lg" place={1} />}
              {top3.length >= 3 && <PodiumBlock row={top3[2]!} height="sm" place={3} />}
            </div>
          </Card>
        </motion.div>
      )}

      {/* Ranked table */}
      {rest.length > 0 && (
        <motion.div variants={fadeUp}>
          <Card padding={false}>
            <CardHeader className="px-4 pt-4">
              <CardTitle>Ranked Players</CardTitle>
            </CardHeader>
            <ResponsiveTable
              columns={rankColumns}
              rows={rest}
              rowKey={(row) => row.student_id}
            />
          </Card>
        </motion.div>
      )}

      {/* Tier legend */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Tier Bands</CardTitle>
          </CardHeader>
          <div className="flex flex-wrap gap-3 text-xs text-[var(--text-secondary)]">
            <span className="flex items-center gap-1.5">
              <Badge variant="info" size="sm">
                Diamond
              </Badge>
              90–100
            </span>
            <span className="flex items-center gap-1.5">
              <Badge variant="success" size="sm">
                Platinum
              </Badge>
              80–89
            </span>
            <span className="flex items-center gap-1.5">
              <Badge variant="warning" size="sm">
                Gold
              </Badge>
              60–79
            </span>
            <span className="flex items-center gap-1.5">
              <Badge size="sm">Silver</Badge>
              40–59
            </span>
            <span className="flex items-center gap-1.5">
              <Badge size="sm">Bronze</Badge>
              &lt;40
            </span>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}

function PodiumBlock({
  row,
  height,
  place,
}: {
  row: LeaderboardRowResponse
  height: 'sm' | 'md' | 'lg'
  place: number
}) {
  const podiumHeights = { sm: 60, md: 90, lg: 120 }
  return (
    <div className="flex flex-col items-center gap-2">
      <Avatar name={row.name} size="lg" />
      <p
        className={clsx(
          'font-semibold text-sm text-[var(--text-primary)] text-center max-w-[8rem] truncate',
          row.is_current_user && 'text-primary',
        )}
      >
        {row.name}
        {row.is_current_user && ' (you)'}
      </p>
      <span className="stat-value text-xl">{row.total_score.toFixed(0)}</span>
      <Badge variant={TIER_META[row.tier].variant} size="sm">
        {TIER_META[row.tier].label}
      </Badge>
      <div
        style={{ height: podiumHeights[height] }}
        className={clsx(
          'w-20 rounded-t-lg flex items-center justify-center font-bold text-lg',
          place === 1
            ? 'bg-warning/20 text-warning border-2 border-warning/40'
            : place === 2
              ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-2 border-[var(--border-strong)]'
              : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-2 border-[var(--border-default)]',
        )}
      >
        #{place}
      </div>
    </div>
  )
}
