"""Session bootstrap for the SPA: the CSRF token, and who is logged in
plus the cart badge (read by the header on every page)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.auth import AdminUser
from app.schemas.session import CsrfTokenResponse, SessionAdmin, SessionCart, SessionInfo, SessionUser
from app.services.cart import cart_keys, get_cart, total_qty
from app.services.csrf import csrf_token
from app.services.enum_utils import enum_value

router = APIRouter(tags=["session"])


def user_display(user: dict) -> tuple[str, str]:
    """(initials, display name) — "Олена Шевченко" / login fallback."""
    first = user.get("client_name") or ""
    last = user.get("client_surname") or ""
    initials = ((first[:1] + last[:1]) or (user.get("login") or "U")[:1]).upper()
    display = f"{first} {last}".strip() or user.get("login", "")
    return initials, display


def session_user(user: dict | None) -> SessionUser | None:
    if not user:
        return None
    initials, display = user_display(user)
    return SessionUser(
        client_id=user["client_id"], login=user.get("login") or "", email=user.get("email") or "",
        client_name=user.get("client_name"), client_surname=user.get("client_surname"),
        client_PhoneNumber=user.get("client_PhoneNumber"), initials=initials, display_name=display,
    )


@router.get("/csrf-token", response_model=CsrfTokenResponse)
def get_csrf_token(request: Request):
    return {"csrf_token": csrf_token(request.state.session)}


@router.get("/session", response_model=SessionInfo)
def get_session_info(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    admin = None
    username = session.get("admin")
    if username:
        # Re-read the row so a role/permission change (or deletion) shows up
        # without a re-login, same as get_current_admin does.
        row = db.execute(select(AdminUser).where(AdminUser.username == username)).scalar_one_or_none()
        if row is None:
            session.clear()
        else:
            try:
                perms = json.loads(row.permissions or "[]")
            except ValueError:
                perms = []
            admin = SessionAdmin(
                username=row.username, display_name=row.display_name or row.username,
                role=enum_value(row.role) or "staff", perms=perms,
            )
    cart = get_cart(session)
    return SessionInfo(
        user=session_user(session.get("user")), admin=admin,
        cart=SessionCart(count=total_qty(cart), keys=cart_keys(cart)),
    )
