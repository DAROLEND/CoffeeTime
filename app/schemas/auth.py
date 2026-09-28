from __future__ import annotations

from typing import Literal

from app.schemas.base import Schema


class LoginInfo(Schema):
    is_locked: bool
    lock_minutes: int
    remembered_email: str


class LoginRequest(Schema):
    # One field for both: customers may use their email or their login,
    # admins their username.
    login: str = ""
    password: str = ""
    remember: bool = False


class LoginResult(Schema):
    kind: Literal["user", "admin"]
    redirect: str


class RegisterRequest(Schema):
    email: str = ""
    login: str = ""
    password: str = ""
    confirm: str = ""


class ForgotRequest(Schema):
    email: str = ""


class ResetTokenInfo(Schema):
    valid: bool
    email: str
    error: str


class ResetRequest(Schema):
    token: str = ""
    password: str = ""
    confirm: str = ""


class ChangePasswordRequest(Schema):
    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""


class MessageResponse(Schema):
    ok: bool = True
    message: str = ""
