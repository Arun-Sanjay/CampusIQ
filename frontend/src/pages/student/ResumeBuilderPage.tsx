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
  BarChart3,
  Bot,
  Code,
  Download,
  ExternalLink,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Send,
  User as UserIcon,
} from 'lucide-react'
import Card, { CardLabel } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import TextArea from '../../components/ui/TextArea'
import { ApiError, resumeApi } from '../../api/client'
import type {
  ATSScoreResponse,
  ResumeChatHistoryItem,
  ResumeContent,
  ResumeResponse,
} from '../../types'

const stagger: Variants = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

interface UIChatMsg {
  role: 'assistant' | 'user'
  text: string
  isPending?: boolean
}

function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function atsBadgeVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score >= 75) return 'success'
  if (score >= 55) return 'warning'
  return 'danger'
}

export default function ResumeBuilderPage() {
  const [resume, setResume] = useState<ResumeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [messages, setMessages] = useState<UIChatMsg[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  // ATS modal
  const [atsOpen, setAtsOpen] = useState(false)
  const [atsJD, setAtsJD] = useState('')
  const [atsScoring, setAtsScoring] = useState(false)
  const [atsResult, setAtsResult] = useState<ATSScoreResponse | null>(null)

  // GitHub import modal
  const [ghOpen, setGhOpen] = useState(false)
  const [ghUsername, setGhUsername] = useState('')
  const [ghImporting, setGhImporting] = useState(false)
  const [ghResult, setGhResult] = useState<{
    count: number
    names: string[]
  } | null>(null)

  const chatScrollRef = useRef<HTMLDivElement>(null)

  // ── Initial load ──
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const [r, h] = await Promise.all([resumeApi.me(), resumeApi.history()])
        if (cancelled) return
        setResume(r)
        const initial: UIChatMsg[] = h.messages.map((m: ResumeChatHistoryItem) => ({
          role: m.role,
          text: m.content,
        }))
        if (initial.length === 0) {
          initial.push({
            role: 'assistant',
            text: "Hey! I'm your CampusIQ Resume Coach. Let's build your resume one section at a time. What's your full name and the email you want recruiters to use?",
          })
        }
        setMessages(initial)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load your resume',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || sending) return
    setError(null)
    setInput('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: message },
      { role: 'assistant', text: '…', isPending: true },
    ])
    setSending(true)

    try {
      const result = await resumeApi.chat({ message })
      setMessages((prev) => {
        const next = prev.filter((m) => !m.isPending)
        next.push({ role: 'assistant', text: result.ai_message })
        return next
      })
      // Refresh resume — quickest way to keep ats_score / last_updated in sync
      setResume((prev) =>
        prev
          ? { ...prev, content: result.content, last_updated: new Date().toISOString() }
          : prev,
      )
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Resume Coach call failed',
      )
      setMessages((prev) => prev.filter((m) => !m.isPending))
    } finally {
      setSending(false)
    }
  }

  const handleAtsScore = async () => {
    if (!atsJD.trim()) return
    setAtsScoring(true)
    setError(null)
    try {
      const result = await resumeApi.scoreAts({ job_description: atsJD })
      setAtsResult(result)
      // Bump the displayed score
      setResume((prev) => (prev ? { ...prev, ats_score: result.score } : prev))
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'ATS scoring failed',
      )
    } finally {
      setAtsScoring(false)
    }
  }

  const handleGithubImport = async () => {
    if (!ghUsername.trim()) return
    setGhImporting(true)
    setError(null)
    try {
      const result = await resumeApi.importGithub({ username: ghUsername.trim(), top_n: 5 })
      setResume((prev) =>
        prev ? { ...prev, content: result.content, last_updated: new Date().toISOString() } : prev,
      )
      setGhResult({
        count: result.imported_count,
        names: result.projects.map((p) => p.name),
      })
    } catch (err) {
      setError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'GitHub import failed',
      )
    } finally {
      setGhImporting(false)
    }
  }

  const handlePrint = () => {
    window.print()
  }

  const content: ResumeContent | null = resume?.content ?? null
  const atsScore = resume?.ats_score ?? null

  const personal = content?.personal
  const hasAnyData = useMemo(() => {
    if (!content) return false
    return (
      Boolean(personal?.name) ||
      content.education.length > 0 ||
      content.projects.length > 0 ||
      content.skills.length > 0
    )
  }, [content, personal])

  if (loading) {
    return (
      <Card className="flex items-center justify-center gap-2 py-10 text-[var(--text-tertiary)]">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading your resume…
      </Card>
    )
  }

  return (
    <motion.div className="space-y-4" variants={stagger} initial="initial" animate="animate">
      {error && (
        <motion.div
          variants={fadeUp}
          className="flex items-start gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-sm text-danger no-print"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      {/* Top bar: name + ATS score */}
      <motion.div variants={fadeUp} className="flex items-center justify-between no-print">
        <div className="text-sm text-[var(--text-tertiary)]">
          {hasAnyData ? (
            <>
              <span className="text-[var(--text-secondary)]">Last updated </span>
              {formatRelative(resume?.last_updated ?? new Date().toISOString())}
            </>
          ) : (
            'Empty resume — start chatting to fill it in'
          )}
        </div>
        <div className="flex items-center gap-2">
          {atsScore !== null && atsScore > 0 ? (
            <Badge variant={atsBadgeVariant(atsScore)} size="lg">
              ATS Score: {atsScore.toFixed(0)}/100
            </Badge>
          ) : (
            <Badge size="lg">ATS not scored yet</Badge>
          )}
        </div>
      </motion.div>

      {/* Split layout */}
      <motion.div
        variants={fadeUp}
        className="flex gap-4 no-print"
        style={{ height: 'calc(100vh - 14rem)' }}
      >
        {/* Left: AI Chat */}
        <div className="w-1/2 flex flex-col card">
          <div className="p-3 border-b border-[var(--border-default)] flex items-center justify-between">
            <CardLabel>AI RESUME COACH</CardLabel>
            <span className="text-xs text-[var(--text-tertiary)]">
              {messages.length} message{messages.length === 1 ? '' : 's'}
            </span>
          </div>
          <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={clsx('flex gap-2', msg.role === 'user' && 'justify-end')}
              >
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
                    msg.isPending && 'animate-pulse',
                  )}
                >
                  {msg.text}
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center shrink-0">
                    <UserIcon className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-[var(--border-default)] flex gap-2">
            <input
              value={input}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
              onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                e.key === 'Enter' && void handleSend()
              }
              placeholder="Tell the coach about yourself…"
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
        </div>

        {/* Right: Resume Preview */}
        <div className="w-1/2 overflow-y-auto" id="resume-preview-wrapper">
          <Card className="h-full">
            {!hasAnyData ? (
              <p className="text-sm text-[var(--text-tertiary)] text-center py-12">
                Your resume preview will appear here as you chat with the coach. Start by sending
                your name and email on the left.
              </p>
            ) : (
              <div className="space-y-5 print-resume">
                <div className="border-b border-[var(--border-default)] pb-4">
                  <h2 className="text-2xl font-bold text-[var(--text-primary)]">
                    {personal?.name || 'Your Name'}
                  </h2>
                  {content?.summary && (
                    <p className="text-sm text-[var(--text-secondary)] mt-1">
                      {content.summary}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-[var(--text-secondary)]">
                    {personal?.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3" />
                        {personal.email}
                      </span>
                    )}
                    {personal?.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" />
                        {personal.phone}
                      </span>
                    )}
                    {personal?.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {personal.location}
                      </span>
                    )}
                    {personal?.github && (
                      <span className="flex items-center gap-1">
                        <ExternalLink className="h-3 w-3" />
                        {personal.github.replace(/^https?:\/\//, '')}
                      </span>
                    )}
                  </div>
                </div>

                {content && content.education.length > 0 && (
                  <Section title="Education">
                    {content.education.map((edu, i) => (
                      <div key={i} className="space-y-0.5">
                        <p className="font-medium text-[var(--text-primary)]">
                          {edu.institution}
                        </p>
                        <p className="text-sm text-[var(--text-secondary)]">
                          {edu.degree}
                          {edu.branch && ` · ${edu.branch}`}
                          {edu.start_year && ` · ${edu.start_year}–${edu.end_year || 'present'}`}
                        </p>
                        {edu.cgpa && (
                          <p className="text-xs text-[var(--text-tertiary)]">CGPA: {edu.cgpa}</p>
                        )}
                        {edu.highlights.length > 0 && (
                          <ul className="list-disc list-inside text-xs text-[var(--text-secondary)] mt-1">
                            {edu.highlights.map((h, j) => (
                              <li key={j}>{h}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </Section>
                )}

                {content && content.experience.length > 0 && (
                  <Section title="Experience">
                    {content.experience.map((exp, i) => (
                      <div key={i} className="space-y-0.5">
                        <p className="font-medium text-[var(--text-primary)]">
                          {exp.role}
                          {exp.company && <span className="text-[var(--text-secondary)]"> · {exp.company}</span>}
                        </p>
                        <p className="text-xs text-[var(--text-tertiary)]">
                          {exp.start_date}
                          {exp.end_date && ` – ${exp.end_date}`}
                          {exp.location && ` · ${exp.location}`}
                        </p>
                        {exp.bullets.length > 0 && (
                          <ul className="list-disc list-inside text-xs text-[var(--text-secondary)] mt-1 space-y-0.5">
                            {exp.bullets.map((b, j) => (
                              <li key={j}>{b}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </Section>
                )}

                {content && content.projects.length > 0 && (
                  <Section title="Projects">
                    {content.projects.map((p, i) => (
                      <div key={i}>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {p.name}
                        </p>
                        {p.description && (
                          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                            {p.description}
                          </p>
                        )}
                        {p.tech.length > 0 && (
                          <div className="flex gap-1.5 flex-wrap mt-1.5">
                            {p.tech.map((t) => (
                              <Badge key={t} size="sm">
                                {t}
                              </Badge>
                            ))}
                          </div>
                        )}
                        {p.url && (
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[10px] text-[var(--text-tertiary)] hover:text-primary"
                          >
                            {p.url.replace(/^https?:\/\//, '')}
                          </a>
                        )}
                      </div>
                    ))}
                  </Section>
                )}

                {content && content.skills.length > 0 && (
                  <Section title="Skills">
                    <div className="flex flex-wrap gap-1.5">
                      {content.skills.map((s) => (
                        <Badge key={s} variant="primary" size="sm">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </Section>
                )}

                {content && content.certifications.length > 0 && (
                  <Section title="Certifications">
                    <ul className="list-disc list-inside text-sm text-[var(--text-secondary)] space-y-0.5">
                      {content.certifications.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </Section>
                )}

                {content && content.achievements.length > 0 && (
                  <Section title="Achievements">
                    <ul className="list-disc list-inside text-sm text-[var(--text-secondary)] space-y-0.5">
                      {content.achievements.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </Section>
                )}
              </div>
            )}
          </Card>
        </div>
      </motion.div>

      {/* Bottom action bar */}
      <motion.div variants={fadeUp} className="flex gap-3 no-print">
        <Button icon={Download} onClick={handlePrint} disabled={!hasAnyData}>
          Download PDF
        </Button>
        <Button variant="secondary" icon={BarChart3} onClick={() => setAtsOpen(true)}>
          ATS Score
        </Button>
        <Button variant="secondary" icon={Code} onClick={() => setGhOpen(true)}>
          Import from GitHub
        </Button>
      </motion.div>

      {/* ATS Modal */}
      <Modal isOpen={atsOpen} onClose={() => setAtsOpen(false)} title="Score against a job description" size="lg">
        <div className="space-y-4">
          <TextArea
            label="Job Description"
            placeholder="Paste the JD here…"
            rows={8}
            value={atsJD}
            onChange={(e) => setAtsJD(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setAtsOpen(false)} disabled={atsScoring}>
              Cancel
            </Button>
            <Button onClick={() => void handleAtsScore()} disabled={atsScoring || atsJD.length < 20}>
              {atsScoring ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Scoring…
                </>
              ) : (
                'Score My Resume'
              )}
            </Button>
          </div>

          {atsResult && (
            <div className="space-y-3 border-t border-[var(--border-default)] pt-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Score</span>
                <Badge variant={atsBadgeVariant(atsResult.score)} size="lg">
                  {atsResult.score.toFixed(0)} / 100
                </Badge>
              </div>
              <div>
                <p className="text-xs uppercase text-[var(--text-tertiary)] mb-1">
                  Matched Keywords
                </p>
                <div className="flex flex-wrap gap-1">
                  {atsResult.matched_keywords.map((k) => (
                    <Badge key={k} variant="success" size="sm">
                      {k}
                    </Badge>
                  ))}
                  {atsResult.matched_keywords.length === 0 && (
                    <span className="text-xs text-[var(--text-tertiary)]">None</span>
                  )}
                </div>
              </div>
              <div>
                <p className="text-xs uppercase text-[var(--text-tertiary)] mb-1">
                  Missing Keywords
                </p>
                <div className="flex flex-wrap gap-1">
                  {atsResult.missing_keywords.map((k) => (
                    <Badge key={k} variant="danger" size="sm">
                      {k}
                    </Badge>
                  ))}
                  {atsResult.missing_keywords.length === 0 && (
                    <span className="text-xs text-[var(--text-tertiary)]">None</span>
                  )}
                </div>
              </div>
              {atsResult.suggestions.length > 0 && (
                <div>
                  <p className="text-xs uppercase text-[var(--text-tertiary)] mb-1">Suggestions</p>
                  <ul className="list-disc list-inside text-sm text-[var(--text-secondary)] space-y-0.5">
                    {atsResult.suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>

      {/* GitHub Import Modal */}
      <Modal isOpen={ghOpen} onClose={() => setGhOpen(false)} title="Import projects from GitHub" size="md">
        <div className="space-y-4">
          <Input
            label="GitHub username"
            placeholder="e.g. arunsanjay"
            value={ghUsername}
            onChange={(e) => setGhUsername(e.target.value)}
          />
          <p className="text-xs text-[var(--text-tertiary)]">
            We'll fetch your top public repos sorted by stars and add them to the Projects
            section. Forks and archived repos are skipped.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setGhOpen(false)} disabled={ghImporting}>
              Cancel
            </Button>
            <Button onClick={() => void handleGithubImport()} disabled={ghImporting || !ghUsername.trim()}>
              {ghImporting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Importing…
                </>
              ) : (
                'Import top 5'
              )}
            </Button>
          </div>

          {ghResult && (
            <div className="border-t border-[var(--border-default)] pt-4">
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Imported {ghResult.count} project{ghResult.count === 1 ? '' : 's'}
              </p>
              {ghResult.names.length > 0 && (
                <ul className="list-disc list-inside text-xs text-[var(--text-secondary)] mt-2 space-y-0.5">
                  {ghResult.names.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </Modal>
    </motion.div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)] uppercase tracking-wider mb-2">
        {title}
      </h3>
      <div className="space-y-3">{children}</div>
    </div>
  )
}
