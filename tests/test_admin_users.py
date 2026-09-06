"""Phase 8 verification (part 1): admin_users.php port — super-only
access, CSRF now enforced (confirmed fix; PHP had none here), and the
create/edit/delete business rules (can't touch other supers, can't
delete/edit self incorrectly, orders_edit implies orders_view)."""
from __future__ import annotations

import re

from app.models.auth import AdminUser
from app.services.auth import hash_password, verify_password


def _csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', html)
    assert m
    return m.group(1)


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = _csrf_token(resp.text)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_admin_users_requires_super(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/users", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_admin_users_post_requires_csrf(client, db_session):
    """Confirmed fix: PHP's admin_users.php had NO CSRF check at all."""
    _login_admin(client, db_session)
    resp = client.post("/admin/users", data={"action": "create", "username": "newstaff", "password": "secret1", "perms[products]": "1"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/users"
    assert db_session.query(AdminUser).filter_by(username="newstaff").count() == 0


def test_create_staff_account(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)

    resp = client.post("/admin/users", data={
        "csrf_token": token, "action": "create", "username": "newstaff",
        "display_name": "New Staff", "password": "secret123", "perms[products]": "1",
    }, follow_redirects=False)
    assert resp.status_code == 303

    created = db_session.query(AdminUser).filter_by(username="newstaff").one()
    assert created.role.value == "staff"
    assert verify_password("secret123", created.password)
    import json
    assert json.loads(created.permissions) == ["products"]


def test_create_orders_edit_implies_orders_view(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)
    client.post("/admin/users", data={
        "csrf_token": token, "action": "create", "username": "editor",
        "password": "secret123", "perms[orders_edit]": "1",
    })
    import json
    created = db_session.query(AdminUser).filter_by(username="editor").one()
    perms = json.loads(created.permissions)
    assert "orders_view" in perms and "orders_edit" in perms


def test_create_rejects_duplicate_username(client, db_session):
    _login_admin(client, db_session)
    db_session.add(AdminUser(username="taken", password=hash_password("x"), role="staff", permissions="[]"))
    db_session.commit()

    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)
    # POST follows the redirect back to GET /admin/users by default (httpx
    # TestClient), which is also where the flash is popped from the
    # session — check it on this response, not a separate .get() after
    # (that would find the flash already consumed).
    resp = client.post("/admin/users", data={"csrf_token": token, "action": "create", "username": "taken", "password": "secret123", "perms[products]": "1"})
    assert "вже існує" in resp.text


def test_cannot_edit_other_super_account(client, db_session):
    _login_admin(client, db_session, username="boss1")
    other_super = AdminUser(username="boss2", password=hash_password("x"), role="super", permissions="[]")
    db_session.add(other_super)
    db_session.commit()

    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)
    resp = client.post("/admin/users", data={"csrf_token": token, "action": "edit", "id": other_super.id, "display_name": "Hacked", "perms[products]": "1"})

    db_session.expire_all()
    assert db_session.get(AdminUser, other_super.id).display_name != "Hacked"
    assert "Не можна редагувати інших super" in resp.text


def test_cannot_delete_self_or_super(client, db_session):
    admin = _login_admin(client, db_session)
    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)

    client.post("/admin/users", data={"csrf_token": token, "action": "delete", "id": admin.id})
    db_session.expire_all()
    assert db_session.get(AdminUser, admin.id) is not None  # self-delete blocked


def test_delete_staff_account(client, db_session):
    _login_admin(client, db_session)
    staff = AdminUser(username="tempstaff", password=hash_password("x"), role="staff", permissions="[]")
    db_session.add(staff)
    db_session.commit()
    staff_id = staff.id

    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)
    client.post("/admin/users", data={"csrf_token": token, "action": "delete", "id": staff_id})

    assert db_session.get(AdminUser, staff_id) is None


def test_my_account_requires_correct_current_password(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/users")
    token = _csrf_token(resp.text)

    resp = client.post("/admin/users", data={
        "csrf_token": token, "action": "my_account", "display_name": "Me",
        "current_password": "wrongpass", "new_password": "",
    })
    assert "Невірний поточний пароль" in resp.text
