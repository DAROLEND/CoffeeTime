"""Port of forms/login.php, register.php, forgot.php, reset.php,
change_password.php, and pages/logout.php.

login.php's dual customer/admin branching is reproduced exactly: try the
`users` table first (by email OR login), verify the password, and only
THEN check whether that login also has an admin_users row (customer
account that's also staff); if no `users` row matched at all, fall back
to checking `admin_users` directly (an admin-only account with no
customer-side `users` row). Both paths converge on the same
"admin session" branch that redirects to /admin/dashboard.
"""
from __future__ import annotations

import datetime
import json
import re
import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_user
from app.models.auth import AdminUser, PasswordReset, User
from app.services.auth import (
    hash_password, is_locked_out, record_failed_attempt, verify_password,
)
from app.services.csrf import CSRFError, verify_csrf
from app.services.mail import send_html_email
from app.templating import render

router = APIRouter()

REMEMBER_COOKIE = "remember_me"
LOCK_MINUTES = 15


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "0.0.0.0"


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    if session.get("admin"):
        return RedirectResponse("/admin/dashboard", status_code=302)
    from_admin = "/admin/" in (request.headers.get("referer") or "")
    if session.get("user") and not from_admin:
        return RedirectResponse("/", status_code=302)

    ip = _client_ip(request)
    is_locked = is_locked_out(db, ip)
    return render(
        request, "public/login.html", page="login", page_title="Авторизація — Coffee Time",
        error="", is_locked=is_locked, lock_minutes=LOCK_MINUTES,
        remembered_email=request.cookies.get(REMEMBER_COOKIE, ""),
    )


@router.post("/login")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    try:
        await verify_csrf(request)
    except CSRFError as exc:
        request.state.session["flash_error"] = exc.message
        return RedirectResponse("/login", status_code=303)

    session = request.state.session
    form = await request.form()
    email_or_login = (form.get("email") or "").strip()
    password = (form.get("password") or "").strip()
    remember = "remember" in form

    ip = _client_ip(request)
    is_locked = is_locked_out(db, ip)
    error = ""

    if is_locked:
        error = f"Забагато невдалих спроб. Спробуйте через {LOCK_MINUTES} хвилин."
    elif not email_or_login or not password:
        error = "Будь ласка, заповніть усі поля!"
    else:
        user = db.execute(
            select(User).where((User.email == email_or_login) | (User.login == email_or_login))
        ).scalar_one_or_none()

        if user is not None:
            if verify_password(password, user.password):
                admin_row = db.execute(
                    select(AdminUser).where(AdminUser.username == user.login)
                ).scalar_one_or_none()

                if admin_row:
                    _set_admin_session(session, admin_row)
                    resp = RedirectResponse("/admin/dashboard", status_code=302)
                    return resp

                session["user"] = {
                    "client_id": user.client_id, "login": user.login, "email": user.email,
                    "client_name": user.client_name, "client_surname": user.client_surname,
                    "client_PhoneNumber": user.client_PhoneNumber,
                }
                redirect_to = session.pop("redirect_after_login", "/")
                resp = RedirectResponse(redirect_to, status_code=302)
                if remember:
                    resp.set_cookie(REMEMBER_COOKIE, email_or_login, max_age=7 * 24 * 3600, path="/")
                return resp
            else:
                error = "Невірний пароль."
                record_failed_attempt(db, ip)
        else:
            admin_row = db.execute(
                select(AdminUser).where(AdminUser.username == email_or_login)
            ).scalar_one_or_none()
            if admin_row and verify_password(password, admin_row.password):
                _set_admin_session(session, admin_row)
                return RedirectResponse("/admin/dashboard", status_code=302)
            error = "Користувача не знайдено."
            record_failed_attempt(db, ip)

    return render(
        request, "public/login.html", page="login", page_title="Авторизація — Coffee Time",
        error=error, is_locked=is_locked, lock_minutes=LOCK_MINUTES,
        remembered_email=request.cookies.get(REMEMBER_COOKIE, ""),
    )


def _set_admin_session(session, admin_row: AdminUser) -> None:
    session["admin"] = admin_row.username
    session["admin_role"] = admin_row.role.value if hasattr(admin_row.role, "value") else admin_row.role
    try:
        session["admin_perms"] = json.loads(admin_row.permissions or "[]")
    except ValueError:
        session["admin_perms"] = []


@router.get("/register")
def register_page(request: Request):
    if request.state.session.get("user"):
        return RedirectResponse("/", status_code=302)
    return render(request, "public/register.html", page="register", page_title="Реєстрація — Coffee Time", errors=[], success=False, form={})


@router.post("/register")
async def register_submit(request: Request, db: Session = Depends(get_db)):
    try:
        await verify_csrf(request)
    except CSRFError as exc:
        request.state.session["flash_error"] = exc.message
        return RedirectResponse("/register", status_code=303)

    form = await request.form()
    email = (form.get("email") or "").strip()
    login = (form.get("login") or "").strip()
    password = form.get("password") or ""
    confirm = form.get("confirm") or ""

    errors = []
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("Введіть коректну електронну пошту.")
    if len(login) < 3:
        errors.append("Логін має містити щонайменше 3 символи.")
    if len(password) < 6:
        errors.append("Пароль має містити принаймні 6 символів.")
    if password != confirm:
        errors.append("Паролі не співпадають.")

    if not errors:
        existing = db.execute(
            select(User).where((User.login == login) | (User.email == email))
        ).scalar_one_or_none()
        if existing:
            errors.append("Користувач із таким логіном або email вже існує.")

    success = False
    if not errors:
        db.add(User(email=email, login=login, password=hash_password(password)))
        db.commit()
        success = True

    return render(
        request, "public/register.html", page="register", page_title="Реєстрація — Coffee Time",
        errors=errors, success=success, form={"email": email, "login": login},
    )


@router.get("/forgot")
def forgot_page(request: Request):
    return render(request, "public/forgot.html", page="forgot", page_title="Відновлення пароля — Coffee Time", error="", success=False)


@router.post("/forgot")
async def forgot_submit(request: Request, db: Session = Depends(get_db)):
    from app.config import get_settings

    form = await request.form()
    email = (form.get("email") or "").strip()
    error, success = "", False

    if not email:
        error = "Будь ласка, введіть вашу електронну пошту."
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        error = "Неправильний формат електронної пошти."
    else:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user:
            token = secrets.token_hex(32)
            expires = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            db.add(PasswordReset(email=email, token=token, expires_at=expires))
            db.commit()

            settings = get_settings()
            base_url = (settings.APP_URL or "http://localhost").rstrip("/")
            reset_link = f"{base_url}/reset?token={token}"
            from_name = settings.MAIL_FROM_NAME or "Coffee Time"
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
            if not send_html_email(email, "Відновлення пароля — Coffee Time", html_body, alt_body):
                error = "Не вдалося надіслати листа. Спробуйте пізніше."
            else:
                success = True
        else:
            success = True  # no user-enumeration: always report success

    return render(request, "public/forgot.html", page="forgot", page_title="Відновлення пароля — Coffee Time", error=error, success=success)


@router.get("/reset")
def reset_page(request: Request, token: str = "", db: Session = Depends(get_db)):
    error, success, email = "", False, ""
    token = token.strip()
    if not token:
        error = "Токен не вказано."
    else:
        row = db.execute(select(PasswordReset).where(PasswordReset.token == token)).scalar_one_or_none()
        if row:
            email = row.email
            if row.expires_at < datetime.datetime.utcnow():
                error = "Термін дії посилання вичерпано. Запросіть нове."
        else:
            error = "Недійсне або вже використане посилання."

    return render(
        request, "public/reset.html", page="reset", page_title="Новий пароль — Coffee Time",
        error=error, success=success, email=email, token=token,
    )


@router.post("/reset")
async def reset_submit(request: Request, token: str = "", db: Session = Depends(get_db)):
    form = await request.form()
    token = token.strip()
    password = form.get("password") or ""
    confirm = form.get("confirm") or ""
    error, success, email = "", False, ""

    row = db.execute(select(PasswordReset).where(PasswordReset.token == token)).scalar_one_or_none()
    if not row:
        error = "Недійсне або вже використане посилання."
    else:
        email = row.email
        if row.expires_at < datetime.datetime.utcnow():
            error = "Термін дії посилання вичерпано. Запросіть нове."
        elif len(password) < 6:
            error = "Пароль повинен містити щонайменше 6 символів."
        elif password != confirm:
            error = "Паролі не співпадають."
        else:
            db.execute(
                User.__table__.update().where(User.email == email).values(password=hash_password(password))
            )
            db.execute(PasswordReset.__table__.delete().where(PasswordReset.token == token))
            db.commit()
            success = True

    return render(
        request, "public/reset.html", page="reset", page_title="Новий пароль — Coffee Time",
        error=error, success=success, email=email, token=token,
    )


@router.get("/logout")
def logout(request: Request):
    request.state.session.clear()
    return RedirectResponse("/", status_code=302)


@router.get("/change-password")
def change_password_page(request: Request, user: dict = Depends(require_user)):
    return render(
        request, "public/change_password.html", page="change_password",
        page_title="Зміна паролю — Coffee Time", success_message="", error_message="",
    )


@router.post("/change-password")
async def change_password_submit(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    try:
        await verify_csrf(request)
    except CSRFError as exc:
        request.state.session["flash_error"] = exc.message
        return RedirectResponse("/change-password", status_code=303)

    form = await request.form()
    current_password = form.get("current_password") or ""
    new_password = form.get("new_password") or ""
    confirm_password = form.get("confirm_password") or ""

    success_message, error_message = "", ""
    if not current_password or not new_password or not confirm_password:
        error_message = "Заповніть усі поля."
    elif len(new_password) < 6:
        error_message = "Новий пароль має містити принаймні 6 символів."
    elif new_password != confirm_password:
        error_message = "Нові паролі не збігаються."
    else:
        db_user = db.get(User, user["client_id"])
        if not db_user:
            error_message = "Користувача не знайдено."
        elif not verify_password(current_password, db_user.password):
            error_message = "Неправильний поточний пароль."
        else:
            db_user.password = hash_password(new_password)
            db.commit()
            success_message = "Пароль успішно змінено."

    return render(
        request, "public/change_password.html", page="change_password",
        page_title="Зміна паролю — Coffee Time", success_message=success_message, error_message=error_message,
    )
