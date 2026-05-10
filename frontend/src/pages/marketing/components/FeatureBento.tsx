import { motion } from 'framer-motion'
import {
  BookOpen,
  School,
  ListChecks,
  FileText,
  Mic,
  Briefcase,
  type LucideIcon,
} from 'lucide-react'

interface Feature {
  id: string
  icon: LucideIcon
  title: string
  desc: string
  imgSlot: string
  size?: 'large' | 'wide' | 'standard'
}

const FEATURES: Feature[] = [
  {
    id: 'note-assistant',
    icon: BookOpen,
    title: 'AI Note Assistant',
    desc: 'Chat with your actual lecture material. Streaming answers grounded in cited document chunks via pgvector RAG.',
    imgSlot: 'bento-note-assistant',
    size: 'large',
  },
  {
    id: 'college-gpt',
    icon: School,
    title: 'CollegeGPT',
    desc: 'Handbook, regulations, and placement records — answered.',
    imgSlot: 'bento-college-gpt',
  },
  {
    id: 'adaptive-quiz',
    icon: ListChecks,
    title: 'Adaptive Quizzes',
    desc: 'AI-generated, difficulty that flexes with your weak areas.',
    imgSlot: 'bento-adaptive-quiz',
  },
  {
    id: 'smart-resume',
    icon: FileText,
    title: 'Smart Resume + ATS',
    desc: 'Coach-built bullets, ATS scoring against any JD.',
    imgSlot: 'bento-smart-resume',
  },
  {
    id: 'job-tracker',
    icon: Briefcase,
    title: 'Job Tracker + Fit Scores',
    desc: 'Kanban + cosine-similarity fit per role.',
    imgSlot: 'bento-job-tracker',
  },
  {
    id: 'voice-interview',
    icon: Mic,
    title: 'Voice Mock Interview',
    desc: 'Five rounds. Five voices. One verdict — backed by Claude scoring each turn 0–10.',
    imgSlot: 'bento-voice-interview',
    size: 'wide',
  },
]

const card = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
}

export default function FeatureBento() {
  return (
    <section id="features" className="section">
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <span className="eyebrow">What's inside</span>
          <h2
            className="display"
            style={{
              fontSize: 'clamp(32px, 5vw, 56px)',
              margin: '12px 0 14px',
            }}
          >
            Everything an engineering student needs.{' '}
            <span className="gradient-text">One platform.</span>
          </h2>
          <p
            style={{
              color: 'var(--landing-fg-muted)',
              maxWidth: 620,
              margin: '0 auto',
              fontSize: 16,
              lineHeight: 1.6,
            }}
          >
            Twenty-six features across learning, placement, and growth — all wired into a single readiness score.
          </p>
        </div>

        <div className="bento">
          {FEATURES.map((f, i) => {
            const sizeClass =
              f.size === 'large' ? 'bento-large' : f.size === 'wide' ? 'bento-wide' : ''
            return (
              <motion.div
                key={f.id}
                {...card}
                transition={{ ...card.transition, delay: i * 0.04 }}
                className={`tile glow-border ${sizeClass}`}
              >
                <div
                  className="img-slot"
                  data-img={f.imgSlot}
                  data-img-label={f.imgSlot}
                  style={{ flex: 1, minHeight: 0 }}
                />
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  <div className="tile-icon">
                    <f.icon size={20} strokeWidth={2} />
                  </div>
                  <div>
                    <h3
                      className="display"
                      style={{
                        fontSize: 18,
                        fontWeight: 600,
                        margin: '0 0 4px',
                        color: 'var(--landing-fg)',
                      }}
                    >
                      {f.title}
                    </h3>
                    <p
                      style={{
                        margin: 0,
                        fontSize: 13,
                        color: 'var(--landing-fg-muted)',
                        lineHeight: 1.5,
                      }}
                    >
                      {f.desc}
                    </p>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
