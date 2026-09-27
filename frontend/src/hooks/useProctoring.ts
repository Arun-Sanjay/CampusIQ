/**
 * Proctoring hook: fullscreen enforcement, tab-switch/blur detection,
 * copy/paste/right-click/devtools blocking, a server-anchored hard countdown,
 * and a batched violation event sink. Integrity rests on the server (timer
 * anchor + single-attempt + availability), not these client locks.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { quizzesApi } from '../api/client'
import type { ProctorEventIn, ProctorSummary } from '../types'

export interface UseProctoringOptions {
  quizId: string
  startedAtIso: string
  serverNowIso: string
  timeLimitSeconds: number | null
  enabled: boolean
  maxViolations?: number
  onAutoSubmit: (reason: string) => void
  onWarn: (message: string) => void
}

function emptyCounters(): ProctorSummary {
  return {
    tab_switch_count: 0, fullscreen_exits: 0, copy_paste_attempts: 0,
    face_absent_seconds: 0, face_multiple_seconds: 0, auto_submitted: false,
  }
}

// Phones fire visibilitychange/blur constantly (notification shade, the
// keyboard, app switches) and reject fullscreen — so on touch devices we still
// RECORD every counter but never trip the auto-submit-on-violations path. The
// time-out auto-submit is unaffected.
const isTouch =
  typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches === true

export function useProctoring(opts: UseProctoringOptions) {
  const counters = useRef<ProctorSummary>(emptyCounters())
  const violations = useRef<Record<string, unknown>[]>([])
  const submitted = useRef(false)
  const [remaining, setRemaining] = useState<number | null>(null)

  const record = useCallback((ev: ProctorEventIn) => {
    violations.current.push({ type: ev.type, ts: Date.now(), ...(ev.detail || {}) })
    quizzesApi.recordProctorEvent(opts.quizId, ev).catch(() => {})
  }, [opts.quizId])

  const triggerAuto = useCallback((reason: string) => {
    if (submitted.current) return
    submitted.current = true
    counters.current.auto_submitted = true
    opts.onAutoSubmit(reason)
  }, [opts])

  // Hard countdown anchored to the SERVER's started_at (+ clock-skew correction).
  useEffect(() => {
    if (!opts.enabled || !opts.timeLimitSeconds) return
    const started = new Date(opts.startedAtIso).getTime()
    const serverNow = new Date(opts.serverNowIso).getTime()
    const skew = Date.now() - serverNow
    const endLocal = started + opts.timeLimitSeconds * 1000 + skew
    const tick = () => {
      const rem = Math.max(0, Math.round((endLocal - Date.now()) / 1000))
      setRemaining(rem)
      if (rem <= 0) triggerAuto('time')
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [opts.enabled, opts.startedAtIso, opts.serverNowIso, opts.timeLimitSeconds, triggerAuto])

  // Anti-cheat listeners.
  useEffect(() => {
    if (!opts.enabled) return
    const maxV = opts.maxViolations ?? 6
    const bumpSwitch = (type: 'tab_switch' | 'blur') => {
      counters.current.tab_switch_count += 1
      record({ type })
      opts.onWarn('⚠ Leaving the test window is recorded. Stay on this tab.')
      // Touch devices fire these spuriously — count but don't auto-submit.
      if (!isTouch && counters.current.tab_switch_count >= maxV) triggerAuto('violations')
    }
    const onVis = () => { if (document.hidden) bumpSwitch('tab_switch') }
    const onBlur = () => bumpSwitch('blur')
    const onFs = () => {
      if (!document.fullscreenElement) {
        counters.current.fullscreen_exits += 1
        record({ type: 'fullscreen_exit' })
        opts.onWarn('⚠ Please stay in fullscreen for the duration of the test.')
      }
    }
    const blocker = (type: ProctorEventIn['type']) => (e: Event) => {
      e.preventDefault()
      counters.current.copy_paste_attempts += 1
      record({ type })
    }
    const onCopy = blocker('copy')
    const onPaste = blocker('paste')
    const onCut = blocker('copy')
    const onCtx = blocker('contextmenu')
    const onKey = (e: KeyboardEvent) => {
      const k = e.key.toUpperCase()
      const meta = e.ctrlKey || e.metaKey
      if (e.key === 'F12' || (meta && e.shiftKey && ['I', 'J', 'C'].includes(k)) || (meta && k === 'P')) {
        e.preventDefault()
        counters.current.copy_paste_attempts += 1
        record({ type: 'devtools' })
      }
    }
    document.addEventListener('visibilitychange', onVis)
    window.addEventListener('blur', onBlur)
    document.addEventListener('fullscreenchange', onFs)
    document.addEventListener('copy', onCopy)
    document.addEventListener('paste', onPaste)
    document.addEventListener('cut', onCut)
    document.addEventListener('contextmenu', onCtx)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      window.removeEventListener('blur', onBlur)
      document.removeEventListener('fullscreenchange', onFs)
      document.removeEventListener('copy', onCopy)
      document.removeEventListener('paste', onPaste)
      document.removeEventListener('cut', onCut)
      document.removeEventListener('contextmenu', onCtx)
      document.removeEventListener('keydown', onKey)
    }
  }, [opts.enabled, opts.maxViolations, record, triggerAuto, opts])

  const enterFullscreen = useCallback(async () => {
    // Try the standard API first, then the webkit fallback (older Safari). iOS
    // rejects fullscreen on non-<video> elements — swallow the failure silently.
    const el = document.documentElement as HTMLElement & {
      webkitRequestFullscreen?: () => Promise<void> | void
    }
    try {
      await el.requestFullscreen?.()
    } catch {
      try { await el.webkitRequestFullscreen?.() } catch { /* iOS / user declined */ }
    }
  }, [])

  const teardown = useCallback(() => {
    try { if (document.fullscreenElement) void document.exitFullscreen() } catch { /* noop */ }
  }, [])

  // Accumulate face-absence locally (sent in the final summary) — avoids a
  // per-second network POST. Discrete events still log live via record().
  const addFaceSeconds = useCallback((kind: 'absent' | 'multiple', secs: number) => {
    if (kind === 'absent') counters.current.face_absent_seconds += secs
    else counters.current.face_multiple_seconds += secs
  }, [])

  const markSubmitted = useCallback(() => { submitted.current = true }, [])

  return { remaining, counters, violations, enterFullscreen, teardown, addFaceSeconds, markSubmitted }
}
