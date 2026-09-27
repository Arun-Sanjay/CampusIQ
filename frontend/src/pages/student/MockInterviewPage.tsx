import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from 'react'
import { motion, type Variants } from 'framer-motion'
import { clsx } from 'clsx'
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Download,
  Loader2,
  MessageSquare,
  Mic,
  MicOff,
  Play,
  RotateCcw,
  Send,
  Square,
  User,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardLabel } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import type { BadgeVariant } from '../../components/ui/Badge'
import ProgressBar from '../../components/ui/ProgressBar'
import { ApiError, interviewsApi } from '../../api/client'
import LiveInterviewRoom from '../../components/interview/LiveInterviewRoom'
import type {
  HireVerdict,
  InterviewPersona,
  InterviewSessionResponse,
  InterviewTranscriptTurn,
  LiveRoundFinalizeResponse,
  VoiceCapabilitiesResponse,
} from '../../types'

const stagger: Variants = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

interface CompanyChoice {
  name: string
  difficulty: 'Easy' | 'Medium' | 'Hard'
  variant: BadgeVariant
}

const companies: CompanyChoice[] = [
  { name: 'Google', difficulty: 'Hard', variant: 'danger' },
  { name: 'Amazon', difficulty: 'Hard', variant: 'danger' },
  { name: 'Microsoft', difficulty: 'Hard', variant: 'danger' },
  { name: 'Flipkart', difficulty: 'Medium', variant: 'warning' },
  { name: 'TCS', difficulty: 'Easy', variant: 'success' },
  { name: 'Startup', difficulty: 'Medium', variant: 'warning' },
]

interface PersonaChoice {
  value: InterviewPersona
  emoji: string
  name: string
  desc: string
}

const personas: PersonaChoice[] = [
  { value: 'friendly', emoji: '😊', name: 'Friendly', desc: 'Supportive and encouraging, guides you gently' },
  { value: 'tough', emoji: '😤', name: 'Tough', desc: 'Pushes hard, expects precise answers' },
  { value: 'rapid_fire', emoji: '⚡', name: 'Rapid Fire', desc: 'Quick questions, tests speed and recall' },
  { value: 'unpredictable', emoji: '🎲', name: 'Unpredictable', desc: 'Random question styles, keeps you on edge' },
]

const rounds = [
  { label: 'HR', num: 1 },
  { label: 'Technical', num: 2 },
  { label: 'Sys Design', num: 3 },
  { label: 'Managerial', num: 4 },
  { label: 'Negotiation', num: 5 },
]

type View = 'setup' | 'interview' | 'debrief'

function verdictBadgeVariant(v: HireVerdict): BadgeVariant {
  if (v === 'strong_hire') return 'success'
  if (v === 'hire') return 'success'
  if (v === 'leaning_no') return 'warning'
  return 'danger'
}

function verdictLabel(v: HireVerdict): string {
  return {
    strong_hire: 'STRONG HIRE',
    hire: 'LIKELY HIRED',
    leaning_no: 'LEANING NO',
    no_hire: 'NO HIRE',
  }[v]
}

/** Chat-bubble transcript with per-answer score reveals. Shared by text mode
 *  and the live voice mode's graded-transcript panel. */
function TranscriptView({ turns }: { turns: InterviewTranscriptTurn[] }) {
  return (
    <>
      {turns.map((msg, i) => (
        <div key={i}>
          <div className={clsx('flex gap-2', msg.role === 'user' && 'justify-end')}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <Bot className="h-3.5 w-3.5 text-primary" />
              </div>
            )}
            <div
              className={clsx(
                'max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-line',
                msg.role === 'assistant'
                  ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                  : 'bg-primary text-primary-foreground',
              )}
            >
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center shrink-0">
                <User className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
              </div>
            )}
          </div>
          {msg.role === 'user' && msg.score !== null && msg.score !== undefined && (
            <div className="flex justify-end mt-1.5 mr-9">
              <div className="bg-success/5 border border-success/20 rounded-md px-3 py-1.5 text-xs text-[var(--text-secondary)]">
                <span
                  className={clsx(
                    'font-semibold',
                    msg.score >= 7.5
                      ? 'text-success'
                      : msg.score >= 5
                        ? 'text-warning'
                        : 'text-danger',
                  )}
                >
                  Score: {msg.score.toFixed(1)}/10
                </span>
                {msg.score_reason && <span> — {msg.score_reason}</span>}
              </div>
            </div>
          )}
        </div>
      ))}
    </>
  )
}

export default function MockInterviewPage() {
  const [view, setView] = useState<View>('setup')
  const [selectedCompany, setSelectedCompany] = useState<string>('Google')
  const [selectedRole, setSelectedRole] = useState<string>('SWE')
  const [selectedPersona, setSelectedPersona] = useState<InterviewPersona>('tough')
  const [mode, setMode] = useState<'text' | 'voice'>('text')
  const [input, setInput] = useState<string>('')

  const [session, setSession] = useState<InterviewSessionResponse | null>(null)
  const [starting, setStarting] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Live voice mode — ElevenLabs conversational agent
  const [capabilities, setCapabilities] = useState<VoiceCapabilitiesResponse | null>(null)

  const chatScrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll the transcript to the bottom whenever it updates
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [session?.transcript?.length, view])

  // Fetch which voice paths the server supports. `agent_available` gates the
  // live conversational voice interview.
  useEffect(() => {
    let cancelled = false
    interviewsApi
      .voiceCapabilities()
      .then((data) => {
        if (!cancelled) setCapabilities(data)
      })
      .catch(() => {
        // Capabilities endpoint unreachable — voice mode stays disabled.
      })
    return () => {
      cancelled = true
    }
  }, [])

  // True when the live ElevenLabs interview agent is configured on the server.
  const agentAvailable = capabilities?.agent_available ?? false

  // While a live voice interview runs, poll the session so background round
  // grades (and the final debrief) surface as they land.
  useEffect(() => {
    if (view !== 'interview' || mode !== 'voice' || !session) return
    const sessionId = session.id
    const timer = window.setInterval(() => {
      interviewsApi
        .get(sessionId)
        .then((fresh) => {
          setSession(fresh)
          if (fresh.status === 'completed') setView('debrief')
        })
        .catch(() => {
          /* transient — keep polling */
        })
    }, 3500)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, mode, session?.id])

  // ── Actions ──

  const handleStart = async () => {
    setStarting(true)
    setError(null)
    try {
      const data = await interviewsApi.start({
        company_target: selectedCompany,
        role_target: selectedRole,
        interviewer_persona: selectedPersona,
        mode,
      })
      setSession(data)
      setView('interview')
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Could not start the interview',
      )
    } finally {
      setStarting(false)
    }
  }

  const handleSend = async () => {
    if (!session || !input.trim() || sending) return
    const content = input.trim()
    setInput('')
    setSending(true)
    setError(null)
    try {
      const result = await interviewsApi.sendMessage(session.id, { content })
      setSession(result.session)
      if (result.interview_completed) {
        setView('debrief')
      }
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Failed to submit your answer',
      )
    } finally {
      setSending(false)
    }
  }

  // ── Live voice mode (ElevenLabs conversational agent) ──
  const handleRoundFinalized = (resp: LiveRoundFinalizeResponse) => {
    setSession(resp.session)
    // The final round's debrief is generated in the background; the session
    // poll flips the view to 'debrief' once it's ready.
  }

  const handleActiveRoundChange = (roundNumber: number) => {
    // Optimistically advance the stepper; the next poll reconciles statuses.
    setSession((prev) => (prev ? { ...prev, current_round: roundNumber } : prev))
  }

  const handleEnd = async () => {
    if (!session) return
    if (!window.confirm('End this interview now? We\'ll generate your debrief with whatever we have so far.')) return
    setSending(true)
    try {
      const updated = await interviewsApi.end(session.id)
      setSession(updated)
      setView('debrief')
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Failed to end the interview',
      )
    } finally {
      setSending(false)
    }
  }

  const handleTryAgain = () => {
    setSession(null)
    setInput('')
    setError(null)
    setView('setup')
  }

  // ── Derived state ──

  const currentRoundIdx = session ? session.current_round - 1 : 0
  const transcript = session?.transcript ?? []
  const report = session?.feedback_report ?? null

  const roundBanner = useMemo(() => {
    if (!session) return 'Round 1: HR / Behavioural'
    const summary = session.round_summaries.find((r) => r.status === 'active')
    if (summary) return `Round ${summary.round_number}: ${summary.name}`
    const last = session.round_summaries[session.round_summaries.length - 1]
    return last ? `Round ${last.round_number}: ${last.name}` : 'Interview'
  }, [session])

  // ══════════════════════════════════════════════════════════════
  // SETUP VIEW
  // ══════════════════════════════════════════════════════════════
  if (view === 'setup') {
    return (
      <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
        {error && (
          <motion.div
            variants={fadeUp}
            className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger"
          >
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}

        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Select Company</CardLabel>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {companies.map((c) => (
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

        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Role</CardLabel>
          <div className="flex flex-wrap gap-2">
            {['SWE', 'SDE', 'Backend Engineer', 'ML Engineer', 'Full-Stack Intern'].map((r) => (
              <Button
                key={r}
                variant={selectedRole === r ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setSelectedRole(r)}
              >
                {r}
              </Button>
            ))}
          </div>
        </motion.div>

        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Select Persona</CardLabel>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {personas.map((p) => (
              <div
                key={p.value}
                onClick={() => setSelectedPersona(p.value)}
                className={clsx(
                  'card-hover p-4 cursor-pointer',
                  selectedPersona === p.value && 'border-[var(--border-strong)] ring-1 ring-primary/20',
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

        <motion.div variants={fadeUp}>
          <CardLabel className="mb-3">Interview Mode</CardLabel>
          <div className="flex gap-2 items-center flex-wrap">
            <Button
              variant={mode === 'text' ? 'primary' : 'secondary'}
              icon={MessageSquare}
              onClick={() => setMode('text')}
            >
              Text
            </Button>
            <Button
              variant={mode === 'voice' ? 'primary' : 'secondary'}
              icon={agentAvailable ? Mic : MicOff}
              onClick={() => agentAvailable && setMode('voice')}
              disabled={!agentAvailable}
              title={
                agentAvailable
                  ? 'Live voice — talk to the AI interviewer in real time, one round at a time.'
                  : 'Live voice interview is not configured on the server. Use Text mode.'
              }
            >
              Voice (Live)
            </Button>
            {capabilities && (
              <span className="text-xs text-[var(--text-tertiary)] ml-1">
                {agentAvailable
                  ? 'Real-time voice agent ready'
                  : 'Voice agent off — text mode only'}
              </span>
            )}
          </div>
        </motion.div>

        <motion.div variants={fadeUp}>
          <Button
            size="lg"
            icon={starting ? undefined : Play}
            onClick={() => void handleStart()}
            disabled={starting}
          >
            {starting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin inline" />
                Starting…
              </>
            ) : (
              'Start Interview'
            )}
          </Button>
        </motion.div>
      </motion.div>
    )
  }

  // ══════════════════════════════════════════════════════════════
  // INTERVIEW VIEW
  // ══════════════════════════════════════════════════════════════
  if (view === 'interview') {
    return (
      <motion.div className="space-y-4" variants={stagger} initial="initial" animate="animate">
        {error && (
          <motion.div
            variants={fadeUp}
            className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger"
          >
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}

        <motion.div variants={fadeUp}>
          <div className="flex items-center justify-center gap-0">
            {rounds.map((r, i) => {
              const roundSummary = session?.round_summaries[i]
              const status = roundSummary?.status ?? 'locked'
              return (
                <div key={r.label} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={clsx(
                        'w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors',
                        status === 'completed'
                          ? 'bg-success border-success text-white'
                          : status === 'active'
                            ? 'bg-primary border-primary text-primary-foreground'
                            : 'border-[var(--border-default)] text-[var(--text-tertiary)] bg-[var(--bg-secondary)]',
                      )}
                    >
                      {status === 'completed' ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                    </div>
                    <span
                      className={clsx(
                        'text-[10px] mt-1 font-medium',
                        status === 'active'
                          ? 'text-[var(--text-primary)]'
                          : 'text-[var(--text-tertiary)]',
                      )}
                    >
                      {r.label}
                    </span>
                  </div>
                  {i < rounds.length - 1 && (
                    <div
                      className={clsx(
                        'w-12 h-0.5 mx-1 mt-[-12px]',
                        i < currentRoundIdx ? 'bg-success' : 'bg-[var(--border-default)]',
                      )}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </motion.div>

        <motion.div variants={fadeUp}>
          <Card className="text-center py-2">
            <span className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
              {roundBanner}
            </span>
          </Card>
        </motion.div>

        {mode === 'voice' ? (
          <>
            <motion.div variants={fadeUp}>
              <LiveInterviewRoom
                session={session!}
                onRoundFinalized={handleRoundFinalized}
                onActiveRoundChange={handleActiveRoundChange}
                onError={setError}
              />
            </motion.div>
            {transcript.length > 0 && (
              <motion.div variants={fadeUp} className="card">
                <div className="px-4 pt-3 text-[10px] uppercase tracking-wider text-[var(--text-tertiary)]">
                  Graded transcript
                </div>
                <div className="max-h-72 overflow-y-auto p-4 space-y-4">
                  <TranscriptView turns={transcript} />
                </div>
              </motion.div>
            )}
          </>
        ) : (
          <motion.div
            variants={fadeUp}
            className="card flex flex-col h-[calc(100dvh-22rem)]"
          >
            <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
              <TranscriptView turns={transcript} />
              {sending && (
                <div className="flex gap-2">
                  <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div className="bg-[var(--bg-tertiary)] rounded-lg px-3 py-2 text-sm text-[var(--text-tertiary)] animate-pulse">
                    Thinking…
                  </div>
                </div>
              )}
            </div>
            <div className="p-3 border-t border-[var(--border-default)] flex gap-2">
              <input
                value={input}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                  e.key === 'Enter' && void handleSend()
                }
                placeholder="Type your answer…"
                className="input-base flex-1"
                disabled={sending}
              />
              <Button
                size="sm"
                icon={sending ? undefined : Send}
                onClick={() => void handleSend()}
                disabled={sending || !input.trim()}
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Send'}
              </Button>
            </div>
          </motion.div>
        )}

        <motion.div variants={fadeUp} className="flex gap-3">
          <Button variant="secondary" icon={Square} onClick={() => void handleEnd()} disabled={sending}>
            End Interview
          </Button>
          <span className="text-xs text-[var(--text-tertiary)] self-center">
            Persona: {session?.interviewer_persona} · Company: {session?.company_target}
          </span>
        </motion.div>
      </motion.div>
    )
  }

  // ══════════════════════════════════════════════════════════════
  // DEBRIEF VIEW
  // ══════════════════════════════════════════════════════════════
  const overallScore = session?.overall_score ?? 0
  const verdict: HireVerdict = report?.hire_verdict ?? 'leaning_no'

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      <motion.div variants={fadeUp}>
        <Card className="text-center py-6">
          <span className="stat-value text-5xl">{overallScore.toFixed(0)}/100</span>
          <div className="mt-3">
            <Badge variant={verdictBadgeVariant(verdict)} size="lg">
              {verdictLabel(verdict)}
            </Badge>
          </div>
          <p className="text-sm text-[var(--text-tertiary)] mt-2">
            {session?.company_target} — {session?.interviewer_persona} persona
          </p>
          {report?.headline && (
            <p className="text-sm text-[var(--text-secondary)] mt-3 italic max-w-xl mx-auto">
              "{report.headline}"
            </p>
          )}
        </Card>
      </motion.div>

      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Round Breakdown</CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {session?.round_summaries.map((r) => {
              const score = r.avg_score ?? 0
              return (
                <div key={r.round_number} className="flex items-center gap-4">
                  <span className="w-32 text-sm font-medium text-[var(--text-primary)]">
                    {r.name}
                  </span>
                  <div className="flex-1">
                    <ProgressBar
                      value={score}
                      max={10}
                      size="md"
                      color={score >= 7.5 ? 'success' : score >= 5 ? 'warning' : 'danger'}
                    />
                  </div>
                  <span className="text-sm font-semibold text-[var(--text-primary)] w-16 text-right tabular-nums">
                    {r.avg_score !== null ? `${r.avg_score.toFixed(1)}/10` : '—'}
                  </span>
                </div>
              )
            })}
          </div>
        </Card>
      </motion.div>

      {report && (
        <>
          {report.strengths.length > 0 && (
            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle>Strengths</CardTitle>
                </CardHeader>
                <ul className="space-y-2">
                  {report.strengths.map((s, i) => (
                    <li key={i} className="flex gap-3 text-sm text-[var(--text-secondary)]">
                      <span className="w-5 h-5 rounded-full bg-success/10 flex items-center justify-center text-[10px] font-bold text-success shrink-0">
                        ✓
                      </span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </motion.div>
          )}

          {report.improvements.length > 0 && (
            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle>Top Improvements</CardTitle>
                </CardHeader>
                <ol className="space-y-3">
                  {report.improvements.map((item, i) => (
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
          )}

          {(report.standout_answer || report.biggest_gap) && (
            <motion.div variants={fadeUp}>
              <Card>
                <CardHeader>
                  <CardTitle>Highlights</CardTitle>
                </CardHeader>
                <div className="space-y-3 text-sm">
                  {report.standout_answer && (
                    <div>
                      <p className="text-xs uppercase tracking-wider text-success mb-1">
                        Standout Answer
                      </p>
                      <p className="text-[var(--text-secondary)]">{report.standout_answer}</p>
                    </div>
                  )}
                  {report.biggest_gap && (
                    <div>
                      <p className="text-xs uppercase tracking-wider text-danger mb-1">
                        Biggest Gap
                      </p>
                      <p className="text-[var(--text-secondary)]">{report.biggest_gap}</p>
                    </div>
                  )}
                </div>
              </Card>
            </motion.div>
          )}
        </>
      )}

      <motion.div variants={fadeUp} className="flex gap-3">
        <Button icon={Download} onClick={() => window.print()}>
          Download Report
        </Button>
        <Button variant="secondary" icon={RotateCcw} onClick={handleTryAgain}>
          Try Again
        </Button>
      </motion.div>
    </motion.div>
  )
}
