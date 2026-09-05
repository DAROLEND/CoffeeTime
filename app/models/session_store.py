"""
Server-side session storage — new infrastructure, not a PHP table.

PHP used file-based `$_SESSION` (opaque to the DB entirely, keyed by a
cookie holding the raw session id). FastAPI has no built-in equivalent, so
this table plays that role: the cookie holds only a signed, random session
id; the actual session dict (cart, user, csrf_token, flash_*, etc. — the
same key set enumerated in the migration plan) lives here as JSON.

Chosen over a pure signed-cookie session (Starlette's SessionMiddleware)
because the PHP cart can hold many variant-JSON blobs and would otherwise
bloat the cookie; this also keeps the session payload opaque to the
client, matching today's behavior more closely than a client-readable
signed cookie would.
"""
from __future__ import annotations

import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSession(Base):
    __tablename__ = "app_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[str] = mapped_column(Text, default="{}")  # JSON-encoded dict
    last_activity: Mapped[datetime.datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
