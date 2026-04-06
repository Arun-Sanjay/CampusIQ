import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  Camera,
  Video,
  Square,
  Eye,
  Activity,
  MessageCircle,
  Gauge,
  Sparkles,
  TrendingUp,
  Dumbbell,
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

const metrics = [
  { label: 'Eye Contact', value: 78, type: 'progress', color: 'success', icon: Eye },
  { label: 'Posture Score', value: 82, type: 'progress', color: 'success', icon: Activity },
  { label: 'Filler Words', value: '12', type: 'badge', variant: 'warning', icon: MessageCircle },
  { label: 'Speaking Pace', value: '145 WPM', type: 'badge', variant: 'success', icon: Gauge },
  { label: 'Clarity Score', value: 71, type: 'progress', color: 'warning', icon: Sparkles },
  { label: 'Overall Confidence', value: 74, type: 'progress', color: 'primary', icon: TrendingUp },
]

const drills = [
  {
    title: 'Power Pause Drill',
    description: 'Practice inserting deliberate 2-second pauses between key points instead of using filler words. Record a 1-minute response and aim for zero fillers.',
  },
  {
    title: 'Mirror Eye Contact',
    description: 'Maintain eye contact with yourself in a mirror for 60 seconds while answering a behavioral question. Focus on the camera lens when recording.',
  },
  {
    title: 'Structured Answer Framework',
    description: 'Use the STAR method (Situation, Task, Action, Result) to structure 3 different behavioral responses. Time each for under 2 minutes.',
  },
]

export default function ConfidenceCoachPage() {
  const [isRecording, setIsRecording] = useState(false)

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Record Response */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Record Response</CardTitle>
          </CardHeader>
          <div className="mb-3 p-3 rounded-lg bg-[var(--bg-tertiary)]">
            <CardLabel>Prompt</CardLabel>
            <p className="text-sm text-[var(--text-primary)] mt-1">Tell me about a time you led a team project</p>
          </div>
          <div
            className={clsx(
              'h-64 rounded-lg border-2 border-dashed flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors',
              isRecording
                ? 'border-danger bg-danger/5'
                : 'border-[var(--border-default)] bg-[var(--bg-secondary)] hover:border-[var(--border-strong)]',
            )}
            onClick={() => !isRecording && setIsRecording(true)}
          >
            {isRecording ? (
              <>
                <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center animate-pulse">
                  <Video className="h-6 w-6 text-danger" />
                </div>
                <p className="text-sm text-danger font-medium">Recording in progress...</p>
                <p className="text-xs text-[var(--text-tertiary)]">0:34 elapsed</p>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
                  <Camera className="h-6 w-6 text-[var(--text-tertiary)]" />
                </div>
                <p className="text-sm text-[var(--text-tertiary)]">Click to record your response</p>
              </>
            )}
          </div>
          <div className="flex gap-2 mt-3">
            {isRecording ? (
              <Button variant="danger" icon={Square} onClick={() => setIsRecording(false)}>
                Stop Recording
              </Button>
            ) : (
              <Button icon={Video} onClick={() => setIsRecording(true)}>
                Start Recording
              </Button>
            )}
          </div>
        </Card>
      </motion.div>

      {/* Results metrics */}
      <motion.div variants={fadeUp}>
        <CardLabel className="mb-3">Previous Session Results</CardLabel>
        <div className="grid grid-cols-3 gap-4">
          {metrics.map(m => {
            const Icon = m.icon
            return (
              <Card key={m.label}>
                <div className="flex items-start justify-between mb-3">
                  <span className="label">{m.label}</span>
                  <Icon className="h-4 w-4 text-[var(--text-tertiary)]" />
                </div>
                {m.type === 'progress' ? (
                  <>
                    <span className="stat-value">{m.value}%</span>
                    <ProgressBar value={m.value} color={m.color} size="sm" className="mt-2" />
                  </>
                ) : (
                  <div className="flex items-end gap-2">
                    <span className="stat-value">{m.value}</span>
                    <Badge variant={m.variant} size="sm">
                      {m.variant === 'success' ? 'Ideal' : 'Needs work'}
                    </Badge>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      </motion.div>

      {/* Growth Timeline */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Growth Timeline</CardTitle>
          </CardHeader>
          <div className="h-40 flex items-center justify-center rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-default)]">
            <p className="text-sm text-[var(--text-tertiary)]">
              Line chart showing improvement over 8 sessions will render here
            </p>
          </div>
        </Card>
      </motion.div>

      {/* Recommended Drills */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Recommended Drills</CardTitle>
            <Dumbbell className="h-4 w-4 text-[var(--text-tertiary)]" />
          </CardHeader>
          <div className="space-y-4">
            {drills.map((d, i) => (
              <div key={i} className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{d.title}</p>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">{d.description}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
