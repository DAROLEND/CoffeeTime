"""
Server-side session storage. The cookie holds only a random session id;
the session dict (cart, user, csrf_token, flash_*, etc.) lives here as
JSON.

Chosen over a pure signed-cookie session (Starlette's SessionMiddleware)
because the cart can hold many variant-JSON blobs and would otherwise
bloat the cookie; this also keeps the session payload opaque to the
client rather than merely signed.
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
