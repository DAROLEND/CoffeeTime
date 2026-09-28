"""Staff-account management: super-only access, CSRF enforcement, and the
create/edit/delete business rules (can't touch other supers, can't delete
self, orders_edit implies orders_view)."""
from __future__ import annotations

import json

from app.models.auth import AdminUser, User
from app.services.auth import hash_password, verify_password
from tests.helpers import login_admin


def test_admin_users_requires_super(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    resp = api.get("/api/admin/users")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Цей розділ доступний тільки головному адміну."


def test_admin_users_post_requires_csrf(api, db_session):
    login_admin(api, db_session)
    resp = api.client.post("/api/admin/users", json={"username": "newstaff", "password": "secret1", "perms": ["products"]})
    assert resp.status_code == 403
    assert resp.json()["code"] == "csrf_invalid"
    assert db_session.query(AdminUser).filter_by(username="newstaff").count() == 0


def test_list_admins(api, db_session):
    login_admin(api, db_session)
    data = api.get("/api/admin/users").json()
    assert data["users"][0]["username"] == "boss" and data["users"][0]["is_me"] is True
    assert [p["key"] for p in data["all_perms"]] == ["orders_view", "orders_edit", "products", "content", "reviews"]


def test_create_staff_account(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/users", json={
        "username": "newstaff", "display_name": "New Staff", "password": "secret123", "perms": ["products"],
    })
    assert resp.status_code == 201
    created = db_session.query(AdminUser).filter_by(username="newstaff").one()
    assert created.role.value == "staff"
    assert verify_password("secret123", created.password)
    assert json.loads(created.permissions) == ["products"]


def test_create_orders_edit_implies_orders_view(api, db_session):
    login_admin(api, db_session)
    api.post("/api/admin/users", json={"username": "editor", "password": "secret123", "perms": ["orders_edit", "bogus"]})
    perms = json.loads(db_session.query(AdminUser).filter_by(username="editor").one().permissions)
    assert sorted(perms) == ["orders_edit", "orders_view"]  # unknown keys dropped


def test_create_rejects_duplicate_username(api, db_session):
    login_admin(api, db_session)
    db_session.add(AdminUser(username="taken", password=hash_password("x"), role="staff", permissions="[]"))
    db_session.commit()
    resp = api.post("/api/admin/users", json={"username": "taken", "password": "secret123", "perms": ["products"]})
    assert resp.status_code == 400
    assert "вже існує" in resp.json()["detail"]


def test_cannot_edit_other_super_account(api, db_session):
    login_admin(api, db_session, username="boss1")
    other_super = AdminUser(username="boss2", password=hash_password("x"), role="super", permissions="[]")
    db_session.add(other_super)
    db_session.commit()
    resp = api.patch(f"/api/admin/users/{other_super.id}", json={"display_name": "Hacked", "perms": ["products"]})
    assert resp.status_code == 403
    assert "Не можна редагувати інших super" in resp.json()["detail"]
    db_session.expire_all()
    assert db_session.get(AdminUser, other_super.id).display_name != "Hacked"


def test_edit_staff_account(api, db_session):
    login_admin(api, db_session)
    staff = AdminUser(username="s1", password=hash_password("x"), role="staff", permissions='["products"]')
    db_session.add(staff)
    db_session.commit()
    api.patch(f"/api/admin/users/{staff.id}", json={"display_name": "Оля", "perms": ["content"], "new_password": "newsecret"})
    db_session.expire_all()
    updated = db_session.get(AdminUser, staff.id)
    assert updated.display_name == "Оля" and json.loads(updated.permissions) == ["content"]
    assert verify_password("newsecret", updated.password)


def test_cannot_delete_self_or_super(api, db_session):
    admin = login_admin(api, db_session)
    assert api.delete(f"/api/admin/users/{admin.id}").status_code == 400
    other_super = AdminUser(username="boss2", password=hash_password("x"), role="super", permissions="[]")
    db_session.add(other_super)
    db_session.commit()
    assert api.delete(f"/api/admin/users/{other_super.id}").status_code == 403
    db_session.expire_all()
    assert db_session.get(AdminUser, admin.id) is not None


def test_delete_staff_account(api, db_session):
    login_admin(api, db_session)
    staff = AdminUser(username="tempstaff", password=hash_password("x"), role="staff", permissions="[]")
    db_session.add(staff)
    db_session.commit()
    staff_id = staff.id
    assert "видалено" in api.delete(f"/api/admin/users/{staff_id}").json()["message"]
    assert db_session.get(AdminUser, staff_id) is None


def test_my_account_requires_correct_current_password(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/users/me", json={"display_name": "Me", "current_password": "wrongpass", "new_password": ""})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Невірний поточний пароль."
    ok = api.post("/api/admin/users/me", json={"display_name": "Me", "current_password": "adminpass1", "new_password": ""})
    assert ok.json()["message"] == "Акаунт оновлено."
    assert api.get("/api/admin/layout").json()["display_name"] == "Me"


def test_my_account_new_password_works_for_login_shared_with_a_customer(api, db_session):
    """The admin login also has a customer row. After "Мій акаунт" changes
    the password, the new one signs in and the old one no longer does."""
    db_session.add(User(login="boss", email="boss@example.com", password=hash_password("adminpass1")))
    db_session.commit()
    login_admin(api, db_session)
    resp = api.post("/api/admin/users/me", json={"display_name": "Boss", "current_password": "adminpass1", "new_password": "brandnew1"})
    assert resp.json()["message"] == "Акаунт оновлено."
    api.post("/api/auth/logout")

    old = api.post("/api/auth/login", json={"login": "boss", "password": "adminpass1"})
    assert old.status_code == 400
    new = api.post("/api/auth/login", json={"login": "boss", "password": "brandnew1"})
    assert new.json()["kind"] == "admin"
    db_session.expire_all()
    customer = db_session.query(User).filter_by(login="boss").one()
    assert verify_password("brandnew1", customer.password)
