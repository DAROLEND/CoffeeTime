"""Registration, the dual customer/admin login branching, IP
rate-limiting, forgot/reset password, change-password and logout —
through the JSON API."""
from __future__ import annotations

import datetime

from app.models.auth import AdminUser, LoginAttempt, PasswordReset, User
from app.services.auth import hash_password, verify_password
from tests.helpers import login_user


def test_register_then_login(api, db_session):
    resp = api.post("/api/auth/register", json={
        "email": "new@example.com", "login": "newuser", "password": "secret6", "confirm": "secret6",
    })
    assert resp.status_code == 201
    assert "Реєстрація успішна" in resp.json()["message"]

    user = db_session.query(User).filter_by(login="newuser").one()
    assert user.email == "new@example.com"
    assert user.password != "secret6"  # hashed, not plaintext

    resp = api.post("/api/auth/login", json={"login": "newuser", "password": "secret6"})
    assert resp.json() == {"kind": "user", "redirect": "/"}
    me = api.get("/api/session").json()
    assert me["user"]["login"] == "newuser"
    assert me["user"]["initials"] == "N"
    assert me["admin"] is None


def test_register_validation_lists_every_error(api):
    resp = api.post("/api/auth/register", json={"email": "bad", "login": "ab", "password": "1", "confirm": "2"})
    assert resp.status_code == 400
    assert len(resp.json()["errors"]) == 4


def test_register_rejects_duplicate_login(api, db_session):
    db_session.add(User(login="taken", email="taken@example.com", password=hash_password("x")))
    db_session.commit()
    resp = api.post("/api/auth/register", json={
        "email": "other@example.com", "login": "taken", "password": "secret6", "confirm": "secret6",
    })
    assert resp.status_code == 400
    assert "вже існує" in resp.json()["detail"]


def test_login_with_email_instead_of_login(api, db_session):
    db_session.add(User(login="olga", email="olga@example.com", password=hash_password("realpass")))
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": "olga@example.com", "password": "realpass"})
    assert resp.status_code == 200


def test_login_with_wrong_password_records_attempt(api, db_session):
    db_session.add(User(login="bob", email="bob@example.com", password=hash_password("realpass")))
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": "bob", "password": "wrong"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Невірний пароль."
    assert db_session.query(LoginAttempt).count() == 1


def test_login_lockout_after_five_failed_attempts(api, db_session):
    db_session.add(User(login="carl", email="carl@example.com", password=hash_password("realpass")))
    db_session.commit()
    for _ in range(5):
        api.post("/api/auth/login", json={"login": "carl", "password": "wrong"})

    assert api.get("/api/auth/login-info").json()["is_locked"] is True
    resp = api.post("/api/auth/login", json={"login": "carl", "password": "realpass"})
    assert resp.status_code == 429  # locked out even with the correct password
    assert "Забагато невдалих спроб" in resp.json()["detail"]


def test_login_customer_account_that_is_also_admin(api, db_session):
    """Login matches `users` by login/email first; when that login also has
    an admin_users row, the session is an admin one."""
    db_session.add(User(login="staffmember", email="staff@example.com", password=hash_password("adminpass")))
    db_session.add(AdminUser(username="staffmember", password=hash_password("adminpass"), role="staff", permissions='["products"]'))
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": "staffmember", "password": "adminpass"})
    assert resp.json() == {"kind": "admin", "redirect": "/admin/dashboard"}
    me = api.get("/api/session").json()
    assert me["admin"] == {"username": "staffmember", "display_name": "staffmember", "role": "staff", "perms": ["products"]}
    assert me["user"] is None


def test_login_admin_only_account_with_no_users_row(api, db_session):
    db_session.add(AdminUser(username="admin_only", password=hash_password("adminpass"), role="super", permissions="[]"))
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": "admin_only", "password": "adminpass"})
    assert resp.json()["kind"] == "admin"


def test_login_rotates_session_id(api, db_session):
    db_session.add(User(login="dan", email="dan@example.com", password=hash_password("pass1234")))
    db_session.commit()
    api.get("/api/csrf-token")
    before = api.client.cookies.get("coffeetime_session")
    api.post("/api/auth/login", json={"login": "dan", "password": "pass1234"})
    after = api.client.cookies.get("coffeetime_session")
    assert before and after and before != after


def test_remember_me_cookie_prefills_login(api, db_session):
    db_session.add(User(login="eve", email="eve@example.com", password=hash_password("pass1234")))
    db_session.commit()
    api.post("/api/auth/login", json={"login": "eve@example.com", "password": "pass1234", "remember": True})
    assert api.get("/api/auth/login-info").json()["remembered_email"] == "eve@example.com"


def test_forgot_password_creates_reset_token(api, db_session, monkeypatch):
    import app.routers.public.auth as auth_module
    monkeypatch.setattr(auth_module, "send_html_email", lambda *a, **k: True)
    db_session.add(User(login="dana", email="dana@example.com", password=hash_password("x")))
    db_session.commit()

    resp = api.post("/api/auth/forgot", json={"email": "dana@example.com"})
    assert resp.json()["message"] == "Лист надіслано"
    reset = db_session.query(PasswordReset).filter_by(email="dana@example.com").one()
    assert len(reset.token) == 64


def test_forgot_password_reports_unknown_email(api, db_session):
    resp = api.post("/api/auth/forgot", json={"email": "nobody@example.com"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "email_not_found"
    assert resp.json()["detail"] == "Користувача з такою поштою не знайдено."


def test_forgot_password_matches_email_case_insensitively(api, db_session, monkeypatch):
    import app.routers.public.auth as auth_module
    sent = []
    monkeypatch.setattr(auth_module, "send_html_email", lambda to, *a, **k: sent.append(to) or True)
    db_session.add(User(login="olena", email="olena@example.com", password=hash_password("x")))
    db_session.commit()

    api.post("/api/auth/forgot", json={"email": "Olena@Example.com"})
    assert sent == ["olena@example.com"]  # the registered address
    assert db_session.query(PasswordReset).filter_by(email="olena@example.com").count() == 1


def test_forgot_password_reports_mail_failure(api, db_session, monkeypatch):
    import app.routers.public.auth as auth_module
    monkeypatch.setattr(auth_module, "send_html_email", lambda *a, **k: False)
    db_session.add(User(login="maria", email="maria@example.com", password=hash_password("x")))
    db_session.commit()
    resp = api.post("/api/auth/forgot", json={"email": "maria@example.com"})
    assert resp.status_code == 502
    assert resp.json()["code"] == "mail_failed"


def test_login_by_email_ignores_case(api, db_session):
    db_session.add(User(login="ivan", email="ivan@example.com", password=hash_password("pass1234")))
    db_session.commit()
    resp = api.post("/api/auth/login", json={"login": "Ivan@Example.com", "password": "pass1234"})
    assert resp.status_code == 200, resp.text


def test_register_rejects_email_differing_only_in_case(api, db_session):
    db_session.add(User(login="taken", email="taken@example.com", password=hash_password("x")))
    db_session.commit()
    resp = api.post("/api/auth/register", json={"email": "Taken@Example.com", "login": "fresh", "password": "secret1", "confirm": "secret1"})
    assert resp.status_code == 400


def test_mail_without_smtp_config_fails_fast(monkeypatch):
    from app.config import get_settings
    from app.services import mail

    settings = get_settings()
    monkeypatch.setattr(settings, "MAIL_HOST", "")
    assert mail.send_html_email("a@example.com", "s", "<p>h</p>", "h") is False


def test_forgot_password_validates_email(api):
    assert api.post("/api/auth/forgot", json={"email": "nope"}).status_code == 400


def test_reset_password_with_valid_token(api, db_session):
    db_session.add(User(login="erin", email="erin@example.com", password=hash_password("oldpass")))
    db_session.add(PasswordReset(email="erin@example.com", token="a" * 64, expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)))
    db_session.commit()

    info = api.get("/api/auth/reset?token=" + "a" * 64).json()
    assert info == {"valid": True, "email": "erin@example.com", "error": ""}

    resp = api.post("/api/auth/reset", json={"token": "a" * 64, "password": "newpass123", "confirm": "newpass123"})
    assert resp.json()["message"] == "Пароль змінено"

    db_session.expire_all()
    user = db_session.query(User).filter_by(login="erin").one()
    assert verify_password("newpass123", user.password)
    assert db_session.query(PasswordReset).filter_by(token="a" * 64).count() == 0


def test_reset_password_with_expired_token(api, db_session):
    db_session.add(PasswordReset(email="frank@example.com", token="b" * 64, expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1)))
    db_session.commit()
    info = api.get("/api/auth/reset?token=" + "b" * 64).json()
    assert info["valid"] is False
    assert "вичерпано" in info["error"]
    resp = api.post("/api/auth/reset", json={"token": "b" * 64, "password": "newpass123", "confirm": "newpass123"})
    assert resp.status_code == 400


def test_change_password_requires_login(api):
    resp = api.post("/api/auth/change-password", json={"current_password": "a", "new_password": "bbbbbb", "confirm_password": "bbbbbb"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "auth_required"


def test_change_password_flow(api, db_session):
    login_user(api, db_session, login="gina", password="oldpass123")
    resp = api.post("/api/auth/change-password", json={
        "current_password": "oldpass123", "new_password": "brandnew123", "confirm_password": "brandnew123",
    })
    assert "успішно змінено" in resp.json()["message"]
    db_session.expire_all()
    user = db_session.query(User).filter_by(login="gina").one()
    assert verify_password("brandnew123", user.password)


def test_logout_clears_session(api, db_session):
    login_user(api, db_session, login="hank", password="pass123")
    assert api.post("/api/auth/logout").json() == {"ok": True}
    assert api.get("/api/session").json()["user"] is None
    resp = api.post("/api/auth/change-password", json={"current_password": "pass123", "new_password": "x" * 8, "confirm_password": "x" * 8})
    assert resp.status_code == 401  # no longer logged in


def test_login_shared_account_checks_the_admin_password(api, db_session):
    """If the two rows' passwords differ, the admin one is what signs in."""
    db_session.add(User(login="mixed", email="mixed@example.com", password=hash_password("customerpass")))
    db_session.add(AdminUser(username="mixed", password=hash_password("adminpass"), role="super", permissions="[]"))
    db_session.commit()
    assert api.post("/api/auth/login", json={"login": "mixed", "password": "customerpass"}).status_code == 400
    assert api.post("/api/auth/login", json={"login": "mixed", "password": "adminpass"}).json()["kind"] == "admin"
