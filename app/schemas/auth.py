from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LoginInfo(BaseModel):
    is_locked: bool
    lock_minutes: int
    remembered_email: str


class LoginRequest(BaseModel):
    # One field for both: customers may use their email or their login,
    # admins their username.
    login: str = ""
    password: str = ""
    remember: bool = False


class LoginResult(BaseModel):
    kind: Literal["user", "admin"]
    redirect: str


class RegisterRequest(BaseModel):
    email: str = ""
    login: str = ""
    password: str = ""
    confirm: str = ""


class ForgotRequest(BaseModel):
    email: str = ""


class ResetTokenInfo(BaseModel):
    valid: bool
    email: str
    error: str


class ResetRequest(BaseModel):
    token: str = ""
    password: str = ""
    confirm: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""


class MessageResponse(BaseModel):
    ok: bool = True
    message: str = ""
