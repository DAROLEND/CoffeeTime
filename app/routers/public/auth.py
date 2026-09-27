"""
Login, registration, password reset/change, and logout.

Login checks the `users` table first (by email OR login) and verifies
the password, then checks whether that login also has an admin_users row
(a customer account that's also staff); if no `users` row matched at
all, it falls back to checking `admin_users` directly (an admin-only
account with no customer-side `users` row). Both admin paths return
`kind: "admin"` and the SPA goes to /admin/dashboard.

A successful login rotates the session id (see
app/middleware/session.py), so a session id planted before login is
useless afterwards.
"""
from __future__ import annotations

import datetime
import json
import re
import secrets

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError, bad_request
from app.config import get_settings
from app.db.session import get_db
from app.dependencies import require_user
from app.models.auth import AdminUser, PasswordReset, User
from app.schemas.auth import (
    ChangePasswordRequest, ForgotRequest, LoginInfo, LoginRequest, LoginResult,
    MessageResponse, RegisterRequest, ResetRequest, ResetTokenInfo,
)
from app.schemas.common import OkResponse
from app.services.auth import hash_password, is_locked_out, record_failed_attempt, verify_password
from app.services.mail import send_html_email

router = APIRouter(prefix="/auth", tags=["auth"])

REMEMBER_COOKIE = "remember_me"
LOCK_MINUTES = 15
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "0.0.0.0"


def _set_admin_session(request: Request, admin_row: AdminUser) -> None:
    session = request.state.session
    session.pop("user", None)
    session["admin"] = admin_row.username
    session["admin_role"] = admin_row.role.value if hasattr(admin_row.role, "value") else admin_row.role
    try:
        session["admin_perms"] = json.loads(admin_row.permissions or "[]")
    except ValueError:
        session["admin_perms"] = []
    request.state.rotate_session = True


def _locked_error() -> ApiError:
    return ApiError(429, f"Забагато невдалих спроб. Спробуйте через {LOCK_MINUTES} хвилин.", code="locked")


@router.get("/login-info", response_model=LoginInfo)
def login_info(request: Request, db: Session = Depends(get_db)):
    return {
        "is_locked": is_locked_out(db, _client_ip(request)),
        "lock_minutes": LOCK_MINUTES,
        "remembered_email": request.cookies.get(REMEMBER_COOKIE, ""),
    }


@router.post("/login", response_model=LoginResult)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    session = request.state.session
    email_or_login = body.login.strip()
    password = body.password.strip()
    ip = _client_ip(request)

    if is_locked_out(db, ip):
        raise _locked_error()
    if not email_or_login or not password:
        raise bad_request("Будь ласка, заповніть усі поля!", code="missing_fields")

    user = db.execute(
        select(User).where((User.email == email_or_login) | (User.login == email_or_login))
    ).scalar_one_or_none()

    if user is not None:
        if not verify_password(password, user.password):
            record_failed_attempt(db, ip)
            raise bad_request("Невірний пароль.", code="invalid_credentials")
        admin_row = db.execute(select(AdminUser).where(AdminUser.username == user.login)).scalar_one_or_none()
        if admin_row:
            _set_admin_session(request, admin_row)
            return {"kind": "admin", "redirect": "/admin/dashboard"}

        session["user"] = {
            "client_id": user.client_id, "login": user.login, "email": user.email,
            "client_name": user.client_name, "client_surname": user.client_surname,
            "client_PhoneNumber": user.client_PhoneNumber,
        }
        request.state.rotate_session = True
        if body.remember:
            response.set_cookie(REMEMBER_COOKIE, email_or_login, max_age=7 * 24 * 3600, path="/", samesite="lax")
        else:
            response.delete_cookie(REMEMBER_COOKIE, path="/")
        return {"kind": "user", "redirect": session.pop("redirect_after_login", "/")}

    admin_row = db.execute(select(AdminUser).where(AdminUser.username == email_or_login)).scalar_one_or_none()
    if admin_row and verify_password(password, admin_row.password):
        _set_admin_session(request, admin_row)
        return {"kind": "admin", "redirect": "/admin/dashboard"}
    record_failed_attempt(db, ip)
    raise bad_request("Користувача не знайдено.", code="invalid_credentials")


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.strip()
    login = body.login.strip()

    errors = []
    if not email or not EMAIL_RE.match(email):
        errors.append("Введіть коректну електронну пошту.")
    if len(login) < 3:
        errors.append("Логін має містити щонайменше 3 символи.")
    if len(body.password) < 6:
        errors.append("Пароль має містити принаймні 6 символів.")
    if body.password != body.confirm:
        errors.append("Паролі не співпадають.")
    if not errors:
        existing = db.execute(select(User.client_id).where((User.login == login) | (User.email == email))).first()
        if existing:
            errors.append("Користувач із таким логіном або email вже існує.")
    if errors:
        raise bad_request(errors[0], code="validation", errors=errors)

    db.add(User(email=email, login=login, password=hash_password(body.password)))
    db.commit()
    return {"ok": True, "message": "Реєстрація успішна! Тепер ви можете увійти."}


@router.post("/forgot", response_model=MessageResponse)
def forgot(body: ForgotRequest, db: Session = Depends(get_db)):
    email = body.email.strip()
    if not email:
        raise bad_request("Будь ласка, введіть вашу електронну пошту.")
    if not EMAIL_RE.match(email):
        raise bad_request("Неправильний формат електронної пошти.")

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        # No user enumeration: the same answer whether or not the email exists.
        return {"ok": True, "message": "Лист надіслано"}

    token = secrets.token_hex(32)
    db.add(PasswordReset(email=email, token=token, expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)))
    db.commit()

    settings = get_settings()
    reset_link = f"{(settings.APP_URL or 'http://localhost').rstrip('/')}/reset?token={token}"
    html_body, alt_body = _reset_email(reset_link, settings.MAIL_FROM_NAME or "Coffee Time")
    if not send_html_email(email, "Відновлення пароля — Coffee Time", html_body, alt_body):
        raise ApiError(502, "Не вдалося надіслати листа. Спробуйте пізніше.", code="mail_failed")
    return {"ok": True, "message": "Лист надіслано"}


def _reset_row(db: Session, token: str) -> tuple[PasswordReset | None, str]:
    token = token.strip()
    if not token:
        return None, "Токен не вказано."
    row = db.execute(select(PasswordReset).where(PasswordReset.token == token)).scalar_one_or_none()
    if row is None:
        return None, "Недійсне або вже використане посилання."
    if row.expires_at < datetime.datetime.utcnow():
        return row, "Термін дії посилання вичерпано. Запросіть нове."
    return row, ""


@router.get("/reset", response_model=ResetTokenInfo)
def reset_info(token: str = "", db: Session = Depends(get_db)):
    row, error = _reset_row(db, token)
    return {"valid": not error, "email": row.email if row else "", "error": error}


@router.post("/reset", response_model=MessageResponse)
def reset_password(body: ResetRequest, db: Session = Depends(get_db)):
    row, error = _reset_row(db, body.token)
    if error:
        raise bad_request(error, code="invalid_token")
    if len(body.password) < 6:
        raise bad_request("Пароль повинен містити щонайменше 6 символів.")
    if body.password != body.confirm:
        raise bad_request("Паролі не співпадають.")
    db.execute(User.__table__.update().where(User.email == row.email).values(password=hash_password(body.password)))
    db.execute(PasswordReset.__table__.delete().where(PasswordReset.token == row.token))
    db.commit()
    return {"ok": True, "message": "Пароль змінено"}


@router.post("/change-password", response_model=MessageResponse)
def change_password(body: ChangePasswordRequest, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    if not body.current_password or not body.new_password or not body.confirm_password:
        raise bad_request("Заповніть усі поля.")
    if len(body.new_password) < 6:
        raise bad_request("Новий пароль має містити принаймні 6 символів.")
    if body.new_password != body.confirm_password:
        raise bad_request("Нові паролі не збігаються.")
    db_user = db.get(User, user["client_id"])
    if db_user is None:
        raise bad_request("Користувача не знайдено.")
    if not verify_password(body.current_password, db_user.password):
        raise bad_request("Неправильний поточний пароль.", code="invalid_credentials")
    db_user.password = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "Пароль успішно змінено."}


@router.post("/logout", response_model=OkResponse)
def logout(request: Request):
    request.state.session.clear()
    request.state.rotate_session = True
    return {"ok": True}


def _reset_email(reset_link: str, from_name: str) -> tuple[str, str]:
    html_body = f"""<!DOCTYPE html><html lang="uk"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#faf7f2;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#faf7f2;padding:32px 16px;">
<tr><td align="center"><table width="100%" style="max-width:520px;background:#fff;border-radius:16px;border:1px solid #f0e8df;overflow:hidden;">
<tr><td style="background:#FFC107;padding:24px 32px;text-align:center;">
<p style="margin:0;font-size:28px;">☕</p><p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#5a2d00;">{from_name}</p></td></tr>
<tr><td style="padding:32px;">
<p style="margin:0 0 8px;font-size:22px;font-weight:700;color:#2c1810;">Відновлення пароля</p>
<p style="margin:0 0 24px;font-size:15px;color:#666;line-height:1.6;">Ми отримали запит на скидання пароля для вашого акаунту.<br>Натисніть кнопку нижче — посилання дійсне протягом <strong>1 години</strong>.</p>
<table cellpadding="0" cellspacing="0" style="margin:0 auto 24px;"><tr><td style="background:#FFC107;border-radius:12px;padding:0;">
<a href="{reset_link}" style="display:inline-block;padding:13px 36px;font-size:15px;font-weight:700;color:#5a2d00;text-decoration:none;white-space:nowrap;">Змінити пароль</a></td></tr></table>
<p style="margin:0;font-size:12px;color:#aaa;text-align:center;line-height:1.6;">Якщо ви не надсилали цей запит — просто ігноруйте цей лист.<br>Ваш пароль залишиться незмінним.</p></td></tr>
<tr><td style="padding:16px 32px;border-top:1px solid #f0e8df;text-align:center;"><p style="margin:0;font-size:12px;color:#bbb;">Маєте питання? Ми завжди поруч ☕</p></td></tr>
</table></td></tr></table></body></html>"""
    alt_body = f"Щоб скинути пароль, перейдіть за посиланням: {reset_link}\n\nПосилання дійсне 1 годину."
    return html_body, alt_body
