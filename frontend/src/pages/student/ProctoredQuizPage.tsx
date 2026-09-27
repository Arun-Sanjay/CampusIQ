import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ShieldCheck, Camera, Maximize, AlertTriangle, Clock, Send, Smartphone } from 'lucide-react'
import { Button, Card, Badge } from '../../components/ui'
import { quizzesApi } from '../../api/client'
import { useIsMobile } from '../../hooks/useMediaQuery'
import { useProctoring } from '../../hooks/useProctoring'
import { useConfidenceTracker } from '../../hooks/useConfidenceTracker'
import type { QuizForStudent, StartAttemptResponse } from '../../types'

type Phase = 'loading' | 'preflight' | 'running' | 'submitting' | 'error'

function fmt(sec: number | null): string {
  if (sec == null) return '--:--'
  const m = Math.floor(sec / 60), s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function ProctoredQuizPage() {
  const { quizId = '' } = useParams()
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [quiz, setQuiz] = useState<QuizForStudent | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [err, setErr] = useState<string | null>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [idx, setIdx] = useState(0)
  const [warning, setWarning] = useState<string | null>(null)
  const [facePresent, setFacePresent] = useState(true)
  const [start, setStart] = useState<StartAttemptResponse | null>(null)

  const videoRef = useRef<HTMLVideoElement>(null)
  const answersRef = useRef(answers)
  answersRef.current = answers
  const liveRef = useRef<number | null>(1)
  const tracker = useConfidenceTracker()
  liveRef.current = tracker.liveEyeContact

  useEffect(() => {
    quizzesApi.getAsStudent(quizId)
      .then((q) => { setQuiz(q); setPhase('preflight') })
      .catch((e) => { setErr(e.detail || 'Could not load quiz'); setPhase('error') })
  }, [quizId])

  // Attach the camera stream to the preview element + the MediaPipe tracker.
  useEffect(() => {
    if (stream && videoRef.current) {
      videoRef.current.srcObject = stream
      void videoRef.current.play().catch(() => {})
      tracker.start(stream).catch(() => {})
    }
  }, [stream, tracker])

  const requestCamera = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      setStream(s)
    } catch {
      setWarning('Camera access is required for a proctored test. Please allow it and retry.')
    }
  }, [])

  useEffect(() => {
    if (phase === 'preflight') void requestCamera()
  }, [phase, requestCamera])

  const cleanup = useCallback(() => {
    try { tracker.stop() } catch { /* noop */ }
    stream?.getTracks().forEach((t) => t.stop())
  }, [stream, tracker])

  const submitRef = useRef<((auto: boolean) => void) | null>(null)

  const proctor = useProctoring({
    quizId,
    startedAtIso: start?.started_at ?? new Date().toISOString(),
    serverNowIso: start?.server_now ?? new Date().toISOString(),
    timeLimitSeconds: start?.time_limit_seconds ?? null,
    enabled: phase === 'running',
    onAutoSubmit: () => submitRef.current?.(true),
    onWarn: (m) => { setWarning(m); window.setTimeout(() => setWarning(null), 4000) },
  })

  const doSubmit = useCallback(async (auto: boolean) => {
    if (!quiz || !start) return
    setPhase('submitting')
    proctor.markSubmitted()
    const payload = {
      answers: quiz.questions.map((q) => ({ question_id: q.id, student_answer: answersRef.current[q.id] || '' }))
        .filter((a) => a.student_answer),
      started_attempt_id: start.attempt_id,
      proctor: { ...proctor.counters.current, auto_submitted: auto || proctor.counters.current.auto_submitted },
      // Discrete events (tab/fullscreen/copy) are already logged live via the
      // proctor-events endpoint; face-absence is carried in the summary above.
    }
    try {
      const result = await quizzesApi.submitAttempt(quiz.id, payload)
      sessionStorage.setItem(`quiz-result-${result.id}`, JSON.stringify(result))
      proctor.teardown()
      cleanup()
      navigate(`/student/quizzes/${quiz.id}/result/${result.id}`)
    } catch (e) {
      setErr((e as { detail?: string }).detail || 'Submission failed')
      setPhase('error')
    }
  }, [quiz, start, navigate, cleanup, proctor])
  submitRef.current = doSubmit

  // Face-presence polling (1s) while the test runs.
  useEffect(() => {
    if (phase !== 'running' || !tracker.available) return
    const addFaceSeconds = proctor.addFaceSeconds
    const id = setInterval(() => {
      const present = liveRef.current !== null
      setFacePresent(present)
      if (!present) addFaceSeconds('absent', 1)
    }, 1000)
    return () => clearInterval(id)
  }, [phase, tracker.available, proctor.addFaceSeconds])

  const begin = useCallback(async () => {
    try {
      const s = await quizzesApi.startAttempt(quizId)
      setStart(s)
      await proctor.enterFullscreen()
      setPhase('running')
    } catch (e) {
      const detail = (e as { detail?: string; status?: number }).detail
      setErr(detail || 'Could not start the test')
      setPhase('error')
    }
  }, [quizId, proctor])

  useEffect(() => () => { cleanup() }, [cleanup])

  if (phase === 'loading') return <div className="p-6 text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading…</div>
  if (phase === 'error') {
    return (
      <div className="max-w-lg mx-auto mt-10">
        <Card className="text-center py-8">
          <AlertTriangle className="h-7 w-7 mx-auto mb-2" style={{ color: 'var(--danger,#e5484d)' }} />
          <p style={{ color: 'var(--text-primary)' }}>{err}</p>
          <div className="mt-4"><Button variant="secondary" onClick={() => navigate('/student/quizzes')}>Back to quizzes</Button></div>
        </Card>
      </div>
    )
  }

  // ── Pre-flight ──
  if (phase === 'preflight' && quiz) {
    return (
      <div className="max-w-xl mx-auto mt-8 space-y-4">
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="h-5 w-5" style={{ color: 'var(--text-primary)' }} />
            <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{quiz.title} — Proctored Test</h1>
          </div>
          <ul className="text-sm space-y-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
            <li>• The test runs in fullscreen. Leaving the tab or fullscreen is recorded.</li>
            <li>• Your webcam must stay on; the system checks you're present.</li>
            <li>• Copy/paste and right-click are disabled. <strong>Single attempt.</strong></li>
            <li>• {quiz.time_limit_minutes ? `Time limit: ${quiz.time_limit_minutes} min (auto-submits at 0).` : 'No time limit.'}</li>
          </ul>
          {isMobile && (
            <div
              className="flex items-start gap-2.5 rounded-lg p-3 mb-4"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-strong)' }}
            >
              <Smartphone className="h-5 w-5 shrink-0 mt-0.5" style={{ color: 'var(--text-primary)' }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Best taken on a laptop
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  Proctoring (fullscreen + tab monitoring) is limited on phones. You can still proceed.
                </p>
              </div>
            </div>
          )}
          <div className="rounded-lg overflow-hidden mb-3" style={{ background: '#000', aspectRatio: '16/9' }}>
            <video ref={videoRef} muted playsInline className="w-full h-full object-cover" />
          </div>
          <div className="flex items-center gap-2 text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
            <Camera className="h-4 w-4" />
            {stream ? (tracker.available ? 'Camera ready · face tracking active' : 'Camera ready · face tracking unavailable (will proceed)') : 'Waiting for camera permission…'}
          </div>
          {warning && <div className="text-sm mb-3" style={{ color: 'var(--danger,#e5484d)' }}>{warning}</div>}
          {!quiz.can_attempt ? (
            <div className="text-sm" style={{ color: 'var(--danger,#e5484d)' }}>
              You have already used your attempt for this test.
            </div>
          ) : (
            <Button onClick={begin}>
              <Maximize className="h-4 w-4" /> Begin Test
            </Button>
          )}
          {!stream && (
            <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
              No camera detected — the test will still enforce fullscreen, tab-switch and timer rules.
            </p>
          )}
        </Card>
      </div>
    )
  }

  // ── Running ──
  if (!quiz) return null
  const q = quiz.questions[idx]
  const answeredCount = Object.values(answers).filter(Boolean).length
  const low = (proctor.remaining ?? 999) <= 60

  return (
    <div className="max-w-3xl mx-auto py-4 space-y-4">
      {/* Top bar: timer + webcam + status */}
      <div className="flex items-center gap-3 sticky top-0 z-10 py-2" style={{ background: 'var(--bg-primary)' }}>
        <div className="flex items-center gap-2 font-mono text-lg font-bold"
          style={{ color: low ? 'var(--danger,#e5484d)' : 'var(--text-primary)' }}>
          <Clock className="h-5 w-5" /> {fmt(proctor.remaining)}
        </div>
        <Badge variant={facePresent ? 'success' : 'danger'}>{facePresent ? 'Face detected' : 'Face not detected'}</Badge>
        <div className="ml-auto rounded-lg overflow-hidden border" style={{ width: 120, height: 68, borderColor: 'var(--border-default)' }}>
          <video ref={videoRef} muted playsInline className="w-full h-full object-cover" />
        </div>
      </div>

      {warning && (
        <div className="rounded-lg p-2 text-sm text-center" style={{ background: 'var(--danger,#e5484d)', color: '#fff' }}>
          {warning}
        </div>
      )}

      <Card>
        <div className="flex items-center gap-2 mb-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>
          <span>Question {idx + 1} of {quiz.questions.length}</span>
          <span>· {answeredCount} answered</span>
          {q.co && <Badge variant="default">{q.co}</Badge>}
          <Badge variant="info">{q.marks} marks</Badge>
        </div>
        <div className="text-base font-medium mb-4" style={{ color: 'var(--text-primary)' }}>{q.question_text}</div>
        <div className="space-y-2">
          {(q.options || []).map((opt) => {
            const selected = answers[q.id] === opt
            return (
              <button key={opt} onClick={() => setAnswers({ ...answers, [q.id]: opt })}
                className="w-full text-left rounded-lg p-3 text-sm transition-colors"
                style={{
                  background: selected ? 'var(--bg-elevated)' : 'var(--bg-tertiary)',
                  border: `1px solid ${selected ? 'var(--text-primary)' : 'var(--border-default)'}`,
                  color: 'var(--text-primary)',
                }}>
                {opt}
              </button>
            )
          })}
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <Button variant="ghost" disabled={idx === 0} onClick={() => setIdx(idx - 1)}>Previous</Button>
        <div className="flex gap-1">
          {quiz.questions.map((qq, i) => (
            <button key={qq.id} onClick={() => setIdx(i)}
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: answers[qq.id] ? 'var(--text-primary)' : i === idx ? 'var(--text-tertiary)' : 'var(--border-default)' }} />
          ))}
        </div>
        {idx < quiz.questions.length - 1 ? (
          <Button onClick={() => setIdx(idx + 1)}>Next</Button>
        ) : (
          <Button onClick={() => doSubmit(false)} disabled={phase === 'submitting'}>
            <Send className="h-4 w-4" /> {phase === 'submitting' ? 'Submitting…' : 'Submit test'}
          </Button>
        )}
      </div>
    </div>
  )
}
