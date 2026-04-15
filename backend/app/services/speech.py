"""Speech pipeline for Phase 20 — Whisper ASR + ElevenLabs TTS.

Both sides are lazy-cached so missing keys don't crash the app at import time.
Every function returns a non-raising sentinel (empty string / None) and logs
the root cause so the calling service can decide whether to fall back.

Why two vendors?
----------------
- OpenAI Whisper (`whisper-1`) is the cheapest, most accurate multilingual
  transcription available via API — ~$0.006/min. The mock-interview and
  confidence-coach flows both use it, so it lives here once.
- ElevenLabs is the demo showstopper: 5 distinct human voices map to the 5
  interview rounds so the candidate experiences a different interviewer voice
  at each stage. We're on the starter plan (~10k chars/mo) so every TTS call
  is metered and rate-limited — see `is_tts_available()` / cost guard below.

Audio files are written to `backend/uploads/audio/` and served by FastAPI's
`StaticFiles` mount (added in `main.py`). We keep the returned URL relative
so the frontend can prepend the API base URL without knowing about the mount.

Format notes
------------
- Whisper accepts webm/wav/mp3/m4a/ogg/flac — the browser's MediaRecorder
  defaults to `audio/webm;codecs=opus` which is perfect.
- ElevenLabs output is MP3 (`mp3_44100_128`) by default. We keep that.
"""
from __future__ import annotations

import io
import logging
import uuid
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# File storage
# ════════════════════════════════════════════════════════════════

# Audio files land in backend/uploads/audio/ (relative to the backend cwd).
# The uploads/ folder already exists; we add an `audio/` subdir.
AUDIO_DIR = Path("uploads") / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Public URL prefix — matches the StaticFiles mount in main.py.
AUDIO_URL_PREFIX = "/audio"


def save_audio_bytes(data: bytes, *, extension: str = "mp3") -> tuple[Path, str]:
    """Persist a blob of audio bytes under a UUID filename.

    Returns the on-disk Path and the public URL path (without host). Callers
    usually return the URL path to the client and keep the Path for cleanup.
    """
    if not extension.startswith("."):
        extension = "." + extension
    file_id = uuid.uuid4().hex
    file_path = AUDIO_DIR / f"{file_id}{extension}"
    file_path.write_bytes(data)
    return file_path, f"{AUDIO_URL_PREFIX}/{file_path.name}"


# ════════════════════════════════════════════════════════════════
# OpenAI Whisper (ASR)
# ════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def _get_openai_client():
    """Return a cached OpenAI client, or None if the key isn't set."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError as e:
        logger.warning("openai package not installed: %s", e)
        return None
    try:
        return OpenAI(api_key=settings.openai_api_key)
    except Exception as e:
        logger.exception("Failed to construct OpenAI client: %s", e)
        return None


def is_asr_available() -> bool:
    """True if Whisper transcription can be performed."""
    return _get_openai_client() is not None


def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename: str = "audio.webm",
    language: str | None = "en",
) -> str:
    """Transcribe a chunk of audio using Whisper. Returns plain text.

    Never raises — returns "" and logs on failure so the caller can decide
    whether the empty transcript is recoverable.
    """
    client = _get_openai_client()
    if client is None:
        logger.warning("Whisper transcription skipped: OPENAI_API_KEY missing")
        return ""
    if not audio_bytes:
        return ""

    # The OpenAI SDK accepts a (name, bytes, mime) tuple for streaming uploads.
    buffer = io.BytesIO(audio_bytes)
    buffer.name = filename  # the SDK uses `name` to sniff the mime type
    try:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=buffer,
            language=language or None,
            response_format="text",
        )
    except Exception as e:
        logger.exception("Whisper transcription failed: %s", e)
        return ""

    # The SDK returns a plain string when response_format="text", but some
    # versions wrap it in an object with a .text attribute — handle both.
    if isinstance(result, str):
        return result.strip()
    text = getattr(result, "text", None)
    return text.strip() if isinstance(text, str) else ""


# ════════════════════════════════════════════════════════════════
# ElevenLabs TTS
# ════════════════════════════════════════════════════════════════

# Interview round → ElevenLabs voice mapping.
#
# These are the default voices that ship with every ElevenLabs account, so
# any working API key will be able to hit them. The mapping is intentional:
#
#   Round 1 — HR / Behavioural     → Rachel (warm, calm, friendly)
#   Round 2 — Technical            → Adam (deep, male, focused)
#   Round 3 — System Design        → Antoni (articulate male, presenter tone)
#   Round 4 — Managerial           → Domi (authoritative female)
#   Round 5 — Negotiation          → Josh (assertive male)
#
# Each voice ID is a public default voice. If a user customises their
# ElevenLabs library they can override via env later.
VOICE_BY_ROUND: dict[int, str] = {
    1: "21m00Tcm4TlvDq8ikWAM",  # Rachel
    2: "pNInz6obpgDQGcFmaJgB",  # Adam
    3: "ErXwobaYiN019PkySvjV",  # Antoni
    4: "AZnzlk1XvdvUeBnXmlld",  # Domi
    5: "TxGEqnHWrfWFTfGW9XjX",  # Josh
}

DEFAULT_VOICE_ID = VOICE_BY_ROUND[1]


@lru_cache(maxsize=1)
def _get_elevenlabs_client():
    """Return a cached ElevenLabs client, or None if the key isn't set."""
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        return None
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as e:
        logger.warning("elevenlabs package not installed: %s", e)
        return None
    try:
        return ElevenLabs(api_key=settings.elevenlabs_api_key)
    except Exception as e:
        logger.exception("Failed to construct ElevenLabs client: %s", e)
        return None


def is_tts_available() -> bool:
    """True if ElevenLabs text-to-speech can be performed."""
    return _get_elevenlabs_client() is not None


# Starter-plan guard — don't TTS prompts longer than this. Keeps us from
# eating the monthly character quota on one long interview.
MAX_TTS_CHARS = 900


def synthesize_speech(
    text: str,
    *,
    voice_id: str | None = None,
    round_number: int | None = None,
) -> tuple[bytes, str] | None:
    """Generate an MP3 of the given text.

    Either pass a raw `voice_id` or a `round_number` (1-5). If neither is
    given, the round-1 Rachel voice is used. Returns (audio_bytes, voice_id)
    on success or None on failure / missing key.
    """
    client = _get_elevenlabs_client()
    if client is None:
        logger.info("ElevenLabs skipped: ELEVENLABS_API_KEY missing")
        return None

    clean_text = (text or "").strip()
    if not clean_text:
        return None
    if len(clean_text) > MAX_TTS_CHARS:
        # Truncate but keep whole sentences where possible
        cut = clean_text[:MAX_TTS_CHARS]
        last_stop = max(cut.rfind("."), cut.rfind("?"), cut.rfind("!"))
        if last_stop > 200:
            cut = cut[: last_stop + 1]
        clean_text = cut
        logger.info("Truncated TTS prompt to %d chars", len(clean_text))

    # Resolve the voice ID
    if voice_id is None and round_number is not None:
        voice_id = VOICE_BY_ROUND.get(round_number, DEFAULT_VOICE_ID)
    elif voice_id is None:
        voice_id = DEFAULT_VOICE_ID

    try:
        # ElevenLabs v2 SDK returns an iterator of audio chunks when you
        # call text_to_speech.convert(). We join them into a single bytes blob.
        audio_iter = client.text_to_speech.convert(
            voice_id=voice_id,
            text=clean_text,
            model_id="eleven_turbo_v2_5",  # cheapest fast model — 32k char/month on starter
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(chunk for chunk in audio_iter if chunk)
    except Exception as e:
        logger.exception("ElevenLabs TTS failed: %s", e)
        return None

    return audio_bytes, voice_id


def synthesize_and_save(
    text: str,
    *,
    voice_id: str | None = None,
    round_number: int | None = None,
) -> tuple[str, str] | None:
    """Generate TTS and persist it under uploads/audio/.

    Returns (public_url, voice_id) on success, None on failure.
    """
    result = synthesize_speech(text, voice_id=voice_id, round_number=round_number)
    if result is None:
        return None
    audio_bytes, used_voice = result
    _, public_url = save_audio_bytes(audio_bytes, extension="mp3")
    return public_url, used_voice
