"""
CSRF protection for the SPA.

The token lives in the server-side session, as before. The SPA reads it
once from `GET /api/csrf-token` and sends it back in an `X-CSRF-Token`
header on every mutating request (the old form field is gone). The
check itself is unchanged: a constant-time compare against the session
copy.

`verify_csrf` is a dependency on the whole `/api` router (see
app/api/router.py), so a new endpoint is covered by default. It raises
CSRFError instead of building a response, and app/main.py maps that to a
403 with a `code` the client uses to fetch a fresh token and retry once.

A header works as a CSRF defence here because a cross-site page can't
set custom headers on a credentialed request without a CORS preflight,
and the API allows no cross-origin callers.
"""
from __future__ import annotations

import hmac
import secrets

from starlette.requests import Request

from app.middleware.session import SessionData

CSRF_SESSION_KEY = "csrf_token"
CSRF_HEADER = "x-csrf-token"
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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


async def verify_csrf(request: Request) -> None:
    """Raise CSRFError unless a mutating request carries the session's
    token in the X-CSRF-Token header. Safe methods pass through."""
    if request.method not in MUTATING_METHODS:
        return

    session: SessionData = request.state.session
    expected = session.get(CSRF_SESSION_KEY, "")
    submitted = request.headers.get(CSRF_HEADER, "")

    if not expected:
        csrf_token(session)  # seed one for the retry
        raise CSRFError("Сесія закінчилась. Спробуйте ще раз.", session_expired=True)

    if not submitted or not hmac.compare_digest(str(expected), str(submitted)):
        raise CSRFError("Помилка безпеки. Спробуйте ще раз.")
