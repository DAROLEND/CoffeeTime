from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CsrfTokenResponse(BaseModel):
    csrf_token: str


class SessionUser(BaseModel):
    client_id: int
    login: str
    email: str
    client_name: str | None = None
    client_surname: str | None = None
    client_PhoneNumber: str | None = None  # noqa: N815 — mirrors the DB column
    initials: str
    display_name: str


class SessionAdmin(BaseModel):
    username: str
    display_name: str
    role: Literal["super", "staff"]
    perms: list[str]


class SessionCart(BaseModel):
    count: int
    keys: list[str]


class SessionInfo(BaseModel):
    user: SessionUser | None
    admin: SessionAdmin | None
    cart: SessionCart
