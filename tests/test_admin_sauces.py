"""Tests for the admin sauce management endpoints."""
from __future__ import annotations

import re

import app.routers.admin.sauces as sauces_module
from app.models.auth import AdminUser
from app.models.catalog import Sauce
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_sauces_page_requires_products_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["orders_view"]')
    resp = client.get("/admin/sauces", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_sauces_page_lists_sauces(client, db_session):
    _login_admin(client, db_session)
    db_session.add(Sauce(name="Кетчуп", price=15, active=True, sort_order=1, image=""))
    db_session.commit()

    resp = client.get("/admin/sauces")
    assert resp.status_code == 200
    assert "Кетчуп" in resp.text
    assert "15 ₴" in resp.text


def test_sauces_page_empty_state(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/sauces")
    assert "Соусів ще немає" in resp.text


def test_add_sauce_requires_name(client, db_session):
    _login_admin(client, db_session)
    resp = client.post("/admin/sauces", data={"action": "add", "price": "10"})
    assert resp.json() == {"success": False, "error": "Назва обовʼязкова"}
    assert db_session.query(Sauce).count() == 0


def test_add_sauce_creates_row(client, db_session):
    _login_admin(client, db_session)
    resp = client.post("/admin/sauces", data={"action": "add", "name": "Майонез", "price": "20", "sort_order": "2", "active": "1"})
    data = resp.json()
    assert data["success"] is True
    created = db_session.get(Sauce, data["id"])
    assert created.name == "Майонез"
    assert float(created.price) == 20.0
    assert created.active is True
    assert created.sort_order == 2


def test_add_sauce_without_active_flag_is_inactive(client, db_session):
    """Checkbox semantics: the field is only present when checked."""
    _login_admin(client, db_session)
    resp = client.post("/admin/sauces", data={"action": "add", "name": "Гострий", "price": "10"})
    data = resp.json()
    created = db_session.get(Sauce, data["id"])
    assert created.active is False


def test_update_sauce(client, db_session):
    _login_admin(client, db_session)
    sauce = Sauce(name="Стара назва", price=10, active=True, sort_order=0, image="")
    db_session.add(sauce)
    db_session.commit()
    sauce_id = sauce.id

    resp = client.post("/admin/sauces", data={"action": "update", "id": sauce_id, "name": "Нова назва", "price": "25", "sort_order": "5"})
    assert resp.json() == {"success": True}
    db_session.expire_all()
    updated = db_session.get(Sauce, sauce_id)
    assert updated.name == "Нова назва"
    assert float(updated.price) == 25.0
    assert updated.active is False  # no "active" field sent -> unchecked


def test_toggle_sauce(client, db_session):
    _login_admin(client, db_session)
    sauce = Sauce(name="Соус", price=10, active=True, sort_order=0, image="")
    db_session.add(sauce)
    db_session.commit()
    sauce_id = sauce.id

    resp = client.post("/admin/sauces", data={"action": "toggle", "id": sauce_id, "active": "0"})
    assert resp.json() == {"success": True}
    db_session.expire_all()
    assert db_session.get(Sauce, sauce_id).active is False


def test_delete_sauce(client, db_session):
    _login_admin(client, db_session)
    sauce = Sauce(name="Соус", price=10, active=True, sort_order=0, image="")
    db_session.add(sauce)
    db_session.commit()
    sauce_id = sauce.id

    resp = client.post("/admin/sauces", data={"action": "delete", "id": sauce_id})
    assert resp.json() == {"success": True}
    assert db_session.get(Sauce, sauce_id) is None


def test_add_sauce_with_image_upload(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(sauces_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/sauces",
        data={"action": "add", "name": "Барбекю", "price": "18"},
        files={"sauce_image": ("sauce.png", b"\x89PNG" + b"0" * 50, "image/png")},
    )
    data = resp.json()
    assert data["success"] is True
    assert data["image"].endswith(".png")
    assert (tmp_path / data["image"]).exists()


def test_add_sauce_rejects_oversized_image(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(sauces_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sauces_module, "MAX_UPLOAD_SIZE", 10)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/sauces",
        data={"action": "add", "name": "Завеликий", "price": "18"},
        files={"sauce_image": ("sauce.png", b"0" * 100, "image/png")},
    )
    data = resp.json()
    assert data["success"] is True
    assert data["image"] == ""  # oversized upload silently ignored


def test_unknown_action_returns_error(client, db_session):
    _login_admin(client, db_session)
    resp = client.post("/admin/sauces", data={"action": "bogus"})
    assert resp.json() == {"success": False, "error": "Unknown action"}
