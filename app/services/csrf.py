"""
CSRF token generation and verification.

`verify_csrf` raises `CSRFError` on failure rather than building a
response itself, since a FastAPI dependency can't "exit early" with a
custom response; app.main installs an exception handler
(csrf_error_handler) that returns a JSON 403 for AJAX requests or a
flash + redirect otherwise.
"""
from __future__ import annotations

import hmac
import secrets

from starlette.requests import Request

from app.middleware.session import SessionData

CSRF_SESSION_KEY = "csrf_token"


class CSRFError(Exception):
    def __init__(self, message: str, *, session_expired: bool = False):
        self.message = message
        self.session_expired = session_expired
        super().__init__(message)


def csrf_token(session: SessionData) -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_field(session: SessionData) -> str:
    token = csrf_token(session)
    return f'<input type="hidden" name="csrf_token" value="{token}">'


def is_ajax(request: Request) -> bool:
    return request.headers.get("x-requested-with", "").lower() == "xmlhttprequest"


async def verify_csrf(request: Request) -> None:
    """Raise CSRFError on failure; call explicitly (as a FastAPI
    dependency) on every state-mutating route."""
    if request.method != "POST":
        return

    session: SessionData = request.state.session
    expected = session.get(CSRF_SESSION_KEY, "")

    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
        submitted = body.get("csrf_token", "")
    else:
        form = await request.form()
        submitted = form.get("csrf_token") or request.headers.get("x-csrf-token", "")

    if not expected:
        csrf_token(session)  # seed one for the retry
        raise CSRFError("Сесія закінчилась. Спробуйте ще раз.", session_expired=True)

    if not submitted or not hmac.compare_digest(str(expected), str(submitted)):
        raise CSRFError("Помилка безпеки. Спробуйте ще раз.")
