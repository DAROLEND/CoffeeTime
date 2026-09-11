"""
Shared FastAPI dependencies: DB session (re-exported), current customer
user, and the admin-auth dependency.

`get_current_admin` re-fetches role/permissions from `admin_users` on
every admin request, so a permission change by a super-admin takes effect
immediately without the affected staff member re-logging in, and destroys
the session if the admin_users row has been deleted.
"""
from __future__ import annotations

import json

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.session import get_db
from app.models.auth import AdminUser, User


class AuthRequired(Exception):
    """Raised when a public page requires a logged-in customer. The
    exception handler in app.main redirects to the login page."""


def get_current_user(request: Request) -> dict | None:
    """Returns the logged-in customer's session data, or None for guests."""
    return request.state.session.get("user")


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise AuthRequired()
    return user


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    """Re-fetches the admin row every request, refreshes session
    role/permissions/display_name, and destroys the session + raises if
    the account was deleted out from under it."""
    username = request.state.session.get("admin")
    if not username:
        raise AuthRequired()

    admin = db.execute(select(AdminUser).where(AdminUser.username == username)).scalar_one_or_none()
    if admin is None:
        # Account deleted since login.
        request.state.session.clear()
        raise AuthRequired()

    session = request.state.session
    session["admin_role"] = admin.role.value if hasattr(admin.role, "value") else admin.role
    try:
        session["admin_perms"] = json.loads(admin.permissions or "[]")
    except ValueError:
        session["admin_perms"] = []
    if admin.display_name:
        session["admin_display"] = admin.display_name

    return admin
