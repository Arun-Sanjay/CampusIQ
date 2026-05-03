/**
 * Computes eye-contact and posture scores from a live MediaStream using
 * MediaPipe Tasks Vision. Lazy-loads the WASM bundles and model files from
 * jsdelivr/Google CDN so we don't bloat the main JS bundle.
 *
 * Phase 5 of the punch list — replaces the hardcoded eye_contact / posture
 * placeholders that the Confidence Coach page was sending to the backend.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  FaceLandmarker,
  FilesetResolver,
  PoseLandmarker,
  type FaceLandmarkerResult,
  type PoseLandmarkerResult,
} from '@mediapipe/tasks-vision'

const WASM_BASE_URL =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm'
const FACE_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
const POSE_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'

const SAMPLE_INTERVAL_MS = 200 // 5 samples/sec — plenty for confidence scoring
const MAX_SAMPLES = 600 // safety cap (~2 minutes at 5fps)

export interface ConfidenceTrackerSamples {
  avgEyeContact: number | null
  avgPosture: number | null
  liveEyeContact: number | null
  livePosture: number | null
  sampleCount: number
}

export interface UseConfidenceTrackerResult extends ConfidenceTrackerSamples {
  /**
   * Start sampling against the given MediaStream. The stream must have a video
   * track. Resolves once the first frame has been processed (or sooner if the
   * model fails to load — in which case fallback metrics will be reported).
   */
  start: (stream: MediaStream) => Promise<void>
  /**
   * Stop sampling. Returns the final aggregated metrics.
   */
  stop: () => ConfidenceTrackerSamples
  /** True while a sampling loop is running. */
  running: boolean
  /** Last error from model load / inference. Null if everything is fine. */
  error: string | null
  /**
   * `false` if MediaPipe was unable to load (e.g. offline, unsupported browser).
   * The page should fall back to a neutral baseline when this is the case.
   */
  available: boolean
}

let cachedFaceLandmarker: Promise<FaceLandmarker> | null = null
let cachedPoseLandmarker: Promise<PoseLandmarker> | null = null

function loadFaceLandmarker(): Promise<FaceLandmarker> {
  if (!cachedFaceLandmarker) {
    cachedFaceLandmarker = (async () => {
      const fileset = await FilesetResolver.forVisionTasks(WASM_BASE_URL)
      return await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: FACE_MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numFaces: 1,
        outputFaceBlendshapes: false,
        outputFacialTransformationMatrixes: false,
      })
    })().catch((err) => {
      cachedFaceLandmarker = null
      throw err
    })
  }
  return cachedFaceLandmarker
}

function loadPoseLandmarker(): Promise<PoseLandmarker> {
  if (!cachedPoseLandmarker) {
    cachedPoseLandmarker = (async () => {
      const fileset = await FilesetResolver.forVisionTasks(WASM_BASE_URL)
      return await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: POSE_MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numPoses: 1,
      })
    })().catch((err) => {
      cachedPoseLandmarker = null
      throw err
    })
  }
  return cachedPoseLandmarker
}

/**
 * Eye contact score: combines (1) head centeredness in frame and (2) how aligned
 * the nose tip is with the midpoint between the eyes (a proxy for "facing the
 * camera straight on" vs profile turn). Returns 0–100 or null if no face.
 */
function computeEyeContact(result: FaceLandmarkerResult): number | null {
  const faces = result.faceLandmarks
  if (!faces || faces.length === 0) return null
  const lm = faces[0]
  // Landmark indices from MediaPipe FaceLandmarker.
  const noseTip = lm[4]
  const rightEyeOuter = lm[33]
  const leftEyeOuter = lm[263]
  if (!noseTip || !rightEyeOuter || !leftEyeOuter) return null

  const eyeMidX = (rightEyeOuter.x + leftEyeOuter.x) / 2
  const facingOffset = Math.abs(noseTip.x - eyeMidX) // 0 = perfectly facing camera
  const centerness = 1 - Math.min(1, Math.abs(noseTip.x - 0.5) * 2) // 1 = nose at frame x-center

  // facingOffset of ~0.04 still reads as fully facing camera; >0.12 is clearly turned.
  const facingScore = Math.max(0, 1 - facingOffset * 9)
  const score = Math.round((centerness * 0.45 + facingScore * 0.55) * 100)
  return Math.max(0, Math.min(100, score))
}

/**
 * Posture score: combines (1) shoulder tilt (level shoulders score high) and
 * (2) head-over-shoulders alignment (nose horizontally near the shoulder
 * midpoint). Returns 0–100 or null if no pose.
 */
function computePosture(result: PoseLandmarkerResult): number | null {
  const poses = result.landmarks
  if (!poses || poses.length === 0) return null
  const lm = poses[0]
  const leftShoulder = lm[11]
  const rightShoulder = lm[12]
  const nose = lm[0]
  if (!leftShoulder || !rightShoulder || !nose) return null

  const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y) // 0 = level
  const shoulderMidX = (leftShoulder.x + rightShoulder.x) / 2
  const headOver = Math.abs(nose.x - shoulderMidX) // 0 = head squarely above shoulders

  const tiltScore = Math.max(0, 1 - shoulderTilt * 12) // tilt > 0.083 → 0
  const overScore = Math.max(0, 1 - headOver * 6) // offset > 0.166 → 0
  const score = Math.round((tiltScore * 0.55 + overScore * 0.45) * 100)
  return Math.max(0, Math.min(100, score))
}

export function useConfidenceTracker(): UseConfidenceTrackerResult {
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [available, setAvailable] = useState(true)
  const [liveEyeContact, setLiveEyeContact] = useState<number | null>(null)
  const [livePosture, setLivePosture] = useState<number | null>(null)
  const [sampleCount, setSampleCount] = useState(0)

  const samplesRef = useRef<{ eye: number; posture: number }[]>([])
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const intervalRef = useRef<number | null>(null)
  const cancelledRef = useRef(false)

  const aggregate = useCallback((): ConfidenceTrackerSamples => {
    const arr = samplesRef.current
    if (arr.length === 0) {
      return {
        avgEyeContact: null,
        avgPosture: null,
        liveEyeContact: null,
        livePosture: null,
        sampleCount: 0,
      }
    }
    const sumE = arr.reduce((a, b) => a + b.eye, 0)
    const sumP = arr.reduce((a, b) => a + b.posture, 0)
    return {
      avgEyeContact: Math.round(sumE / arr.length),
      avgPosture: Math.round(sumP / arr.length),
      liveEyeContact: arr[arr.length - 1]!.eye,
      livePosture: arr[arr.length - 1]!.posture,
      sampleCount: arr.length,
    }
  }, [])

  const cleanup = useCallback(() => {
    if (intervalRef.current != null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    const v = videoRef.current
    if (v) {
      try {
        v.pause()
      } catch {
        /* ignore */
      }
      v.srcObject = null
      videoRef.current = null
    }
  }, [])

  const start = useCallback(
    async (stream: MediaStream): Promise<void> => {
      cancelledRef.current = false
      setError(null)
      samplesRef.current = []
      setLiveEyeContact(null)
      setLivePosture(null)
      setSampleCount(0)
      setRunning(true)

      // Set up an offscreen video element bound to the same stream so we
      // don't fight the Confidence Coach's visible <video> element.
      const video = document.createElement('video')
      video.srcObject = stream
      video.muted = true
      video.playsInline = true
      videoRef.current = video

      try {
        await video.play()
      } catch (playErr) {
        // Autoplay was blocked. We can still keep going; detection will just
        // start once the user manually triggers anything.
        const msg =
          playErr instanceof Error ? playErr.message : 'Could not start video preview'
        setError(msg)
      }

      let face: FaceLandmarker
      let pose: PoseLandmarker
      try {
        ;[face, pose] = await Promise.all([loadFaceLandmarker(), loadPoseLandmarker()])
      } catch (loadErr) {
        const msg =
          loadErr instanceof Error
            ? loadErr.message
            : 'Could not load body / face tracking models'
        setError(msg)
        setAvailable(false)
        setRunning(false)
        cleanup()
        return
      }

      if (cancelledRef.current) {
        cleanup()
        return
      }

      intervalRef.current = window.setInterval(() => {
        const v = videoRef.current
        if (!v || v.readyState < 2 || v.videoWidth === 0) return
        const ts = performance.now()
        try {
          const faceResult = face.detectForVideo(v, ts)
          const poseResult = pose.detectForVideo(v, ts)
          const eye = computeEyeContact(faceResult)
          const posture = computePosture(poseResult)
          if (eye != null && posture != null) {
            const arr = samplesRef.current
            if (arr.length < MAX_SAMPLES) {
              arr.push({ eye, posture })
              setLiveEyeContact(eye)
              setLivePosture(posture)
              setSampleCount(arr.length)
            }
          }
        } catch {
          // A single frame failure shouldn't halt the loop.
        }
      }, SAMPLE_INTERVAL_MS)
    },
    [cleanup],
  )

  const stop = useCallback((): ConfidenceTrackerSamples => {
    cancelledRef.current = true
    cleanup()
    setRunning(false)
    return aggregate()
  }, [aggregate, cleanup])

  // Defensive cleanup on unmount.
  useEffect(() => {
    return () => {
      cancelledRef.current = true
      cleanup()
    }
  }, [cleanup])

  return {
    start,
    stop,
    running,
    error,
    available,
    avgEyeContact: liveEyeContact, // mirror live as "current avg" hint while running
    avgPosture: livePosture,
    liveEyeContact,
    livePosture,
    sampleCount,
  }
}
