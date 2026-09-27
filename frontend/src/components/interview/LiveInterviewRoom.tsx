import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ConversationProvider, useConversation } from '@elevenlabs/react'
import type { Language } from '@elevenlabs/react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { AlertCircle, Check, Loader2, Mic, MicOff, PhoneOff, Sparkles } from 'lucide-react'
import Button from '../ui/Button'
import { ApiError, interviewsApi } from '../../api/client'
import type { InterviewSessionResponse, LiveRoundFinalizeResponse } from '../../types'

const TOTAL_ROUNDS = 5
const CONNECT_TIMEOUT_MS = 20000
const ALL_ROUNDS = [1, 2, 3, 4, 5]

const ROUND_NAMES: Record<number, string> = {
  1: 'HR / Behavioural',
  2: 'Technical',
  3: 'System Design',
  4: 'Managerial',
  5: 'Negotiation',
}

type Phase = 'idle' | 'connecting' | 'live' | 'finalizing' | 'between' | 'done'

interface LiveMsg {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  session: InterviewSessionResponse
  onRoundFinalized: (resp: LiveRoundFinalizeResponse) => void
  onActiveRoundChange?: (round: number) => void
  onError?: (msg: string) => void
}

function clampRound(n: number): number {
  return Math.min(Math.max(n || 1, 1), TOTAL_ROUNDS)
}

// ── Audio-reactive orb (ChatGPT-voice style) ──────────────────────────
function VoiceOrb({
  level,
  speaking,
  active,
  connecting,
}: {
  level: number
  speaking: boolean
  active: boolean
  connecting: boolean
}) {
  const coreScale = active ? 1 + level * 0.5 : 1
  return (
    <div className="relative w-40 h-40 flex items-center justify-center">
      <motion.div
        className="absolute inset-0 rounded-full blur-3xl"
        style={{ background: 'var(--gradient-accent)' }}
        animate={{ opacity: active ? 0.3 + level * 0.5 : 0.22, scale: active ? 1 + level * 0.7 : 1 }}
        transition={{ duration: 0.12 }}
      />
      <motion.div
        className="absolute w-32 h-32 rounded-full border-2"
        style={{ borderColor: 'var(--glow-color, var(--border-strong))' }}
        animate={
          connecting
            ? { scale: [1, 1.18, 1], opacity: [0.6, 0.15, 0.6] }
            : { scale: active ? 1 + level * 0.32 : 1, opacity: speaking ? 0.8 : 0.4 }
        }
        transition={connecting ? { duration: 1.4, repeat: Infinity } : { duration: 0.12 }}
      />
      <motion.div
        className="w-24 h-24 rounded-full"
        style={{
          background: 'var(--gradient-accent)',
          boxShadow: '0 0 48px var(--glow-color, rgba(120,120,255,0.45))',
        }}
        animate={{ scale: coreScale }}
        transition={{ type: 'spring', stiffness: 320, damping: 18 }}
      />
    </div>
  )
}

function LiveInterviewRoomInner({
  session,
  onRoundFinalized,
  onActiveRoundChange,
  onError,
}: Props) {
  // Which rounds are graded (server) — drives the picker badges.
  const gradedScores = useMemo(() => {
    const m = new Map<number, number | null>()
    session.round_summaries.forEach((r) => m.set(r.round_number, r.avg_score))
    return m
  }, [session.round_summaries])

  const firstUngraded = useMemo(
    () => ALL_ROUNDS.find((n) => gradedScores.get(n) == null) ?? 1,
    [gradedScores],
  )

  const [selectedRound, setSelectedRound] = useState<number>(() =>
    clampRound(session.current_round || firstUngraded),
  )
  const [phase, setPhase] = useState<Phase>('idle')
  const [transcript, setTranscript] = useState<LiveMsg[]>([])
  const [localError, setLocalError] = useState<string | null>(null)
  const [level, setLevel] = useState(0)
  // Rounds finalized this session but not yet graded by the server.
  const [pendingRounds, setPendingRounds] = useState<Set<number>>(() => new Set())

  const conversationIdRef = useRef<string | null>(null)
  const activeRoundRef = useRef<number>(selectedRound)
  const finalizingRef = useRef(false)
  const mountedRef = useRef(true)
  const captionsEndRef = useRef<HTMLDivElement>(null)

  const conversation = useConversation()
  const convoRef = useRef(conversation)
  convoRef.current = conversation
  const status = conversation.status
  const isSpeaking = conversation.isSpeaking
  const isMuted = conversation.isMuted

  // Drop pending rounds once the server reports their grade.
  useEffect(() => {
    setPendingRounds((prev) => {
      if (prev.size === 0) return prev
      const next = new Set([...prev].filter((r) => gradedScores.get(r) == null))
      return next.size === prev.size ? prev : next
    })
  }, [gradedScores])

  const finalizeRound = useCallback(async () => {
    if (finalizingRef.current) return
    finalizingRef.current = true
    let cid = conversationIdRef.current
    if (!cid) {
      try {
        cid = convoRef.current.getId()
      } catch {
        cid = null
      }
    }
    const r = activeRoundRef.current
    if (!cid) {
      if (mountedRef.current) setPhase('between')
      finalizingRef.current = false
      return
    }
    if (mountedRef.current) setPhase('finalizing')
    try {
      const resp = await interviewsApi.liveRoundFinalize(session.id, r, cid)
      if (!mountedRef.current) return
      setPendingRounds((prev) => new Set(prev).add(r))
      onRoundFinalized(resp)
      if (resp.interview_completing) {
        setPhase('done')
      } else {
        // Hop to the next round that's neither graded nor just-finished.
        const doneOrPending = new Set<number>([
          ...session.round_summaries.filter((rs) => rs.avg_score != null).map((rs) => rs.round_number),
          ...pendingRounds,
          r,
        ])
        const next = ALL_ROUNDS.find((n) => !doneOrPending.has(n))
        setSelectedRound(next ?? r)
        setPhase('between')
      }
    } catch (err) {
      if (!mountedRef.current) return
      const msg =
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Failed to finalize the round'
      setLocalError(msg)
      onError?.(msg)
      setPhase('between')
    }
  }, [session.id, session.round_summaries, pendingRounds, onRoundFinalized, onError])

  // Drive the live state off the SDK's own connection status.
  useEffect(() => {
    if (status === 'connected') {
      setPhase((p) => (p === 'connecting' ? 'live' : p))
    } else if (status === 'error') {
      setLocalError((e) => e ?? 'Voice connection error. Please retry.')
      setPhase((p) => (p === 'connecting' || p === 'live' ? 'between' : p))
    }
  }, [status])

  // Fail clearly if the connection never lands.
  useEffect(() => {
    if (phase !== 'connecting') return
    const t = window.setTimeout(() => {
      if (!mountedRef.current) return
      setPhase((p) => {
        if (p !== 'connecting') return p
        setLocalError(
          'Could not connect to the voice agent — check your microphone permission and network, then retry.',
        )
        try {
          convoRef.current.endSession()
        } catch {
          /* noop */
        }
        return 'between'
      })
    }, CONNECT_TIMEOUT_MS)
    return () => window.clearTimeout(t)
  }, [phase])

  // Audio-reactive level for the orb.
  useEffect(() => {
    if (phase !== 'live') {
      setLevel(0)
      return
    }
    let raf = 0
    const tick = () => {
      try {
        const data = isSpeaking
          ? convoRef.current.getOutputByteFrequencyData()
          : convoRef.current.getInputByteFrequencyData()
        if (data && data.length) {
          let sum = 0
          for (let i = 0; i < data.length; i++) sum += data[i]
          setLevel(Math.min(1, sum / data.length / 90))
        }
      } catch {
        /* audio graph not ready yet */
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [phase, isSpeaking])

  useEffect(() => {
    captionsEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [transcript.length])

  useEffect(() => {
    return () => {
      mountedRef.current = false
      try {
        convoRef.current.endSession()
      } catch {
        /* already closed */
      }
    }
  }, [])

  const startRound = useCallback(
    async (roundToRun: number) => {
      setLocalError(null)
      setTranscript([])
      conversationIdRef.current = null
      finalizingRef.current = false
      activeRoundRef.current = roundToRun
      setPhase('connecting')
      onActiveRoundChange?.(roundToRun)

      // Prime mic permission up front so denials are clear and connect is fast.
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((t) => t.stop())
      } catch {
        setLocalError('Microphone access is required for the voice interview. Allow it in your browser and try again.')
        setPhase('between')
        return
      }

      let cfg
      try {
        cfg = await interviewsApi.liveRoundStart(session.id, roundToRun)
      } catch (err) {
        const msg =
          err instanceof ApiError && typeof err.detail === 'string'
            ? err.detail
            : 'Could not start the round. You can switch to Text mode.'
        setLocalError(msg)
        onError?.(msg)
        setPhase('between')
        return
      }

      try {
        // Callbacks MUST be passed to startSession (not just the hook) or they
        // won't fire for this session.
        convoRef.current.startSession({
          signedUrl: cfg.signed_url,
          connectionType: 'websocket',
          overrides: {
            agent: {
              prompt: { prompt: cfg.system_prompt },
              firstMessage: cfg.first_message,
              language: cfg.language as Language,
            },
            tts: { voiceId: cfg.voice_id },
          },
          onConnect: ({ conversationId }) => {
            conversationIdRef.current = conversationId
            if (mountedRef.current) setPhase('live')
          },
          onMessage: ({ message, role }) => {
            const text = (message || '').trim()
            if (!text || !mountedRef.current) return
            setTranscript((prev) => [
              ...prev,
              { role: role === 'user' ? 'user' : 'assistant', content: text },
            ])
          },
          onError: (m) => {
            if (!mountedRef.current) return
            setLocalError(m || 'Voice connection error')
            onError?.(m || 'Voice connection error')
          },
          onDisconnect: () => {
            if (mountedRef.current) void finalizeRound()
          },
        })
      } catch {
        const msg = 'Could not open the voice connection. Try again or use Text mode.'
        setLocalError(msg)
        onError?.(msg)
        setPhase('between')
      }
    },
    [session.id, finalizeRound, onActiveRoundChange, onError],
  )

  const endRound = useCallback(() => {
    setPhase('finalizing')
    try {
      convoRef.current.endSession() // → onDisconnect → finalizeRound()
    } catch {
      void finalizeRound()
    }
  }, [finalizeRound])

  const toggleMute = useCallback(() => {
    try {
      convoRef.current.setMuted(!convoRef.current.isMuted)
    } catch {
      /* noop */
    }
  }, [])

  const showPicker = phase === 'idle' || phase === 'between'
  const connecting = phase === 'connecting'
  const live = phase === 'live'
  const activeRound = live || connecting || phase === 'finalizing' ? activeRoundRef.current : selectedRound
  const activeName = ROUND_NAMES[activeRound] ?? `Round ${activeRound}`
  const selectedGraded = gradedScores.get(selectedRound) != null
  const statusText = connecting
    ? 'Connecting to your interviewer…'
    : live
      ? isSpeaking
        ? 'Interviewer speaking…'
        : 'Listening — your turn'
      : phase === 'finalizing'
        ? 'Wrapping up & grading…'
        : ''

  return (
    <div className="rounded-2xl overflow-hidden border" style={{ borderColor: 'var(--border-default)' }}>
      {/* Immersive voice stage */}
      <div
        className="relative flex flex-col items-center justify-center px-4 py-8 min-h-[460px]"
        style={{ background: 'radial-gradient(ellipse at 50% 0%, var(--bg-tertiary), var(--bg-secondary))' }}
      >
        <div className="absolute top-4 left-4 flex items-center gap-2 text-xs">
          <span
            className="px-2.5 py-1 rounded-full font-medium"
            style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}
          >
            Round {activeRound}/{TOTAL_ROUNDS} · {activeName}
          </span>
          {live && (
            <span className="inline-flex items-center gap-1.5 text-danger font-semibold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-danger animate-pulse" /> Live
            </span>
          )}
        </div>

        {live && (
          <button
            type="button"
            onClick={toggleMute}
            title={isMuted ? 'Unmute' : 'Mute'}
            className="absolute top-4 right-4 w-9 h-9 rounded-full flex items-center justify-center"
            style={{ background: 'var(--bg-elevated)', color: isMuted ? 'var(--text-tertiary)' : 'var(--text-secondary)' }}
          >
            {isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </button>
        )}

        <VoiceOrb level={level} speaking={isSpeaking} active={live} connecting={connecting} />

        <div className="mt-5 h-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <AnimatePresence mode="wait">
            <motion.span
              key={statusText}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2 }}
            >
              {statusText}
            </motion.span>
          </AnimatePresence>
        </div>

        {/* live captions */}
        {transcript.length > 0 && (
          <div className="mt-3 w-full max-w-lg max-h-32 overflow-y-auto space-y-2 px-1">
            {transcript.map((m, i) => (
              <div key={i} className={clsx('text-sm leading-relaxed', m.role === 'user' && 'text-right')}>
                <span className="text-[10px] uppercase tracking-wider mr-1.5 opacity-50">
                  {m.role === 'assistant' ? 'Interviewer' : 'You'}
                </span>
                <span style={{ color: m.role === 'assistant' ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>
                  {m.content}
                </span>
              </div>
            ))}
            <div ref={captionsEndRef} />
          </div>
        )}

        {/* round picker (idle / between) — choose ANY round, any order */}
        {showPicker && (
          <div className="mt-6 w-full max-w-xl flex flex-col items-center gap-4">
            <div className="text-[11px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
              Pick a round — do them in any order
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 w-full">
              {ALL_ROUNDS.map((r) => {
                const score = gradedScores.get(r)
                const graded = score != null
                const pending = pendingRounds.has(r) && !graded
                const isSel = selectedRound === r
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setSelectedRound(r)}
                    className={clsx(
                      'relative rounded-lg px-2 py-2.5 text-center transition-colors border',
                      isSel ? 'border-[var(--border-strong)] ring-1 ring-primary/30' : 'border-[var(--border-default)]',
                    )}
                    style={{ background: isSel ? 'var(--bg-elevated)' : 'var(--bg-secondary)' }}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        R{r}
                      </span>
                      {graded && <Check className="h-3 w-3 text-success" />}
                    </div>
                    <div className="text-[10px] mt-0.5 leading-tight" style={{ color: 'var(--text-tertiary)' }}>
                      {ROUND_NAMES[r]}
                    </div>
                    <div className="text-[10px] mt-1 font-medium h-3">
                      {graded ? (
                        <span className={clsx(score! >= 7.5 ? 'text-success' : score! >= 5 ? 'text-warning' : 'text-danger')}>
                          {score!.toFixed(1)}/10
                        </span>
                      ) : pending ? (
                        <span className="inline-flex items-center gap-1" style={{ color: 'var(--text-tertiary)' }}>
                          <Loader2 className="h-2.5 w-2.5 animate-spin" /> grading
                        </span>
                      ) : null}
                    </div>
                  </button>
                )
              })}
            </div>

            <Button size="lg" icon={Mic} onClick={() => void startRound(selectedRound)}>
              {selectedGraded
                ? `Re-do Round ${selectedRound} — ${ROUND_NAMES[selectedRound]}`
                : `Start Round ${selectedRound} — ${ROUND_NAMES[selectedRound]}`}
            </Button>
            <span className="text-xs text-center" style={{ color: 'var(--text-tertiary)' }}>
              Talk naturally — the interviewer replies in real time. Allow your mic when asked.
              {' '}Finish all five to auto-generate your debrief, or end early any time.
            </span>
          </div>
        )}

        {phase === 'done' && (
          <div className="mt-6 flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <Sparkles className="h-4 w-4 text-primary" /> All rounds complete — preparing your debrief…
          </div>
        )}
      </div>

      {/* control bar while connected/connecting */}
      {(live || connecting || phase === 'finalizing') && (
        <div
          className="flex items-center justify-center gap-3 py-3 border-t"
          style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}
        >
          {connecting ? (
            <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
              Connecting…
            </span>
          ) : (
            <Button variant="danger" icon={PhoneOff} onClick={endRound} disabled={phase === 'finalizing'}>
              {phase === 'finalizing' ? 'Grading…' : 'End round'}
            </Button>
          )}
        </div>
      )}

      {localError && (
        <div className="flex items-start gap-2 p-3 text-sm text-danger" style={{ background: 'var(--bg-secondary)' }}>
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{localError}</span>
        </div>
      )}
    </div>
  )
}

/**
 * Live voice interview room — each round is a real-time ElevenLabs
 * conversational-agent call (ChatGPT-voice style). Rounds can be run in any
 * order (and re-run) via the picker; the backend grades each round's transcript
 * and auto-finishes once all five are done. Must be wrapped in a
 * ConversationProvider.
 */
export default function LiveInterviewRoom(props: Props) {
  return (
    <ConversationProvider>
      <LiveInterviewRoomInner {...props} />
    </ConversationProvider>
  )
}
