"""Confidence Coach analysis pipeline (Phase 20, F11).

Given an audio recording + client-side MediaPipe scores, produce:

1. **Transcript**     — Whisper ASR (`services/speech.transcribe_audio`)
2. **Filler count**   — bag-of-words regex match (um/uh/like/you know/so/…)
3. **Speaking pace**  — `word_count / duration_seconds * 60`
4. **Clarity score**  — Claude rates transcript structure 0-100 via JSON protocol
5. **Overall score**  — weighted blend:
        0.25 eye_contact + 0.25 posture + 0.20 clarity
      + 0.15 pace_penalty + 0.15 filler_penalty
   where penalty terms are 100 minus deviations from target ranges.

Everything is best-effort — a missing API key or empty transcript degrades
the metric to None rather than crashing. The frontend handles "—" display
for None metrics.

Why the weights?
----------------
Eye-contact and posture carry the most weight because they're the hardest
things to fake and the easiest for interviewers to spot. Filler-word count
matters but less than body language. Clarity is the LLM's subjective take
on the answer's structure, so we let the deterministic metrics dominate.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.services import claude_client

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Filler-word detection — DMS Unit III: regex as a formal language
# ════════════════════════════════════════════════════════════════

# Patterns matched case-insensitively, as whole words with word boundaries.
# "you know" and "i mean" are multi-word so we handle them with spaces
# rather than \b. Order matters only for de-dup; we just sum counts.
FILLER_PATTERNS: list[str] = [
    r"\bum+\b",
    r"\buh+\b",
    r"\ber+\b",
    r"\bah+\b",
    r"\blike\b",
    r"\bso\b",
    r"\bactually\b",
    r"\bbasically\b",
    r"\bliterally\b",
    r"\bright\b",
    r"\bokay\b",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\byou know\b",
    r"\bi mean\b",
]

_FILLER_RE = re.compile("|".join(FILLER_PATTERNS), re.IGNORECASE)


def count_filler_words(text: str) -> int:
    """Return the number of filler-word hits in a transcript."""
    if not text:
        return 0
    return len(_FILLER_RE.findall(text))


def count_words(text: str) -> int:
    """Return a rough word count (whitespace split, filtering empties)."""
    if not text:
        return 0
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def speaking_pace_wpm(text: str, duration_seconds: int) -> int | None:
    """Words per minute. Returns None if duration is too short for a real read."""
    if duration_seconds <= 0:
        return None
    words = count_words(text)
    if words == 0:
        return 0
    return round(words / (duration_seconds / 60.0))


# ════════════════════════════════════════════════════════════════
# Scoring helpers
# ════════════════════════════════════════════════════════════════

# Target pace is 125-170 WPM (natural interview tempo).
# Outside that band we dock linearly, hitting 0 at ±80 WPM off-target.
PACE_TARGET_MIN = 125
PACE_TARGET_MAX = 170
PACE_FALLOFF = 80.0


def pace_score(wpm: int | None) -> float | None:
    """Return 0-100 pace score, or None if WPM isn't known."""
    if wpm is None:
        return None
    if PACE_TARGET_MIN <= wpm <= PACE_TARGET_MAX:
        return 100.0
    # How far below / above the target band are we?
    deviation = (
        PACE_TARGET_MIN - wpm if wpm < PACE_TARGET_MIN else wpm - PACE_TARGET_MAX
    )
    pct_off = min(1.0, deviation / PACE_FALLOFF)
    return round(100.0 * (1.0 - pct_off), 2)


def filler_score(filler_count: int, word_count: int) -> float:
    """Filler-density score on 0-100.

    0 fillers → 100. Then each filler per 50 words drops the score by 10.
    Capped at 0 so very rambly responses still return something.
    """
    if word_count <= 0:
        return 0.0 if filler_count > 0 else 100.0
    density = filler_count / max(word_count, 1) * 50.0  # fillers per 50 words
    return max(0.0, round(100.0 - density * 10.0, 2))


# ════════════════════════════════════════════════════════════════
# Claude clarity scoring
# ════════════════════════════════════════════════════════════════

CLARITY_SYSTEM = """You are an interview coach. A student recorded a spoken
answer to an interview question. You will be given the prompt (question) and
the transcript (their answer). Evaluate the answer's CLARITY on a 0-100 scale.

Consider:
- Structure — is it a clear beginning/middle/end? STAR-style for behavioural?
- Specificity — are there concrete examples vs. vague generalities?
- Confidence — does the wording sound assertive or hedge-heavy?
- Length — is it appropriate (1-3 paragraphs), not rambling or too terse?

Respond with VALID JSON ONLY (no markdown fences):
{
  "clarity_score": <number 0-100>,
  "headline": "<1-sentence summary of how clear the answer was>",
  "strengths": [<up to 2 short strings>],
  "improvements": [<up to 2 short actionable strings>],
  "recommended_drill": "<name of one drill from: Power Pause | STAR Framework | Confidence Cadence | Mirror Eye Contact>"
}

If the transcript is empty or only a few words, return clarity_score: 0 and
advise the candidate to record a longer response.
"""


@dataclass
class ClarityResult:
    score: float | None
    headline: str
    strengths: list[str]
    improvements: list[str]
    recommended_drill: str


def analyse_clarity(prompt: str, transcript: str) -> ClarityResult:
    """Call Claude Haiku to grade the answer's clarity.

    Falls back to a deterministic skeleton if the API is unavailable or
    returns malformed JSON — we never raise here because the overall score
    still needs to be computed from the other metrics.
    """
    if not claude_client.is_available() or not transcript.strip():
        return _fallback_clarity(transcript)

    user_message = (
        f"Interview prompt: {prompt}\n\n"
        f"Candidate's transcript (spoken answer):\n\"\"\"\n{transcript.strip()}\n\"\"\""
    )

    raw = claude_client.generate_completion(
        system=CLARITY_SYSTEM,
        user_message=user_message,
        max_tokens=600,
        temperature=0.3,
    )
    if not raw:
        return _fallback_clarity(transcript)

    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        data: dict[str, Any] = json.loads(cleaned[cleaned.find("{") :])
    except (ValueError, json.JSONDecodeError):
        logger.warning("Could not parse clarity JSON from Claude: %s", raw[:200])
        return _fallback_clarity(transcript)

    score_val: float | None
    try:
        raw_score = data.get("clarity_score")
        score_val = (
            max(0.0, min(100.0, float(raw_score))) if raw_score is not None else None
        )
    except (TypeError, ValueError):
        score_val = None

    return ClarityResult(
        score=score_val,
        headline=str(data.get("headline") or "").strip() or "Clarity scored.",
        strengths=[str(s) for s in (data.get("strengths") or [])][:2],
        improvements=[str(s) for s in (data.get("improvements") or [])][:2],
        recommended_drill=str(data.get("recommended_drill") or "STAR Framework"),
    )


def _fallback_clarity(transcript: str) -> ClarityResult:
    """When Claude is unavailable, give a conservative clarity score based
    purely on transcript length so the overall score is still computable."""
    words = count_words(transcript)
    if words < 15:
        score: float | None = 20.0
        headline = "Too short to evaluate — try answering for at least 20-30 seconds."
    elif words < 50:
        score = 55.0
        headline = "Reasonable length, but add a specific example or result."
    else:
        score = 70.0
        headline = "Good length. Focus on a crisper structure next time."
    return ClarityResult(
        score=score,
        headline=headline,
        strengths=["Completed the recording with meaningful content."] if words >= 15 else [],
        improvements=["Use the STAR framework: Situation, Task, Action, Result."],
        recommended_drill="STAR Framework",
    )


# ════════════════════════════════════════════════════════════════
# Overall composite score
# ════════════════════════════════════════════════════════════════

# Weights must sum to 1.0. See module docstring for rationale.
WEIGHTS: dict[str, float] = {
    "eye_contact": 0.25,
    "posture": 0.25,
    "clarity": 0.20,
    "pace": 0.15,
    "filler": 0.15,
}


@dataclass
class AnalysisResult:
    transcript: str
    filler_word_count: int
    word_count: int
    speaking_pace_wpm: int | None
    pace_score: float | None
    filler_score: float
    clarity: ClarityResult
    overall_score: float | None
    # Full structured feedback persisted as JSON for the timeline
    detailed_feedback: dict[str, Any]


def analyse_recording(
    *,
    audio_bytes: bytes,
    prompt: str,
    duration_seconds: int,
    eye_contact_pct: float | None,
    posture_pct: float | None,
    transcript_override: str | None = None,
) -> AnalysisResult:
    """End-to-end analysis of a recorded answer.

    Transcribes the audio via Whisper (falling back to empty string if the
    key isn't set), then computes filler count, pace, clarity, and an
    overall weighted score.

    `transcript_override` lets the frontend supply a browser-generated
    transcript (Web Speech API) when OPENAI_API_KEY isn't configured.
    This is the recommended path for dev: it costs nothing, works instantly,
    and keeps the ElevenLabs monthly quota saved for the live demo.
    """
    from app.services import speech

    if transcript_override and transcript_override.strip():
        transcript = transcript_override.strip()
    else:
        transcript = speech.transcribe_audio(audio_bytes, filename="confidence.webm")
    filler = count_filler_words(transcript)
    words = count_words(transcript)
    wpm = speaking_pace_wpm(transcript, duration_seconds)
    pace = pace_score(wpm)
    filler_sc = filler_score(filler, words)
    clarity = analyse_clarity(prompt, transcript)

    overall = _weighted_overall(
        eye_contact=eye_contact_pct,
        posture=posture_pct,
        clarity=clarity.score,
        pace=pace,
        filler=filler_sc,
    )

    detailed: dict[str, Any] = {
        "headline": clarity.headline,
        "strengths": clarity.strengths,
        "improvements": clarity.improvements,
        "recommended_drill": clarity.recommended_drill,
        "metrics": {
            "word_count": words,
            "duration_seconds": duration_seconds,
            "filler_score": filler_sc,
            "pace_score": pace,
            "clarity_score": clarity.score,
            "eye_contact_input": eye_contact_pct,
            "posture_input": posture_pct,
        },
    }

    return AnalysisResult(
        transcript=transcript,
        filler_word_count=filler,
        word_count=words,
        speaking_pace_wpm=wpm,
        pace_score=pace,
        filler_score=filler_sc,
        clarity=clarity,
        overall_score=overall,
        detailed_feedback=detailed,
    )


def _weighted_overall(
    *,
    eye_contact: float | None,
    posture: float | None,
    clarity: float | None,
    pace: float | None,
    filler: float,
) -> float | None:
    """Weighted blend — drops any None metrics and re-normalises the weights
    so a missing metric doesn't drag the overall score to 0."""
    components: list[tuple[float, float]] = []
    if eye_contact is not None:
        components.append((float(eye_contact), WEIGHTS["eye_contact"]))
    if posture is not None:
        components.append((float(posture), WEIGHTS["posture"]))
    if clarity is not None:
        components.append((float(clarity), WEIGHTS["clarity"]))
    if pace is not None:
        components.append((float(pace), WEIGHTS["pace"]))
    components.append((float(filler), WEIGHTS["filler"]))  # filler always computable

    total_weight = sum(w for _, w in components)
    if total_weight <= 0:
        return None
    weighted = sum(v * w for v, w in components) / total_weight
    return round(max(0.0, min(100.0, weighted)), 2)
