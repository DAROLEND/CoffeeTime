from __future__ import annotations

from typing import Literal

from app.schemas.base import Schema


class CsrfTokenResponse(Schema):
    csrf_token: str


class SessionUser(Schema):
    client_id: int
    login: str
    email: str
    client_name: str | None = None
    client_surname: str | None = None
    client_PhoneNumber: str | None = None  # noqa: N815 — mirrors the DB column
    initials: str
    display_name: str


class SessionAdmin(Schema):
    username: str
    display_name: str
    role: Literal["super", "staff"]
    perms: list[str]


class SessionCart(Schema):
    count: int
    keys: list[str]


class SessionInfo(Schema):
    user: SessionUser | None
    admin: SessionAdmin | None
    cart: SessionCart
