import { motion, type Variants } from 'framer-motion'
import {
  Users, Activity, FileText, Brain,
  Clock, Server, HardDrive, CheckCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import ProgressBar from '../../components/ui/ProgressBar'
import StatCard from '../../components/dashboard/StatCard'

const stagger: Variants = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

interface ActivityItem {
  time: string
  text: string
}

const recentActivity: ActivityItem[] = [
  { time: '2 min ago', text: 'Prof. Sharma uploaded 3 documents to DAA' },
  { time: '15 min ago', text: 'New student registration: Rahul K.' },
  { time: '1h ago', text: 'Quiz "Graph Traversal" published by Prof. Rao' },
  { time: '2h ago', text: 'System backup completed successfully' },
  { time: '3h ago', text: 'Prof. Gupta created new subject: Machine Learning' },
]

interface AdminStat {
  label: string
  value: string
  icon: LucideIcon
  trend: number
}

interface UserBreakdownItem {
  role: string
  count: string
  color: string
}

export default function DashboardPage() {
  const stats: AdminStat[] = [
    { label: 'TOTAL USERS', value: '1,247', icon: Users, trend: 8 },
    { label: 'ACTIVE TODAY', value: '89', icon: Activity, trend: 12 },
    { label: 'DOCUMENTS', value: '342', icon: FileText, trend: 5 },
    { label: 'QUIZZES', value: '156', icon: Brain, trend: 3 },
  ]

  const userBreakdown: UserBreakdownItem[] = [
    { role: 'Students', count: '1,100', color: 'bg-primary' },
    { role: 'Teachers', count: '42', color: 'bg-success' },
    { role: 'Admins', count: '5', color: 'bg-warning' },
  ]

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Stats Row */}
      <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.1 + i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <StatCard {...stat} />
          </motion.div>
        ))}
      </motion.div>

      <div className="grid grid-cols-2 gap-6">
        {/* User Breakdown */}
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader>
              <CardTitle>User Breakdown</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {userBreakdown.map((item) => (
                <div key={item.role} className="flex items-center justify-between py-2 border-b border-[var(--border-default)] last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${item.color}`} />
                    <span className="text-sm text-[var(--text-secondary)]">{item.role}</span>
                  </div>
                  <span className="text-sm font-semibold text-[var(--text-primary)] tabular-nums">{item.count}</span>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Recent Activity */}
        <motion.div variants={fadeUp}>
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <div className="space-y-3">
              {recentActivity.map((item, i) => (
                <div key={i} className="flex items-start gap-3">
                  <Clock className="h-3.5 w-3.5 text-[var(--text-tertiary)] mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--text-primary)]">{item.text}</p>
                    <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Platform Health */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Platform Health</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            {/* API Response Time */}
            <div className="flex items-center justify-between py-2 border-b border-[var(--border-default)]">
              <div className="flex items-center gap-3">
                <Server className="h-4 w-4 text-[var(--text-tertiary)]" />
                <span className="text-sm text-[var(--text-primary)]">API Response Time</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[var(--text-primary)] tabular-nums">120ms</span>
                <Badge variant="success" size="sm">Healthy</Badge>
              </div>
            </div>

            {/* Storage Used */}
            <div className="flex items-center justify-between py-2 border-b border-[var(--border-default)]">
              <div className="flex items-center gap-3">
                <HardDrive className="h-4 w-4 text-[var(--text-tertiary)]" />
                <span className="text-sm text-[var(--text-primary)]">Storage Used</span>
              </div>
              <div className="flex items-center gap-3 w-48">
                <ProgressBar value={2.4} max={10} size="sm" color="primary" />
                <span className="text-xs text-[var(--text-tertiary)] whitespace-nowrap tabular-nums">2.4 / 10 GB</span>
              </div>
            </div>

            {/* Uptime */}
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-4 w-4 text-[var(--text-tertiary)]" />
                <span className="text-sm text-[var(--text-primary)]">Uptime</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[var(--text-primary)] tabular-nums">99.9%</span>
                <Badge variant="success" size="sm">Excellent</Badge>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
