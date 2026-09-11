"""
Server-side, DB-backed session middleware. Installed once in app/main.py
and used by every route.

Policy:
- httponly, SameSite=Lax cookie
- `secure` tied to APP_ENV=production, rather than a manually-set flag
  someone has to remember to flip
- 30-minute idle timeout -> regenerate the session id (data carried over)
- 1-hour hard lifetime
"""
from __future__ import annotations

import datetime
import json
import secrets
from typing import Any, MutableMapping

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.db.base import SessionLocal
from app.models.session_store import AppSession

COOKIE_NAME = "coffeetime_session"
IDLE_TIMEOUT = datetime.timedelta(minutes=30)
HARD_LIFETIME = datetime.timedelta(hours=1)


class SessionData(MutableMapping[str, Any]):
    """Dict-like wrapper so `request.state.session['cart']` etc. reads
    like a plain dict while tracking whether it needs to be persisted."""

    def __init__(self, initial: dict[str, Any]):
        self._data = dict(initial)
        self.dirty = False

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.dirty = True

    def __delitem__(self, key: str) -> None:
        del self._data[key]
        self.dirty = True

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def pop(self, key: str, default: Any = None) -> Any:
        self.dirty = True
        return self._data.pop(key, default)

    def to_json(self) -> str:
        return json.dumps(self._data, default=str)


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        now = datetime.datetime.utcnow()
        raw_id = request.cookies.get(COOKIE_NAME)
        session_id = raw_id
        data: dict[str, Any] = {}
        regenerate = False

        db = SessionLocal()
        try:
            row = db.get(AppSession, raw_id) if raw_id else None
            if row is None or row.expires_at < now:
                # No session, or past the 1h hard lifetime -> fresh session
                session_id = secrets.token_hex(32)
                data = {}
            elif (now - row.last_activity) > IDLE_TIMEOUT:
                # Idle too long -> regenerate id, keep data
                data = json.loads(row.data)
                db.delete(row)
                db.commit()
                session_id = secrets.token_hex(32)
                regenerate = True
            else:
                data = json.loads(row.data)

            session = SessionData(data)
            request.state.session = session

            response = await call_next(request)

            if session.dirty or regenerate or row is None:
                existing = db.get(AppSession, session_id)
                if existing is None:
                    existing = AppSession(session_id=session_id)
                    db.add(existing)
                existing.data = session.to_json()
                existing.last_activity = now
                existing.expires_at = now + HARD_LIFETIME
                db.commit()

            if session_id != raw_id:
                response.set_cookie(
                    COOKIE_NAME,
                    session_id,
                    httponly=True,
                    samesite="lax",
                    secure=settings.is_production,
                    path="/",
                )
            return response
        finally:
            db.close()
