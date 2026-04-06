import { motion } from 'framer-motion'
import { Zap, Brain, BarChart3, Trophy } from 'lucide-react'
import Card, { CardLabel } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import ProgressBar from '../../components/ui/ProgressBar'
import StatCard from '../../components/dashboard/StatCard'
import ScoreRing from '../../components/dashboard/ScoreRing'
import TaskFeed from '../../components/dashboard/TaskFeed'
import ActivityFeed from '../../components/dashboard/ActivityFeed'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const mockTasks = [
  { title: 'Complete DAA Quiz 3', priority: 'urgent', reason: 'Will increase your academic score by 4 points' },
  { title: 'Finish Mock Interview (Google)', priority: 'high', reason: 'Interview pillar needs 2 more sessions' },
  { title: 'Review OS Chapter 5 notes', priority: 'medium', reason: 'Weak area detected — scored 42% last quiz' },
  { title: 'Update resume with new project', priority: 'medium', reason: 'Placement pillar incomplete' },
  { title: 'Answer 2 community doubts', priority: 'low', reason: 'Earn 50 XP and help your peers' },
]

const mockActivity = [
  { text: 'Scored 85% on CN Quiz 4', time: '2h ago' },
  { text: 'Completed Mock Interview — Friendly Persona', time: '5h ago' },
  { text: 'Earned badge: Quiz Streak x7', time: '1d ago' },
  { text: 'Answered doubt: TCP 3-way handshake', time: '1d ago' },
  { text: 'Level up! Now Level 12', time: '2d ago' },
]

const mockPillars = [
  { label: 'Academic', value: 72, color: 'primary' },
  { label: 'Skills', value: 58, color: 'purple' },
  { label: 'Interview', value: 65, color: 'warning' },
  { label: 'Placement', value: 73, color: 'success' },
]

export default function DashboardPage() {
  return (
    <motion.div className="flex gap-6" variants={stagger} initial="initial" animate="animate">
      {/* Main Content */}
      <div className="flex-1 min-w-0 space-y-6">
        {/* Identity Badge */}
        <motion.div variants={fadeUp} className="flex items-center justify-between">
          <Badge variant="primary" size="lg">Semester 4 — B.Tech CS</Badge>
          <div className="flex items-center gap-4 text-sm text-[var(--text-tertiary)]">
            <span>5 day streak</span>
            <span>Day 45 as Student</span>
          </div>
        </motion.div>

        {/* Stat Cards */}
        <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4">
          {[
            { label: 'CAMPUSIQ SCORE', value: '67', icon: BarChart3, trend: 3 },
            { label: 'TOTAL XP', value: '3,450', icon: Zap },
            { label: 'QUIZZES DONE', value: '24', icon: Brain },
            { label: 'WEEKLY RANK', value: '#45', icon: Trophy, trend: -2 },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <StatCard {...stat} className="glow-border" />
            </motion.div>
          ))}
        </motion.div>

        {/* Score Detail */}
        <motion.div variants={fadeUp}>
          <Card padding={false} className="glow-border">
            <div className="p-5 flex items-center gap-8">
              <ScoreRing score={67} label="CampusIQ" />
              <div className="flex-1 space-y-3">
                {mockPillars.map((p) => (
                  <ProgressBar
                    key={p.label}
                    label={p.label}
                    value={p.value}
                    showValue
                    color={p.color}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Task Feed */}
        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3 block">WHAT SHOULD I DO NEXT?</CardLabel>
          <TaskFeed tasks={mockTasks} />
        </motion.div>

        {/* XP Bar */}
        <motion.div variants={fadeUp}>
          <Card className="glow-border">
            <div className="flex items-center gap-3">
              <Zap className="h-4 w-4 text-[var(--text-primary)]" />
              <span className="text-sm font-medium text-[var(--text-primary)]">Level 12</span>
              <div className="flex-1">
                <ProgressBar value={3450} max={4000} size="md" />
              </div>
              <span className="text-xs text-[var(--text-tertiary)]">3,450 / 4,000 XP</span>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Right Sidebar */}
      <motion.div
        className="w-72 shrink-0 space-y-6"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3, duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        <Card className="glow-border">
          <div className="flex items-center justify-between mb-3">
            <CardLabel>WEEKLY QUESTS</CardLabel>
            <span className="text-xs text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)]">See All</span>
          </div>
          <div className="space-y-3">
            {[
              { text: 'Complete 5 sessions', progress: '2/5' },
              { text: 'Score 80%+ accuracy', progress: '1/3' },
              { text: 'Help 3 peers', progress: '0/3' },
            ].map((q, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-secondary)]">{q.text}</span>
                <span className="text-[var(--text-tertiary)] text-xs">{q.progress}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="glow-border">
          <CardLabel className="mb-3 block">RECENT ACTIVITY</CardLabel>
          <ActivityFeed activities={mockActivity} />
        </Card>

        <Card className="glow-border">
          <CardLabel className="mb-3 block">ANNOUNCEMENTS</CardLabel>
          <div className="space-y-3">
            <div className="text-sm">
              <p className="text-[var(--text-primary)] font-medium">DAA Assignment 3 Due</p>
              <p className="text-[var(--text-tertiary)] text-xs mt-0.5">Prof. Sharma — 3h ago</p>
            </div>
            <div className="text-sm">
              <p className="text-[var(--text-primary)] font-medium">CN Lab Cancelled Tomorrow</p>
              <p className="text-[var(--text-tertiary)] text-xs mt-0.5">Prof. Rao — 1d ago</p>
            </div>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
