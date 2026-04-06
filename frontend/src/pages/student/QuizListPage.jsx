import { useState } from 'react'
import { motion } from 'framer-motion'
import { Play, Clock, HelpCircle, TrendingDown, AlertTriangle } from 'lucide-react'
import Card, { CardLabel } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import ProgressBar from '../../components/ui/ProgressBar'

const stagger = {
  animate: { transition: { staggerChildren: 0.06 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const availableQuizzes = [
  { id: 1, subject: 'DAA', source: 'Chapter 3 — Graph Algorithms', difficulty: 'Medium', questions: 10, time: 15 },
  { id: 2, subject: 'CN', source: 'Chapter 4 — Transport Layer', difficulty: 'Hard', questions: 10, time: 20 },
  { id: 3, subject: 'DMS', source: 'Chapter 2 — Set Theory & Relations', difficulty: 'Easy', questions: 10, time: 12 },
  { id: 4, subject: 'OS', source: 'Chapter 5 — Process Scheduling', difficulty: 'Medium', questions: 10, time: 15 },
  { id: 5, subject: 'DBMS', source: 'Chapter 6 — Normalization', difficulty: 'Hard', questions: 10, time: 20 },
  { id: 6, subject: 'DAA', source: 'Chapter 5 — Dynamic Programming', difficulty: 'Easy', questions: 10, time: 12 },
]

const historyData = [
  { date: 'Apr 5, 2026', subject: 'DAA', score: 85, time: '12m 30s', difficulty: 'Medium' },
  { date: 'Apr 4, 2026', subject: 'CN', score: 72, time: '18m 15s', difficulty: 'Hard' },
  { date: 'Apr 3, 2026', subject: 'DMS', score: 95, time: '8m 45s', difficulty: 'Easy' },
  { date: 'Apr 2, 2026', subject: 'OS', score: 58, time: '16m 20s', difficulty: 'Medium' },
  { date: 'Apr 1, 2026', subject: 'DBMS', score: 40, time: '19m 50s', difficulty: 'Hard' },
]

const weakAreas = [
  { topic: 'Dynamic Programming', subject: 'DAA', score: 35, action: 'Retake DP quiz and review Chapter 5 notes' },
  { topic: 'TCP/UDP Protocols', subject: 'CN', score: 42, action: 'Review Transport Layer lecture slides' },
  { topic: 'Normalization (BCNF)', subject: 'DBMS', score: 48, action: 'Practice normalization exercises from lab manual' },
  { topic: 'Deadlock Detection', subject: 'OS', score: 55, action: 'Re-read Chapter 7 and attempt Practice Set 3' },
]

const difficultyVariant = { Easy: 'success', Medium: 'warning', Hard: 'danger' }

function scoreColor(score) {
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  return 'text-danger'
}

const tabs = ['Available', 'History', 'Weak Areas']

export default function QuizListPage() {
  const [activeTab, setActiveTab] = useState('Available')

  return (
    <div className="space-y-6">
      {/* Tab Bar */}
      <div className="flex gap-1 p-1 rounded-lg bg-[var(--bg-tertiary)] w-fit">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
              activeTab === tab
                ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Available Tab */}
      {activeTab === 'Available' && (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          variants={stagger}
          initial="initial"
          animate="animate"
        >
          {availableQuizzes.map((quiz) => (
            <motion.div key={quiz.id} variants={fadeUp}>
              <Card hover className="flex flex-col gap-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-[var(--text-primary)]">{quiz.subject}</h3>
                    <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{quiz.source}</p>
                  </div>
                  <Badge variant={difficultyVariant[quiz.difficulty]} size="sm">
                    {quiz.difficulty}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-[var(--text-tertiary)]">
                  <span className="flex items-center gap-1">
                    <HelpCircle className="h-3 w-3" />
                    {quiz.questions} questions
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {quiz.time} min
                  </span>
                </div>
                <Button size="sm" icon={Play} className="w-full mt-auto">
                  Start Quiz
                </Button>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* History Tab */}
      {activeTab === 'History' && (
        <motion.div variants={fadeUp} initial="initial" animate="animate">
          <Card padding={false}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    {['Date', 'Subject', 'Score', 'Time', 'Difficulty'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {historyData.map((row, i) => (
                    <tr
                      key={i}
                      className="border-b border-[var(--border-default)] last:border-0 hover:bg-[var(--bg-tertiary)] transition-colors"
                    >
                      <td className="px-4 py-3 text-[var(--text-secondary)]">{row.date}</td>
                      <td className="px-4 py-3 font-medium text-[var(--text-primary)]">{row.subject}</td>
                      <td className={`px-4 py-3 font-semibold ${scoreColor(row.score)}`}>{row.score}%</td>
                      <td className="px-4 py-3 text-[var(--text-secondary)]">{row.time}</td>
                      <td className="px-4 py-3">
                        <Badge variant={difficultyVariant[row.difficulty]} size="sm">
                          {row.difficulty}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Weak Areas Tab */}
      {activeTab === 'Weak Areas' && (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
          variants={stagger}
          initial="initial"
          animate="animate"
        >
          {weakAreas.map((area) => (
            <motion.div key={area.topic} variants={fadeUp}>
              <Card className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-[var(--text-primary)] flex items-center gap-2">
                      <AlertTriangle className="h-3.5 w-3.5 text-danger" />
                      {area.topic}
                    </h3>
                    <span className="text-xs text-[var(--text-tertiary)]">{area.subject}</span>
                  </div>
                  <span className="text-sm font-semibold text-danger">{area.score}%</span>
                </div>
                <ProgressBar
                  value={area.score}
                  max={100}
                  size="sm"
                  color={area.score < 40 ? 'danger' : area.score < 60 ? 'warning' : 'primary'}
                />
                <div className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                  <TrendingDown className="h-3 w-3 text-[var(--text-tertiary)] mt-0.5 shrink-0" />
                  <span>{area.action}</span>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  )
}
