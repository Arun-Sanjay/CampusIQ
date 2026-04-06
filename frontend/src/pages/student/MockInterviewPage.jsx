import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  Play,
  Square,
  Download,
  RotateCcw,
  Send,
  Bot,
  User,
  CheckCircle2,
  Circle,
  MessageSquare,
  Mic,
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

const companies = [
  { name: 'Google', difficulty: 'Hard', variant: 'danger' },
  { name: 'Amazon', difficulty: 'Hard', variant: 'danger' },
  { name: 'TCS', difficulty: 'Medium', variant: 'warning' },
  { name: 'Infosys', difficulty: 'Easy', variant: 'success' },
  { name: 'Microsoft', difficulty: 'Hard', variant: 'danger' },
  { name: 'Startup', difficulty: 'Medium', variant: 'warning' },
]

const personas = [
  { emoji: '\uD83D\uDE0A', name: 'Friendly', desc: 'Supportive and encouraging, guides you gently' },
  { emoji: '\uD83D\uDE24', name: 'Tough', desc: 'Pushes hard, expects precise answers' },
  { emoji: '\u26A1', name: 'Rapid Fire', desc: 'Quick questions, tests speed and recall' },
  { emoji: '\uD83C\uDFB2', name: 'Unpredictable', desc: 'Random question styles, keeps you on edge' },
]

const rounds = [
  { label: 'HR', short: 'HR' },
  { label: 'Technical', short: 'TECH' },
  { label: 'Sys Design', short: 'SD' },
  { label: 'Managerial', short: 'MGR' },
  { label: 'Negotiation', short: 'NEG' },
]

const interviewMessages = [
  { role: 'ai', text: 'Welcome to Round 2: Technical Interview. Let\'s start with a coding question.' },
  { role: 'ai', text: 'Given an array of integers, find two numbers that add up to a specific target. What approach would you use?' },
  { role: 'user', text: 'I\'d use a hash map approach. Iterate through the array, for each element check if target minus current exists in the map. If yes, return both indices. Otherwise, add current element to the map. This gives O(n) time complexity.' },
  { role: 'ai', text: 'Good approach! Now, what would happen if the array contains duplicate values? How would you handle that edge case?' },
]

const roundScores = [
  { name: 'HR', score: 7.2, max: 10 },
  { name: 'Technical', score: 6.5, max: 10 },
  { name: 'Sys Design', score: 8.1, max: 10 },
  { name: 'Managerial', score: 7.8, max: 10 },
  { name: 'Negotiation', score: 6.0, max: 10 },
]

const improvements = [
  'Practice edge case analysis for coding problems \u2014 you missed 3 edge cases across rounds.',
  'Work on salary negotiation techniques \u2014 your counter-offers lacked market data backing.',
  'Improve system design communication \u2014 start with high-level before diving into details.',
]

export default function MockInterviewPage() {
  const [view, setView] = useState('setup')
  const [selectedCompany, setSelectedCompany] = useState('Google')
  const [selectedPersona, setSelectedPersona] = useState('Tough')
  const [mode, setMode] = useState('text')
  const [input, setInput] = useState('')
  const currentRound = 1 // 0-indexed, round 2

  const handleSend = () => {
    if (!input.trim()) return
    setInput('')
  }

  // ---- SETUP VIEW ----
  if (view === 'setup') {
    return (
      <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
        {/* Company selector */}
        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Select Company</CardLabel>
          <div className="grid grid-cols-3 gap-3">
            {companies.map(c => (
              <div
                key={c.name}
                onClick={() => setSelectedCompany(c.name)}
                className={clsx(
                  'card-hover p-4 cursor-pointer flex items-center justify-between',
                  selectedCompany === c.name && 'border-[var(--border-strong)] ring-1 ring-primary/20',
                )}
              >
                <span className="font-medium text-[var(--text-primary)]">{c.name}</span>
                <Badge variant={c.variant} size="sm">{c.difficulty}</Badge>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Persona selector */}
        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Select Persona</CardLabel>
          <div className="grid grid-cols-2 gap-3">
            {personas.map(p => (
              <div
                key={p.name}
                onClick={() => setSelectedPersona(p.name)}
                className={clsx(
                  'card-hover p-4 cursor-pointer',
                  selectedPersona === p.name && 'border-[var(--border-strong)] ring-1 ring-primary/20',
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{p.emoji}</span>
                  <span className="font-medium text-[var(--text-primary)]">{p.name}</span>
                </div>
                <p className="text-xs text-[var(--text-tertiary)]">{p.desc}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Mode toggle */}
        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Interview Mode</CardLabel>
          <div className="flex gap-2">
            <Button
              variant={mode === 'text' ? 'primary' : 'secondary'}
              icon={MessageSquare}
              onClick={() => setMode('text')}
            >
              Text
            </Button>
            <Button
              variant={mode === 'voice' ? 'primary' : 'secondary'}
              icon={Mic}
              onClick={() => setMode('voice')}
            >
              Voice
            </Button>
          </div>
        </motion.div>

        {/* Start */}
        <motion.div variants={fadeUp}>
          <Button size="lg" icon={Play} onClick={() => setView('interview')}>
            Start Interview
          </Button>
        </motion.div>
      </motion.div>
    )
  }

  // ---- INTERVIEW VIEW ----
  if (view === 'interview') {
    return (
      <motion.div className="space-y-4" variants={stagger} initial="initial" animate="animate">
        {/* Round progress */}
        <motion.div variants={fadeUp}>
          <div className="flex items-center justify-center gap-0">
            {rounds.map((r, i) => (
              <div key={r.label} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={clsx(
                      'w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors',
                      i < currentRound
                        ? 'bg-success border-success text-white'
                        : i === currentRound
                          ? 'bg-primary border-primary text-primary-foreground'
                          : 'border-[var(--border-default)] text-[var(--text-tertiary)] bg-[var(--bg-secondary)]',
                    )}
                  >
                    {i < currentRound ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                  </div>
                  <span className={clsx(
                    'text-[10px] mt-1 font-medium',
                    i === currentRound ? 'text-[var(--text-primary)]' : 'text-[var(--text-tertiary)]',
                  )}>
                    {r.label}
                  </span>
                </div>
                {i < rounds.length - 1 && (
                  <div
                    className={clsx(
                      'w-12 h-0.5 mx-1 mt-[-12px]',
                      i < currentRound ? 'bg-success' : 'bg-[var(--border-default)]',
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Round banner */}
        <motion.div variants={fadeUp}>
          <Card className="text-center py-2">
            <span className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
              Round 2: Technical Interview
            </span>
          </Card>
        </motion.div>

        {/* Chat area */}
        <motion.div variants={fadeUp} className="card flex flex-col" style={{ height: 'calc(100vh - 22rem)' }}>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {interviewMessages.map((msg, i) => (
              <div key={i}>
                <div className={clsx('flex gap-2', msg.role === 'user' && 'justify-end')}>
                  {msg.role === 'ai' && (
                    <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="h-3.5 w-3.5 text-primary" />
                    </div>
                  )}
                  <div
                    className={clsx(
                      'max-w-[80%] rounded-lg px-3 py-2 text-sm',
                      msg.role === 'ai'
                        ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                        : 'bg-primary text-primary-foreground',
                    )}
                  >
                    {msg.text}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center shrink-0">
                      <User className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
                    </div>
                  )}
                </div>
                {/* Per-answer feedback (after user messages) */}
                {msg.role === 'user' && (
                  <div className="flex justify-end mt-1.5 mr-9">
                    <div className="bg-success/5 border border-success/20 rounded-md px-3 py-1.5 text-xs text-[var(--text-secondary)]">
                      <span className="font-semibold text-success">Score: 7/10</span> \u2014 Good approach but missing edge case handling
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-[var(--border-default)] flex gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Type your answer..."
              className="input-base flex-1"
            />
            <Button size="sm" icon={Send} onClick={handleSend}>Send</Button>
          </div>
        </motion.div>

        {/* Bottom actions */}
        <motion.div variants={fadeUp} className="flex gap-3">
          <Button variant="danger" icon={Square} onClick={() => setView('setup')}>
            End Interview
          </Button>
          <Button variant="secondary" onClick={() => setView('debrief')}>
            View Debrief
          </Button>
        </motion.div>
      </motion.div>
    )
  }

  // ---- DEBRIEF VIEW ----
  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Overall score */}
      <motion.div variants={fadeUp}>
        <Card className="text-center py-6">
          <span className="stat-value text-5xl">72/100</span>
          <div className="mt-3">
            <Badge variant="success" size="lg">LIKELY HIRED</Badge>
          </div>
          <p className="text-sm text-[var(--text-tertiary)] mt-2">
            {selectedCompany} \u2014 {selectedPersona} Persona
          </p>
        </Card>
      </motion.div>

      {/* Per-round breakdown */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Round Breakdown</CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {roundScores.map(r => (
              <div key={r.name} className="flex items-center gap-4">
                <span className="w-24 text-sm font-medium text-[var(--text-primary)]">{r.name}</span>
                <div className="flex-1">
                  <ProgressBar
                    value={r.score}
                    max={r.max}
                    size="md"
                    color={r.score >= 7.5 ? 'success' : r.score >= 6.5 ? 'warning' : 'danger'}
                  />
                </div>
                <span className="text-sm font-semibold text-[var(--text-primary)] w-14 text-right">
                  {r.score}/{r.max}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Top 3 Improvements */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Top 3 Improvements</CardTitle>
          </CardHeader>
          <ol className="space-y-3">
            {improvements.map((item, i) => (
              <li key={i} className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                  {i + 1}
                </span>
                <p className="text-sm text-[var(--text-secondary)]">{item}</p>
              </li>
            ))}
          </ol>
        </Card>
      </motion.div>

      {/* Actions */}
      <motion.div variants={fadeUp} className="flex gap-3">
        <Button icon={Download}>Download Report</Button>
        <Button variant="secondary" icon={RotateCcw} onClick={() => setView('setup')}>
          Try Again
        </Button>
      </motion.div>
    </motion.div>
  )
}
