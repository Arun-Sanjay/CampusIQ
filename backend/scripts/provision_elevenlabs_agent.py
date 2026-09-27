#!/usr/bin/env python
"""Provision (create or update) the CampusIQ Mock Interviewer ElevenLabs agent.

The live voice interview reuses ONE ElevenLabs Conversational AI agent and
overrides its prompt / first message / voice per round at `startSession`. For
those client-side overrides to take effect, the agent must have them enabled in
its security/overrides allow-list — that's what this script sets up.

Idempotent: finds the agent by name and PATCHes it, or creates it if missing.
Low-latency knobs are baked in (Flash TTS). Run it once from the backend dir so
pydantic settings read `backend/.env`:

    cd backend
    .venv/bin/python scripts/provision_elevenlabs_agent.py            # create/update, print id
    .venv/bin/python scripts/provision_elevenlabs_agent.py --write-env  # also set ELEVENLABS_AGENT_ID in .env

Requires ELEVENLABS_API_KEY in backend/.env.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

# Make `app` importable when run as `scripts/...` from the backend dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.services import elevenlabs_agent  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("provision")

AGENT_NAME = "CampusIQ Mock Interviewer"

# Low-latency, conversational defaults. Per-round prompt/first_message/voice are
# overridden at runtime (see mock_interview._live_round_overrides), so these are
# just sane fallbacks for a direct dashboard test.
AGENT_LLM = "gemini-2.5-flash"          # ElevenLabs default; fast + cheap. Configurable.
TTS_MODEL = "eleven_flash_v2"            # lowest-latency English TTS (EL requires turbo/flash v2 for English agents)
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (round-1 default)

BASE_PROMPT = (
    "You are a professional mock interviewer for software-engineering candidates. "
    "Conduct a natural spoken interview: ask one question at a time, keep every "
    "reply to 1-3 short sentences, react briefly, and stay in character. Never "
    "mention scores or evaluation — grading happens separately."
)

CONVERSATION_CONFIG = {
    "agent": {
        "first_message": "Hi! Thanks for joining. Whenever you're ready, let's begin.",
        "language": "en",
        "prompt": {
            "prompt": BASE_PROMPT,
            "llm": AGENT_LLM,
            "temperature": 0.5,
        },
    },
    "tts": {
        "voice_id": DEFAULT_VOICE_ID,
        "model_id": TTS_MODEL,
    },
    "conversation": {
        "text_only": False,
        "max_duration_seconds": 600,
    },
}

# The allow-list that makes the client-side per-round overrides actually apply.
PLATFORM_SETTINGS = {
    "overrides": {
        "conversation_config_override": {
            "agent": {
                "prompt": {"prompt": True},
                "first_message": True,
                "language": True,
            },
            "tts": {"voice_id": True},
        }
    }
}


def _find_existing_agent_id() -> str | None:
    for agent in elevenlabs_agent.list_agents():
        if (agent.get("name") or "").strip() == AGENT_NAME:
            return agent.get("agent_id")
    return None


def _write_env_agent_id(agent_id: str) -> None:
    """Idempotently set ELEVENLABS_AGENT_ID in backend/.env."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    line = f"ELEVENLABS_AGENT_ID={agent_id}"
    if not env_path.exists():
        env_path.write_text(line + "\n")
        logger.info("Created %s with %s", env_path, line)
        return
    text = env_path.read_text()
    if re.search(r"^ELEVENLABS_AGENT_ID=", text, flags=re.MULTILINE):
        text = re.sub(r"^ELEVENLABS_AGENT_ID=.*$", line, text, flags=re.MULTILINE)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    env_path.write_text(text)
    logger.info("Updated %s → %s", env_path, line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision the CampusIQ interview agent")
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write ELEVENLABS_AGENT_ID into backend/.env after provisioning",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.elevenlabs_api_key:
        logger.error("ELEVENLABS_API_KEY is not set in backend/.env — aborting.")
        return 1

    existing = _find_existing_agent_id()
    if existing:
        logger.info("Found existing agent '%s' (%s) — updating config…", AGENT_NAME, existing)
        ok = elevenlabs_agent.update_agent(existing, CONVERSATION_CONFIG, PLATFORM_SETTINGS)
        if not ok:
            logger.error("Update failed (see error above).")
            return 1
        agent_id = existing
    else:
        logger.info("Creating agent '%s'…", AGENT_NAME)
        agent_id = elevenlabs_agent.create_agent(AGENT_NAME, CONVERSATION_CONFIG, PLATFORM_SETTINGS)
        if not agent_id:
            logger.error("Create failed (see error above).")
            return 1

    logger.info("\n✅ Agent ready.\n   agent_id = %s\n", agent_id)
    if args.write_env:
        _write_env_agent_id(agent_id)
    else:
        logger.info("Add this to backend/.env (and the prod env):\n   ELEVENLABS_AGENT_ID=%s", agent_id)
    logger.info(
        "\nProd: also set it on Cloud Run / your host, e.g.\n"
        "   ELEVENLABS_AGENT_ID=%s",
        agent_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
