"""Port of admin/login.php (thin redirect stub — the real form lives at
/login) and admin/logout.php."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.requests import Request

router = APIRouter(prefix="/admin")


@router.get("/login")
def admin_login_stub():
    return RedirectResponse("/login", status_code=302)


@router.get("/logout")
def admin_logout(request: Request):
    request.state.session.clear()
    return RedirectResponse("/login", status_code=302)
