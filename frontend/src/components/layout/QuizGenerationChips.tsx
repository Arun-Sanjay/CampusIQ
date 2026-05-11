/**
 * Floating chip stack for in-flight AI quiz generations.
 *
 * Lives at the AppLayout level so the chips survive page navigation —
 * a teacher can fire off a Generate, walk to Analytics, and the chip
 * still ticks away in the top-right until the request completes.
 */
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'
import { useQuizGenerationStore, type PendingQuizGen } from '../../store/quizGenerationStore'

export default function QuizGenerationChips() {
  const pending = useQuizGenerationStore((s) => s.pending)
  const remove = useQuizGenerationStore((s) => s.remove)

  if (pending.length === 0) return null

  return (
    <div className="fixed top-20 right-6 z-40 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {pending.map((job) => (
          <GenerationChip key={job.id} job={job} onDismiss={() => remove(job.id)} />
        ))}
      </AnimatePresence>
    </div>
  )
}

interface GenerationChipProps {
  job: PendingQuizGen
  onDismiss: () => void
}

function GenerationChip({ job, onDismiss }: GenerationChipProps) {
  const [elapsed, setElapsed] = useState(() =>
    Math.max(0, Math.floor((Date.now() - job.startedAt) / 1000)),
  )

  useEffect(() => {
    const tick = setInterval(() => {
      setElapsed(Math.max(0, Math.floor((Date.now() - job.startedAt) / 1000)))
    }, 1000)
    return () => clearInterval(tick)
  }, [job.startedAt])

  const mm = Math.floor(elapsed / 60)
  const ss = elapsed % 60
  const elapsedLabel = mm > 0 ? `${mm}m ${ss}s` : `${ss}s`

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.96 }}
      transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="pointer-events-auto w-[300px] rounded-xl overflow-hidden shadow-elevated relative"
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-default)',
      }}
    >
      {/* Shimmer accent bar — runs across the top to signal "still working". */}
      <div className="relative h-[3px] overflow-hidden bg-[var(--bg-tertiary)]">
        <motion.div
          className="absolute inset-y-0 w-1/3"
          style={{
            background:
              'linear-gradient(90deg, transparent, var(--gradient-accent, #A78BFA), transparent)',
          }}
          animate={{ x: ['-100%', '300%'] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
        />
      </div>

      <div className="px-3.5 py-3">
        <div className="flex items-start gap-2.5">
          {/* Pulsing sparkle */}
          <div className="relative shrink-0 mt-0.5">
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{ background: 'var(--gradient-accent, #A78BFA)', opacity: 0.25 }}
              animate={{ scale: [1, 1.6, 1], opacity: [0.25, 0, 0.25] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
            />
            <div
              className="relative h-7 w-7 rounded-full flex items-center justify-center"
              style={{ background: 'rgba(167, 139, 250, 0.14)' }}
            >
              <Sparkles
                className="h-3.5 w-3.5"
                style={{ color: 'var(--gradient-accent, #A78BFA)' }}
              />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-[12px] font-semibold text-[var(--text-primary)] leading-tight">
              Generating {job.subjectCode} quiz
            </p>
            <p className="text-[10.5px] text-[var(--text-tertiary)] mt-0.5 truncate">
              {job.difficulty} · {job.numQuestions} questions
              {job.topic && ` · ${job.topic}`}
            </p>

            <div className="flex items-center gap-1.5 mt-1.5">
              <motion.span
                className="inline-block h-1 w-1 rounded-full bg-[var(--text-tertiary)]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
              />
              <motion.span
                className="inline-block h-1 w-1 rounded-full bg-[var(--text-tertiary)]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
              />
              <motion.span
                className="inline-block h-1 w-1 rounded-full bg-[var(--text-tertiary)]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
              />
              <span className="text-[10px] text-[var(--text-tertiary)] ml-1 tabular-nums">
                {elapsedLabel}
              </span>
            </div>
          </div>

          <button
            onClick={onDismiss}
            className="shrink-0 p-1 -mt-0.5 -mr-1 rounded-md text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors"
            title="Hide this chip (the quiz will still finish in the background)"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}
