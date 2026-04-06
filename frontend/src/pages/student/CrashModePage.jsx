import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  AlertTriangle,
  Clock,
  Target,
  Zap,
  BookOpen,
  Swords,
  FileText,
  CheckSquare,
  Square,
  TrendingUp,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import ProgressBar from '../../components/ui/ProgressBar'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const studyPlan = [
  {
    priority: 1,
    topic: 'Arrays & Hashing Patterns',
    time: '2.5 hours',
    improvement: '+8%',
    badge: 'Critical',
    badgeVariant: 'danger',
    done: false,
  },
  {
    priority: 2,
    topic: 'Binary Search Variations',
    time: '2 hours',
    improvement: '+7%',
    badge: 'Critical',
    badgeVariant: 'danger',
    done: false,
  },
  {
    priority: 3,
    topic: 'Graph BFS/DFS',
    time: '2.5 hours',
    improvement: '+6%',
    badge: 'Critical',
    badgeVariant: 'danger',
    done: false,
  },
  {
    priority: 4,
    topic: 'Dynamic Programming Basics',
    time: '2 hours',
    improvement: '+5%',
    badge: 'Important',
    badgeVariant: 'warning',
    done: false,
  },
  {
    priority: 5,
    topic: 'System Design Fundamentals',
    time: '1.5 hours',
    improvement: '+5%',
    badge: 'Important',
    badgeVariant: 'warning',
    done: false,
  },
  {
    priority: 6,
    topic: 'Behavioral Question Prep',
    time: '1.5 hours',
    improvement: '+3%',
    badge: 'Optional',
    badgeVariant: 'default',
    done: false,
  },
]

export default function CrashModePage() {
  const [plan, setPlan] = useState(studyPlan)

  const toggleDone = (index) => {
    setPlan(prev =>
      prev.map((item, i) => (i === index ? { ...item, done: !item.done } : item)),
    )
  }

  const completedCount = plan.filter(t => t.done).length

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Top banner */}
      <motion.div variants={fadeUp}>
        <Card className="border-danger/30 bg-danger/5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-5 w-5 text-danger" />
                <h2 className="text-lg font-bold text-danger">CRASH MODE</h2>
              </div>
              <p className="text-sm text-[var(--text-secondary)]">Interview in 3 days</p>
              <div className="flex items-center gap-2 mt-1">
                <Target className="h-4 w-4 text-[var(--text-tertiary)]" />
                <span className="text-sm text-[var(--text-primary)]">Preparing for: <strong>Google SWE</strong></span>
              </div>
            </div>
            <div className="text-right">
              <span className="stat-value text-3xl text-danger">71:42:18</span>
              <p className="text-xs text-[var(--text-tertiary)] mt-1">Time remaining</p>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Optimized Study Plan */}
      <motion.div variants={fadeUp}>
        <CardLabel className="mb-3">Optimized Study Plan</CardLabel>
        <div className="space-y-3">
          {plan.map((item, i) => (
            <motion.div key={i} variants={fadeUp}>
              <Card className={clsx(item.done && 'opacity-60')}>
                <div className="flex items-center gap-4">
                  {/* Checkbox */}
                  <button
                    onClick={() => toggleDone(i)}
                    className="shrink-0 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
                  >
                    {item.done ? (
                      <CheckSquare className="h-5 w-5 text-success" />
                    ) : (
                      <Square className="h-5 w-5" />
                    )}
                  </button>

                  {/* Priority number */}
                  <span
                    className={clsx(
                      'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
                      item.badgeVariant === 'danger'
                        ? 'bg-danger/10 text-danger'
                        : item.badgeVariant === 'warning'
                          ? 'bg-warning/10 text-warning'
                          : 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]',
                    )}
                  >
                    {item.priority}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className={clsx(
                      'text-sm font-medium',
                      item.done
                        ? 'line-through text-[var(--text-tertiary)]'
                        : 'text-[var(--text-primary)]',
                    )}>
                      {item.topic}
                    </p>
                  </div>

                  {/* Time */}
                  <div className="flex items-center gap-1 text-xs text-[var(--text-secondary)]">
                    <Clock className="h-3 w-3" />
                    {item.time}
                  </div>

                  {/* Improvement */}
                  <span className="text-xs font-semibold text-success">{item.improvement}</span>

                  {/* Badge */}
                  <Badge variant={item.badgeVariant} size="sm">{item.badge}</Badge>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Bottom stats */}
      <motion.div variants={fadeUp}>
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <CardLabel>Total Study Time</CardLabel>
                <p className="text-lg font-bold text-[var(--text-primary)]">12 hours</p>
              </div>
              <div className="w-px h-8 bg-[var(--border-default)]" />
              <div>
                <CardLabel>Predicted Improvement</CardLabel>
                <p className="text-lg font-bold text-success">+34%</p>
              </div>
              <div className="w-px h-8 bg-[var(--border-default)]" />
              <div>
                <CardLabel>Progress</CardLabel>
                <p className="text-lg font-bold text-[var(--text-primary)]">{completedCount}/{plan.length}</p>
              </div>
            </div>
            <ProgressBar
              value={completedCount}
              max={plan.length}
              color="success"
              size="lg"
              className="w-32"
            />
          </div>
        </Card>
      </motion.div>

      {/* Quick Access */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Quick Access</CardTitle>
          </CardHeader>
          <div className="flex gap-3">
            <Button icon={Swords}>Start Mock Interview</Button>
            <Button variant="secondary" icon={BookOpen}>Take Practice Quiz</Button>
            <Button variant="secondary" icon={FileText}>Review Resume</Button>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
