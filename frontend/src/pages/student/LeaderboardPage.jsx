import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  Trophy, ArrowUp, ArrowDown, Clock, Users,
} from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Avatar from '../../components/ui/Avatar'
import Button from '../../components/ui/Button'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

function getTier(score) {
  if (score > 80) return { label: 'Placement Ready', variant: 'success' }
  if (score > 60) return { label: 'Gold', variant: 'gold' }
  if (score > 40) return { label: 'Silver', variant: 'silver' }
  return { label: 'Bronze', variant: 'bronze' }
}

const topThree = [
  { rank: 2, name: 'Priya Sharma', score: 91, change: 1 },
  { rank: 1, name: 'Rahul Verma', score: 95, change: 0 },
  { rank: 3, name: 'Ananya Desai', score: 88, change: -1 },
]

const leaderboardData = [
  { rank: 4, name: 'Karthik Nair', score: 85, change: 2 },
  { rank: 5, name: 'Sneha Gupta', score: 83, change: -1 },
  { rank: 6, name: 'Vikram Reddy', score: 79, change: 3 },
  { rank: 7, name: 'Meera Patel', score: 76, change: 0 },
  { rank: 8, name: 'Arjun Singh', score: 72, change: -2 },
  { rank: 9, name: 'Divya Iyer', score: 68, change: 1 },
  { rank: 10, name: 'Rohan Das', score: 65, change: -3 },
  { rank: 11, name: 'Kavitha Rao', score: 62, change: 0 },
  { rank: 12, name: 'Nikhil Joshi', score: 58, change: 2 },
  { rank: 13, name: 'Lakshmi Menon', score: 55, change: -1 },
]

const currentUser = { rank: 45, name: 'Arun Sanjay', score: 67, change: 4 }

const weeklyChallenge = {
  title: 'Quiz Speed Challenge',
  description: 'Complete quizzes faster than anyone else this week. Top 5 win bonus XP and a limited badge.',
  timeRemaining: '3d 14h',
  topParticipants: [
    { rank: 1, name: 'Rahul Verma', score: 312 },
    { rank: 2, name: 'Priya Sharma', score: 298 },
    { rank: 3, name: 'Karthik Nair', score: 275 },
    { rank: 4, name: 'Sneha Gupta', score: 260 },
    { rank: 5, name: 'Ananya Desai', score: 248 },
  ],
}

const tabs = ['Overall', 'Weekly Challenge', 'By Subject']

export default function LeaderboardPage() {
  const [activeTab, setActiveTab] = useState('Overall')

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Leaderboard</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">See where you stand among your peers</p>
        </div>
      </motion.div>

      {/* Tabs */}
      <motion.div variants={fadeUp} className="flex gap-1 p-1 rounded-lg bg-[var(--bg-tertiary)] w-fit">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'px-4 py-2 text-sm font-medium rounded-md transition-all duration-200',
              activeTab === tab
                ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            )}
          >
            {tab}
          </button>
        ))}
      </motion.div>

      {activeTab === 'Overall' && (
        <>
          {/* Top 3 Podium */}
          <motion.div variants={fadeUp} className="grid grid-cols-3 gap-4 items-end">
            {topThree.map((player) => {
              const tier = getTier(player.score)
              const isFirst = player.rank === 1
              return (
                <motion.div
                  key={player.rank}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ delay: 0.15 + player.rank * 0.08, duration: 0.4 }}
                >
                  <Card className={clsx('text-center', isFirst && 'ring-1 ring-primary/20')}>
                    <div className={clsx('flex flex-col items-center', isFirst ? 'py-4' : 'py-2')}>
                      <span className={clsx(
                        'font-bold mb-2',
                        isFirst ? 'text-2xl text-[var(--text-primary)]' : 'text-lg text-[var(--text-secondary)]'
                      )}>
                        #{player.rank}
                      </span>
                      <Avatar name={player.name} size={isFirst ? 'xl' : 'lg'} />
                      <p className={clsx(
                        'font-semibold mt-2 text-[var(--text-primary)]',
                        isFirst ? 'text-base' : 'text-sm'
                      )}>
                        {player.name}
                      </p>
                      <p className="text-lg font-bold text-[var(--text-primary)] mt-1">{player.score}</p>
                      <Badge variant={tier.variant} size="sm" className="mt-1">{tier.label}</Badge>
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </motion.div>

          {/* Leaderboard Table */}
          <motion.div variants={fadeUp}>
            <Card padding={false}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-default)]">
                      <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Rank</th>
                      <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Name</th>
                      <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">CampusIQ Score</th>
                      <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Tier</th>
                      <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...leaderboardData, currentUser].map((row) => {
                      const tier = getTier(row.score)
                      const isCurrentUser = row.rank === 45
                      return (
                        <tr
                          key={row.rank}
                          className={clsx(
                            'border-b border-[var(--border-default)] last:border-b-0',
                            isCurrentUser && 'bg-primary/5'
                          )}
                        >
                          <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                            #{row.rank}
                            {isCurrentUser && <span className="text-xs text-[var(--text-tertiary)] ml-1">(You)</span>}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Avatar name={row.name} size="sm" />
                              <span className="text-[var(--text-primary)] font-medium">{row.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 font-semibold text-[var(--text-primary)]">{row.score}</td>
                          <td className="px-4 py-3">
                            <Badge variant={tier.variant} size="sm">{tier.label}</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <span className={clsx(
                              'inline-flex items-center gap-0.5 text-xs font-medium',
                              row.change > 0 ? 'text-success' : row.change < 0 ? 'text-danger' : 'text-[var(--text-tertiary)]'
                            )}>
                              {row.change > 0 && <ArrowUp className="h-3 w-3" />}
                              {row.change < 0 && <ArrowDown className="h-3 w-3" />}
                              {row.change !== 0 ? Math.abs(row.change) : '--'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        </>
      )}

      {activeTab === 'Weekly Challenge' && (
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader action={<Badge variant="warning" size="sm" dot><Clock className="h-3 w-3" />{weeklyChallenge.timeRemaining}</Badge>}>
              <CardTitle>This Week: {weeklyChallenge.title}</CardTitle>
            </CardHeader>
            <p className="text-sm text-[var(--text-secondary)] mb-4">{weeklyChallenge.description}</p>

            <div className="overflow-x-auto mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    <th className="text-left px-4 py-2 text-[var(--text-tertiary)] font-medium">Rank</th>
                    <th className="text-left px-4 py-2 text-[var(--text-tertiary)] font-medium">Participant</th>
                    <th className="text-left px-4 py-2 text-[var(--text-tertiary)] font-medium">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {weeklyChallenge.topParticipants.map((p) => (
                    <tr key={p.rank} className="border-b border-[var(--border-default)] last:border-b-0">
                      <td className="px-4 py-2 font-medium text-[var(--text-primary)]">#{p.rank}</td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          <Avatar name={p.name} size="sm" />
                          <span className="text-[var(--text-primary)]">{p.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2 font-semibold text-[var(--text-primary)]">{p.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Button icon={Trophy}>Join Challenge</Button>
          </Card>
        </motion.div>
      )}

      {activeTab === 'By Subject' && (
        <motion.div variants={fadeUp}>
          <Card>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Users className="h-10 w-10 text-[var(--text-tertiary)] mb-3" />
              <p className="text-[var(--text-secondary)] font-medium">Subject-wise leaderboards coming soon</p>
              <p className="text-sm text-[var(--text-tertiary)] mt-1">Compare rankings across DAA, CN, OS, and more.</p>
            </div>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}
