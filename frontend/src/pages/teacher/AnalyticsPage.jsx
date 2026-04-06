import { motion } from 'framer-motion'
import {
  BarChart3, CheckCircle, AlertTriangle, Users,
  TrendingUp, TrendingDown,
} from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import ProgressBar from '../../components/ui/ProgressBar'
import Select from '../../components/ui/Select'
import StatCard from '../../components/dashboard/StatCard'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const subjectOptions = [
  { value: 'all', label: 'All Subjects' },
  { value: 'daa', label: 'Design & Analysis of Algorithms' },
  { value: 'os', label: 'Operating Systems' },
  { value: 'cn', label: 'Computer Networks' },
  { value: 'dbms', label: 'Database Management Systems' },
]

const weakTopics = [
  { topic: 'Graph Traversal (BFS/DFS)', score: 42 },
  { topic: 'Dynamic Programming — Tabulation', score: 48 },
  { topic: 'Deadlock Avoidance', score: 55 },
  { topic: 'TCP Congestion Control', score: 63 },
  { topic: 'B-Tree Insertions', score: 71 },
]

const students = [
  { name: 'Priya Sharma', quizzes: 18, avgScore: 89, trend: 'up', weakArea: 'Graph Theory' },
  { name: 'Rahul Verma', quizzes: 16, avgScore: 74, trend: 'up', weakArea: 'Dynamic Programming' },
  { name: 'Ananya Gupta', quizzes: 17, avgScore: 71, trend: 'down', weakArea: 'Deadlocks' },
  { name: 'Vikram Singh', quizzes: 15, avgScore: 65, trend: 'down', weakArea: 'TCP/IP' },
  { name: 'Meera Patel', quizzes: 18, avgScore: 82, trend: 'up', weakArea: 'Normalization' },
  { name: 'Arjun Reddy', quizzes: 14, avgScore: 58, trend: 'down', weakArea: 'Backtracking' },
]

function getBarColor(score) {
  if (score < 50) return 'danger'
  if (score < 70) return 'warning'
  return 'success'
}

export default function AnalyticsPage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Filter */}
      <motion.div variants={fadeUp} className="w-64">
        <Select options={subjectOptions} defaultValue="all" placeholder="Filter by subject" />
      </motion.div>

      {/* Stats Row */}
      <motion.div variants={fadeUp} className="grid grid-cols-4 gap-4">
        {[
          { label: 'CLASS AVERAGE', value: '72%', icon: BarChart3, trend: -2 },
          { label: 'COMPLETION RATE', value: '85%', icon: CheckCircle, trend: 4 },
          { label: 'MOST MISSED', value: 'Graph Traversal', icon: AlertTriangle },
          { label: 'ACTIVE STUDENTS', value: '142', icon: Users, trend: 3 },
        ].map((stat, i) => (
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

      {/* Score Distribution Placeholder */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Score Distribution</CardTitle>
          </CardHeader>
          <div className="h-48 flex items-center justify-center border border-dashed border-[var(--border-default)] rounded-lg">
            <p className="text-sm text-[var(--text-tertiary)]">Histogram chart will render here</p>
          </div>
        </Card>
      </motion.div>

      {/* Weakest Topics */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Weakest Topics</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            {weakTopics.map((item) => (
              <div key={item.topic} className="flex items-center gap-4">
                <span className="text-sm text-[var(--text-primary)] w-56 shrink-0">{item.topic}</span>
                <div className="flex-1">
                  <ProgressBar
                    value={item.score}
                    max={100}
                    color={getBarColor(item.score)}
                    size="md"
                  />
                </div>
                <span className="text-sm font-medium text-[var(--text-secondary)] w-10 text-right tabular-nums">
                  {item.score}%
                </span>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Student Performance Table */}
      <motion.div variants={fadeUp}>
        <Card padding={false}>
          <CardHeader className="px-4 pt-4">
            <CardTitle>Student Performance</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Name</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Quizzes Taken</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Avg Score</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Trend</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Weak Area</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr
                    key={s.name}
                    className="border-b border-[var(--border-default)] last:border-0 hover:bg-[var(--bg-secondary)] transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[var(--text-primary)]">{s.name}</td>
                    <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular-nums">{s.quizzes}</td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span className={s.avgScore >= 70 ? 'text-success font-medium' : s.avgScore >= 50 ? 'text-warning font-medium' : 'text-danger font-medium'}>
                        {s.avgScore}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {s.trend === 'up' ? (
                        <TrendingUp className="h-4 w-4 text-success inline-block" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-danger inline-block" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{s.weakArea}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
