"""Shared Claude (Anthropic) API wrapper.

Reused across phases: document summaries (P7), quiz generation (P11),
RAG chat (P9), mock interviews (P16), etc.

Cost management rule (from the project skill):
    - ALL dev/testing uses claude-haiku-4-5-20251001
    - Only the final demo flips USE_PRODUCTION_MODEL=true to Opus
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from functools import lru_cache

import anthropic

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> anthropic.Anthropic | None:
    """Return a cached Anthropic client, or None if the key isn't set."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def is_available() -> bool:
    """Whether Claude API calls can succeed (i.e. the key is configured)."""
    return _get_client() is not None


def generate_completion(
    system: str,
    user_message: str,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    """Run a single-turn completion. Returns the text content, or "" on failure.

    Errors are logged but never raised — the caller decides whether missing
    output is fatal (e.g. summary generation is best-effort).
    """
    client = _get_client()
    if client is None:
        logger.info("Claude client not configured — skipping completion")
        return ""

    settings = get_settings()
    model = settings.active_anthropic_model  # haiku for dev, opus for demo

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as e:
        logger.exception("Claude API error: %s", e)
        return ""
    except Exception as e:
        logger.exception("Unexpected Claude error: %s", e)
        return ""

    # Pull the first text block
    if not response.content:
        return ""
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts).strip()


def generate_completion_multiturn(
    system: str,
    messages: list[dict],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    """Multi-turn blocking completion. Takes a full conversation history in
    Claude's chat format (alternating user/assistant turns). Returns the
    assistant's next message text, or "" on failure.

    Use this when you need Claude to remember previous turns but don't care
    about streaming — e.g. the Resume Coach, which needs conversation memory
    to avoid asking the same questions twice.
    """
    client = _get_client()
    if client is None:
        logger.info("Claude client not configured — skipping multiturn completion")
        return ""

    if not messages:
        return ""

    settings = get_settings()
    model = settings.active_anthropic_model

    # Claude requires alternating user/assistant, starting with user
    cleaned: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not content:
            continue
        cleaned.append({"role": role, "content": content})
    if not cleaned or cleaned[0]["role"] != "user":
        return ""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=cleaned,
        )
    except anthropic.APIError as e:
        logger.exception("Claude multiturn API error: %s", e)
        return ""
    except Exception as e:
        logger.exception("Unexpected Claude multiturn error: %s", e)
        return ""

    if not response.content:
        return ""
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts).strip()


def stream_completion(
    system: str,
    messages: list[dict],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.4,
) -> Iterator[str]:
    """Stream Claude's response as text deltas.

    `messages` is a list of {role, content} dicts in Claude's chat format.
    Yields plain string chunks suitable for SSE / chunked HTTP.

    If the API key is missing or an error occurs, yields a single fallback
    string explaining the situation — never raises.
    """
    client = _get_client()
    if client is None:
        yield "[AI is not configured. Set ANTHROPIC_API_KEY in backend/.env to enable streaming responses.]"
        return

    settings = get_settings()
    model = settings.active_anthropic_model

    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                if text:
                    yield text
    except anthropic.APIError as e:
        logger.exception("Claude streaming error: %s", e)
        yield f"\n\n[An error occurred while talking to the AI: {e}]"
    except Exception as e:
        logger.exception("Unexpected Claude streaming error: %s", e)
        yield f"\n\n[Unexpected error: {e}]"


# ═══════════════════════════════════════════════════════════════
# Document summary helper (Phase 7)
# ═══════════════════════════════════════════════════════════════

SUMMARY_SYSTEM_PROMPT = """You are a helpful teaching assistant for engineering students.
When given the text of a course document, produce a concise summary suitable for
students reviewing before an exam. Follow these rules:
- 3-5 short paragraphs
- Plain prose, no markdown headers or lists
- Focus on the key concepts, definitions, and anything a student should remember
- Use simple language, avoid jargon when possible
- Do NOT start with phrases like "This document discusses..." — dive straight in"""


def summarize_document(text: str, max_input_chars: int = 12_000) -> str:
    """Generate a short summary of a document's text content.

    Truncates to `max_input_chars` to keep cost bounded. Returns empty string
    if the API key is not set or if the call fails.
    """
    if not text.strip():
        return ""

    truncated = text if len(text) <= max_input_chars else text[:max_input_chars]
    user_message = (
        f"Here is the content of a course document. Write a summary for students.\n\n"
        f"---\n{truncated}\n---"
    )
    return generate_completion(
        system=SUMMARY_SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=800,
        temperature=0.4,
    )
