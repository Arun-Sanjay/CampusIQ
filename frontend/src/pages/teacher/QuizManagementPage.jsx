import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Sparkles, Clock, CheckCircle, FileEdit,
  Users, BarChart3, ToggleLeft, ToggleRight,
} from 'lucide-react'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { CardLabel } from '../../components/ui/Card'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const tabs = ['Pending Review', 'Published', 'Drafts']

const pendingQuizzes = [
  {
    title: 'Graph Traversal & Shortest Paths',
    subject: 'Design & Analysis of Algorithms',
    questions: 15,
    generatedAt: '2h ago',
  },
  {
    title: 'Deadlock Detection & Recovery',
    subject: 'Operating Systems',
    questions: 12,
    generatedAt: '5h ago',
  },
  {
    title: 'TCP/IP Protocol Suite',
    subject: 'Computer Networks',
    questions: 10,
    generatedAt: '1d ago',
  },
]

const publishedQuizzes = [
  {
    title: 'Dynamic Programming Basics',
    subject: 'Design & Analysis of Algorithms',
    attempts: 142,
    avgScore: 68,
    active: true,
  },
  {
    title: 'Process Scheduling',
    subject: 'Operating Systems',
    attempts: 136,
    avgScore: 74,
    active: true,
  },
  {
    title: 'SQL Joins & Subqueries',
    subject: 'Database Management Systems',
    attempts: 128,
    avgScore: 71,
    active: false,
  },
  {
    title: 'OSI Model Fundamentals',
    subject: 'Computer Networks',
    attempts: 145,
    avgScore: 79,
    active: true,
  },
]

const draftQuizzes = [
  {
    title: 'B-Trees & Indexing',
    subject: 'Database Management Systems',
    questions: 8,
    lastEdited: '2d ago',
  },
  {
    title: 'Neural Network Backpropagation',
    subject: 'Machine Learning',
    questions: 5,
    lastEdited: '3d ago',
  },
]

export default function QuizManagementPage() {
  const [activeTab, setActiveTab] = useState('Pending Review')

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Header */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Quiz Management</h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-0.5">Review AI-generated quizzes and manage published content</p>
        </div>
        <Button icon={Sparkles}>Generate Quiz</Button>
      </motion.div>

      {/* Tabs */}
      <motion.div variants={fadeUp} className="flex gap-1 border-b border-[var(--border-default)]">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
              activeTab === tab
                ? 'text-[var(--text-primary)]'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            }`}
          >
            {tab}
            {activeTab === tab && (
              <motion.div
                layoutId="quiz-tab"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
              />
            )}
          </button>
        ))}
      </motion.div>

      {/* Pending Review */}
      {activeTab === 'Pending Review' && (
        <motion.div className="grid gap-4" variants={stagger} initial="initial" animate="animate">
          {pendingQuizzes.map((quiz, i) => (
            <motion.div
              key={quiz.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <Card hover>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-sm text-[var(--text-primary)]">{quiz.title}</h3>
                      <Badge variant="info" size="sm">
                        <Sparkles className="h-3 w-3 mr-0.5" />
                        AI Generated
                      </Badge>
                    </div>
                    <p className="text-xs text-[var(--text-tertiary)]">{quiz.subject}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-[var(--text-secondary)]">
                      <span>{quiz.questions} questions</span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Generated {quiz.generatedAt}
                      </span>
                    </div>
                  </div>
                  <Button size="sm" icon={FileEdit}>Review & Publish</Button>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Published */}
      {activeTab === 'Published' && (
        <motion.div className="grid gap-4" variants={stagger} initial="initial" animate="animate">
          {publishedQuizzes.map((quiz, i) => (
            <motion.div
              key={quiz.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <Card hover>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm text-[var(--text-primary)] mb-1">{quiz.title}</h3>
                    <p className="text-xs text-[var(--text-tertiary)]">{quiz.subject}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-[var(--text-secondary)]">
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        {quiz.attempts} attempts
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <BarChart3 className="h-3 w-3" />
                        Avg: {quiz.avgScore}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={quiz.active ? 'success' : 'default'} size="sm" dot>
                      {quiz.active ? 'Active' : 'Inactive'}
                    </Badge>
                    {quiz.active ? (
                      <ToggleRight className="h-5 w-5 text-success cursor-pointer" />
                    ) : (
                      <ToggleLeft className="h-5 w-5 text-[var(--text-tertiary)] cursor-pointer" />
                    )}
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Drafts */}
      {activeTab === 'Drafts' && (
        <motion.div className="grid gap-4" variants={stagger} initial="initial" animate="animate">
          {draftQuizzes.map((quiz, i) => (
            <motion.div
              key={quiz.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <Card hover>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm text-[var(--text-primary)] mb-1">{quiz.title}</h3>
                    <p className="text-xs text-[var(--text-tertiary)]">{quiz.subject}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-[var(--text-secondary)]">
                      <span>{quiz.questions} questions</span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Edited {quiz.lastEdited}
                      </span>
                    </div>
                  </div>
                  <Button variant="secondary" size="sm" icon={FileEdit}>Continue Editing</Button>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  )
}
