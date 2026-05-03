"""Real-time notifications (Phase 9).

A small WebSocket connection registry + a `publish` helper that other
endpoints can call after they've completed their work. Connections are
authenticated via a JWT passed as a `?token=` query parameter (browsers can't
add Authorization headers to WebSocket handshakes).

Persists every notification to `NotificationDelivery` so we keep history even
when the client isn't currently connected. The TCP-style `sequence_number`
column is incremented per-user.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.algorithm import (
    NotificationDelivery,
    NotificationStatus,
    NotificationType,
)

logger = logging.getLogger(__name__)


# Captured at app startup so sync DB-handler threads can still dispatch sends
# onto the loop that owns the live WebSocket objects.
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def get_main_loop() -> asyncio.AbstractEventLoop | None:
    return _main_loop


class _ConnectionManager:
    """Tracks open WebSocket connections, keyed by user_id."""

    def __init__(self) -> None:
        self._by_user: dict[uuid.UUID, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def add(self, user_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._by_user.setdefault(user_id, []).append(ws)

    async def remove(self, user_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            sockets = self._by_user.get(user_id)
            if not sockets:
                return
            try:
                sockets.remove(ws)
            except ValueError:
                pass
            if not sockets:
                self._by_user.pop(user_id, None)

    def connections_for(self, user_id: uuid.UUID) -> list[WebSocket]:
        return list(self._by_user.get(user_id, []))


manager = _ConnectionManager()


async def _send_payload(ws: WebSocket, payload: dict[str, Any]) -> bool:
    """Try to send a JSON payload. Returns True on success."""
    try:
        await ws.send_json(payload)
        return True
    except Exception:  # noqa: BLE001 — any send failure is non-fatal
        return False


def _next_sequence_number(db: Session, user_id: uuid.UUID) -> int:
    current_max = db.scalar(
        select(func.max(NotificationDelivery.sequence_number)).where(
            NotificationDelivery.user_id == user_id
        )
    )
    return int(current_max or 0) + 1


async def publish(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    content: str,
    extra: dict[str, Any] | None = None,
) -> NotificationDelivery:
    """Persist a notification + push it to any active WebSocket clients.

    The DB row is always written (so users see history when they reconnect).
    Live delivery is best-effort: if no socket is open or sending fails, the
    row is still saved as PENDING and a follow-up reconciliation job could
    retry it later.
    """
    seq = _next_sequence_number(db, user_id)
    row = NotificationDelivery(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        content=content,
        sequence_number=seq,
        status=NotificationStatus.PENDING,
    )
    db.add(row)
    db.flush()

    payload = {
        "id": str(row.id),
        "type": notification_type.value,
        "title": title,
        "content": content,
        "sequence_number": seq,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if extra:
        payload["extra"] = extra

    sockets = manager.connections_for(user_id)
    if sockets:
        # Fire all sends in parallel; mark sent if any succeed.
        results = await asyncio.gather(
            *[_send_payload(ws, payload) for ws in sockets], return_exceptions=False
        )
        if any(results):
            row.status = NotificationStatus.SENT
            row.last_sent_at = datetime.now(tz=timezone.utc)
    return row


async def _push_payload_to_user(user_id: uuid.UUID, payload: dict[str, Any]) -> bool:
    """Send the payload to every active socket for this user. Returns True if
    at least one send succeeded."""
    sockets = manager.connections_for(user_id)
    if not sockets:
        return False
    results = await asyncio.gather(
        *[_send_payload(ws, payload) for ws in sockets], return_exceptions=False
    )
    return any(results)


def publish_sync(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    content: str,
    extra: dict[str, Any] | None = None,
) -> NotificationDelivery:
    """Sync wrapper used from FastAPI sync route handlers.

    Always persists the row. WebSocket fan-out is dispatched onto the main
    event loop via `run_coroutine_threadsafe` so live sockets actually receive
    the message — they belong to that loop, not the calling worker thread.
    """
    seq = _next_sequence_number(db, user_id)
    row = NotificationDelivery(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        content=content,
        sequence_number=seq,
        status=NotificationStatus.PENDING,
    )
    db.add(row)
    db.flush()

    payload = {
        "id": str(row.id),
        "type": notification_type.value,
        "title": title,
        "content": content,
        "sequence_number": seq,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if extra:
        payload["extra"] = extra

    loop = _main_loop
    if loop is None:
        # No live loop captured — pure-DB persistence is the best we can do.
        return row

    try:
        future = asyncio.run_coroutine_threadsafe(
            _push_payload_to_user(user_id, payload), loop
        )
    except RuntimeError as exc:
        logger.warning("Could not schedule notification dispatch: %s", exc)
        return row

    # Block briefly to flip status when delivery succeeds. The 1s timeout
    # keeps the API responsive even if the loop is busy.
    try:
        delivered = future.result(timeout=1.0)
    except Exception:  # noqa: BLE001 — timeout / cancellation are fine
        delivered = False
    if delivered:
        row.status = NotificationStatus.SENT
        row.last_sent_at = datetime.now(tz=timezone.utc)
    return row
