"""Phase 4 verification: registration, the dual customer/admin login
branching, IP rate-limiting, forgot/reset password, and change-password —
driven through FastAPI's TestClient against seeded data."""
from __future__ import annotations

import re

from app.models.auth import AdminUser, PasswordReset, User
from app.services.auth import hash_password


def _csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', html)
    assert m, "csrf token not found in rendered form"
    return m.group(1)


def test_register_then_login(client, db_session):
    resp = client.get("/register")
    token = _csrf_token(resp.text)

    resp = client.post("/register", data={
        "csrf_token": token, "email": "new@example.com", "login": "newuser",
        "password": "secret6", "confirm": "secret6",
    }, follow_redirects=False)
    assert resp.status_code == 200  # re-renders with success overlay, no redirect
    assert "Реєстрація успішна" in resp.text or "successful" in resp.text.lower() or "show" in resp.text

    user = db_session.query(User).filter_by(login="newuser").one()
    assert user.email == "new@example.com"
    assert user.password != "secret6"  # hashed, not plaintext

    # Now log in with the account just created
    resp = client.get("/login")
    token = _csrf_token(resp.text)
    resp = client.post("/login", data={"csrf_token": token, "email": "newuser", "password": "secret6"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


def test_register_rejects_duplicate_login(client, db_session):
    db_session.add(User(login="taken", email="taken@example.com", password=hash_password("x")))
    db_session.commit()

    resp = client.get("/register")
    token = _csrf_token(resp.text)
    resp = client.post("/register", data={
        "csrf_token": token, "email": "other@example.com", "login": "taken",
        "password": "secret6", "confirm": "secret6",
    })
    assert resp.status_code == 200
    assert "вже існує" in resp.text


def test_login_with_wrong_password_records_attempt_and_shows_error(client, db_session):
    db_session.add(User(login="bob", email="bob@example.com", password=hash_password("realpass")))
    db_session.commit()

    resp = client.get("/login")
    token = _csrf_token(resp.text)
    resp = client.post("/login", data={"csrf_token": token, "email": "bob", "password": "wrong"})
    assert resp.status_code == 200
    assert "Невірний пароль" in resp.text

    from app.models.auth import LoginAttempt
    assert db_session.query(LoginAttempt).count() == 1


def test_login_lockout_after_five_failed_attempts(client, db_session):
    db_session.add(User(login="carl", email="carl@example.com", password=hash_password("realpass")))
    db_session.commit()

    for _ in range(5):
        resp = client.get("/login")
        token = _csrf_token(resp.text)
        client.post("/login", data={"csrf_token": token, "email": "carl", "password": "wrong"})

    resp = client.get("/login")
    assert "Забагато невдалих спроб" in resp.text
    token = _csrf_token(resp.text)
    resp = client.post("/login", data={"csrf_token": token, "email": "carl", "password": "realpass"})
    assert "Забагато невдалих спроб" in resp.text  # locked out even with the correct password


def test_login_customer_account_that_is_also_admin_goes_to_dashboard(client, db_session):
    """login.php's core branching: matches `users` by login/email first,
    verifies the password there, and ONLY THEN checks whether that same
    login also has an admin_users row."""
    db_session.add(User(login="staffmember", email="staff@example.com", password=hash_password("adminpass")))
    db_session.add(AdminUser(username="staffmember", password=hash_password("adminpass"), role="staff", permissions="[]"))
    db_session.commit()

    resp = client.get("/login")
    token = _csrf_token(resp.text)
    resp = client.post("/login", data={"csrf_token": token, "email": "staffmember", "password": "adminpass"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/admin/dashboard"


def test_login_admin_only_account_with_no_users_row(client, db_session):
    db_session.add(AdminUser(username="admin_only", password=hash_password("adminpass"), role="super", permissions="[]"))
    db_session.commit()

    resp = client.get("/login")
    token = _csrf_token(resp.text)
    resp = client.post("/login", data={"csrf_token": token, "email": "admin_only", "password": "adminpass"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/admin/dashboard"


def test_forgot_password_creates_reset_token(client, db_session, monkeypatch):
    import app.routers.public.auth as auth_module
    monkeypatch.setattr(auth_module, "send_html_email", lambda *a, **k: True)

    db_session.add(User(login="dana", email="dana@example.com", password=hash_password("x")))
    db_session.commit()

    resp = client.post("/forgot", data={"email": "dana@example.com"})
    assert resp.status_code == 200
    assert "Лист надіслано" in resp.text

    reset = db_session.query(PasswordReset).filter_by(email="dana@example.com").one()
    assert len(reset.token) == 64


def test_forgot_password_does_not_leak_whether_email_exists(client, db_session):
    resp = client.post("/forgot", data={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "Лист надіслано" in resp.text  # same success message either way


def test_reset_password_with_valid_token(client, db_session):
    import datetime
    db_session.add(User(login="erin", email="erin@example.com", password=hash_password("oldpass")))
    db_session.add(PasswordReset(email="erin@example.com", token="a" * 64, expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)))
    db_session.commit()

    resp = client.get("/reset?token=" + "a" * 64)
    assert resp.status_code == 200
    assert "Введіть новий пароль" in resp.text

    resp = client.post("/reset?token=" + "a" * 64, data={"password": "newpass123", "confirm": "newpass123"})
    assert resp.status_code == 200
    assert "Пароль змінено" in resp.text

    from app.services.auth import verify_password
    db_session.expire_all()
    user = db_session.query(User).filter_by(login="erin").one()
    assert verify_password("newpass123", user.password)
    assert db_session.query(PasswordReset).filter_by(token="a" * 64).count() == 0


def test_reset_password_with_expired_token(client, db_session):
    import datetime
    db_session.add(PasswordReset(email="frank@example.com", token="b" * 64, expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1)))
    db_session.commit()

    resp = client.get("/reset?token=" + "b" * 64)
    assert "вичерпано" in resp.text


def test_change_password_requires_login(client, db_session):
    resp = client.get("/change-password", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_change_password_flow(client, db_session):
    db_session.add(User(login="gina", email="gina@example.com", password=hash_password("oldpass123")))
    db_session.commit()

    resp = client.get("/login")
    token = _csrf_token(resp.text)
    client.post("/login", data={"csrf_token": token, "email": "gina", "password": "oldpass123"}, follow_redirects=False)

    resp = client.get("/change-password")
    assert resp.status_code == 200
    token = _csrf_token(resp.text)

    resp = client.post("/change-password", data={
        "csrf_token": token, "current_password": "oldpass123",
        "new_password": "brandnew123", "confirm_password": "brandnew123",
    })
    assert "успішно змінено" in resp.text

    from app.services.auth import verify_password
    db_session.expire_all()
    user = db_session.query(User).filter_by(login="gina").one()
    assert verify_password("brandnew123", user.password)


def test_logout_clears_session(client, db_session):
    db_session.add(User(login="hank", email="hank@example.com", password=hash_password("pass123")))
    db_session.commit()
    resp = client.get("/login")
    token = _csrf_token(resp.text)
    client.post("/login", data={"csrf_token": token, "email": "hank", "password": "pass123"}, follow_redirects=False)

    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get("/change-password", follow_redirects=False)
    assert resp.status_code == 303  # no longer logged in
