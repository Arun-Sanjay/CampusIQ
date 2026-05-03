"""WebSocket notifications endpoint (Phase 9)."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_user_id_from_token
from app.services import notifications

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/notifications")
async def notifications_ws(
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
    token: str = Query(..., description="JWT access token"),
) -> None:
    """Long-lived WebSocket that streams push notifications for the authed user.

    The browser passes the JWT as `?token=...` (it cannot set Authorization
    headers on a WS handshake). We close with 4401 if auth fails so the client
    can distinguish auth errors from network issues.
    """
    try:
        user_id = get_user_id_from_token(token)
    except InvalidTokenError:
        await websocket.close(code=4401)
        return

    from app.services.auth import get_user_by_id

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    await notifications.manager.add(user.id, websocket)

    # Send an initial hello so the client can confirm the channel is live.
    try:
        await websocket.send_json(
            {"type": "_connected", "user_id": str(user.id)}
        )
        while True:
            # Treat any client message as an ACK / keepalive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("notifications WS error for user %s", user.id)
    finally:
        await notifications.manager.remove(user.id, websocket)
