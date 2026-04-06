import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Search, Eye, BookOpen, Flame, Zap, MessageCircle } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Avatar from '../../components/ui/Avatar'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import ProgressBar from '../../components/ui/ProgressBar'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const subjectOptions = [
  { value: 'all', label: 'All Subjects' },
  { value: 'daa', label: 'DAA' },
  { value: 'cn', label: 'CN' },
  { value: 'os', label: 'OS' },
  { value: 'dms', label: 'DMS' },
]

const students = [
  { name: 'Rahul Verma', branch: 'CSE', semester: 4, avgScore: 92, quizzes: 18, lastActive: '2h ago' },
  { name: 'Priya Sharma', branch: 'CSE', semester: 4, avgScore: 88, quizzes: 16, lastActive: '5h ago' },
  { name: 'Karthik Nair', branch: 'ISE', semester: 4, avgScore: 76, quizzes: 14, lastActive: '1d ago' },
  { name: 'Sneha Gupta', branch: 'CSE', semester: 4, avgScore: 71, quizzes: 12, lastActive: '3h ago' },
  { name: 'Vikram Reddy', branch: 'ECE', semester: 6, avgScore: 65, quizzes: 10, lastActive: '2d ago' },
  { name: 'Meera Patel', branch: 'CSE', semester: 4, avgScore: 54, quizzes: 8, lastActive: '4h ago' },
  { name: 'Arjun Singh', branch: 'ISE', semester: 4, avgScore: 48, quizzes: 6, lastActive: '3d ago' },
  { name: 'Divya Iyer', branch: 'CSE', semester: 4, avgScore: 82, quizzes: 15, lastActive: '1h ago' },
]

function getScoreColor(score) {
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  return 'text-danger'
}

const selectedStudent = {
  name: 'Meera Patel',
  branch: 'CSE',
  semester: 4,
  quizScores: [
    { label: 'DAA Quiz 3', value: 62 },
    { label: 'CN Quiz 4', value: 48 },
    { label: 'OS Quiz 2', value: 55 },
    { label: 'DMS Quiz 1', value: 51 },
  ],
  weakAreas: ['Graph Algorithms', 'Transport Layer', 'Process Scheduling'],
  xp: 1820,
  streak: 3,
  communityContributions: 5,
}

export default function StudentDetailsPage() {
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Student Details</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">View individual student performance and engagement</p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div variants={fadeUp} className="flex gap-4">
        <div className="flex-1">
          <Input placeholder="Search students..." icon={Search} />
        </div>
        <div className="w-48">
          <Select options={subjectOptions} placeholder="Filter by subject" />
        </div>
      </motion.div>

      {/* Student Table */}
      <motion.div variants={fadeUp}>
        <Card padding={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Name</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Branch</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Semester</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Avg Score</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Quizzes Taken</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Last Active</th>
                  <th className="text-left px-4 py-3 text-[var(--text-tertiary)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s, i) => (
                  <motion.tr
                    key={s.name}
                    className={clsx(
                      'border-b border-[var(--border-default)] last:border-b-0',
                      s.name === selectedStudent.name && 'bg-primary/5'
                    )}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.15 + i * 0.04 }}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Avatar name={s.name} size="sm" />
                        <span className="text-[var(--text-primary)] font-medium">{s.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{s.branch}</td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{s.semester}</td>
                    <td className={clsx('px-4 py-3 font-semibold', getScoreColor(s.avgScore))}>
                      {s.avgScore}%
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{s.quizzes}</td>
                    <td className="px-4 py-3 text-[var(--text-tertiary)]">{s.lastActive}</td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm" icon={Eye}>View</Button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>

      {/* Selected Student Detail */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Avatar name={selectedStudent.name} size="lg" />
              <div>
                <CardTitle>{selectedStudent.name}</CardTitle>
                <p className="text-xs text-[var(--text-tertiary)]">{selectedStudent.branch} · Semester {selectedStudent.semester}</p>
              </div>
            </div>
          </CardHeader>

          <div className="grid grid-cols-3 gap-6">
            {/* Performance */}
            <div className="col-span-1">
              <h4 className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-3">Recent Quiz Performance</h4>
              <div className="space-y-3">
                {selectedStudent.quizScores.map((q) => (
                  <ProgressBar
                    key={q.label}
                    label={q.label}
                    value={q.value}
                    showValue
                    size="sm"
                    color={q.value >= 60 ? 'primary' : 'danger'}
                  />
                ))}
              </div>
            </div>

            {/* Weak Areas */}
            <div className="col-span-1">
              <h4 className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-3">Weak Areas</h4>
              <div className="flex flex-wrap gap-2">
                {selectedStudent.weakAreas.map((area) => (
                  <Badge key={area} variant="danger" size="sm">{area}</Badge>
                ))}
              </div>
            </div>

            {/* Engagement */}
            <div className="col-span-1">
              <h4 className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-3">Engagement</h4>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Zap className="h-4 w-4 text-[var(--text-tertiary)]" />
                  <span className="text-[var(--text-secondary)]">XP:</span>
                  <span className="font-semibold text-[var(--text-primary)]">{selectedStudent.xp}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Flame className="h-4 w-4 text-[var(--text-tertiary)]" />
                  <span className="text-[var(--text-secondary)]">Streak:</span>
                  <span className="font-semibold text-[var(--text-primary)]">{selectedStudent.streak} days</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <MessageCircle className="h-4 w-4 text-[var(--text-tertiary)]" />
                  <span className="text-[var(--text-secondary)]">Community:</span>
                  <span className="font-semibold text-[var(--text-primary)]">{selectedStudent.communityContributions} answers</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
