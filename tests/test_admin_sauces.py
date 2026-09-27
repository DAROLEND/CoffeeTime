"""Admin sauce management endpoints."""
from __future__ import annotations

import app.routers.admin.sauces as sauces_module
from app.models.catalog import Sauce
from tests.helpers import login_admin


def test_sauces_require_products_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["orders_view"]')
    assert api.get("/api/admin/sauces").status_code == 403


def test_sauces_list(api, db_session):
    login_admin(api, db_session)
    db_session.add(Sauce(name="Кетчуп", price=15, active=True, sort_order=1, image=""))
    db_session.commit()
    data = api.get("/api/admin/sauces").json()
    assert data == [{"id": 1, "name": "Кетчуп", "price": 15.0, "image": "", "has_photo": False, "active": True, "sort_order": 1}]


def test_sauces_empty(api, db_session):
    login_admin(api, db_session)
    assert api.get("/api/admin/sauces").json() == []


def test_add_sauce_requires_name(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/sauces", data={"price": "10"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Назва обовʼязкова"
    assert db_session.query(Sauce).count() == 0


def test_add_sauce(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/sauces", data={"name": "Майонез", "price": "20", "sort_order": "2", "active": "true"})
    assert resp.status_code == 201
    created = db_session.get(Sauce, resp.json()["sauce"]["id"])
    assert created.name == "Майонез"
    assert float(created.price) == 20.0
    assert created.active is True
    assert created.sort_order == 2


def test_add_sauce_without_active_flag_is_inactive(api, db_session):
    """Checkbox semantics: absent means unchecked."""
    login_admin(api, db_session)
    resp = api.post("/api/admin/sauces", data={"name": "Гострий", "price": "10"})
    assert db_session.get(Sauce, resp.json()["sauce"]["id"]).active is False


def test_update_sauce(api, db_session):
    login_admin(api, db_session)
    sauce = Sauce(name="Стара назва", price=10, active=True, sort_order=0, image="")
    db_session.add(sauce)
    db_session.commit()
    resp = api.post(f"/api/admin/sauces/{sauce.id}", data={"name": "Нова назва", "price": "25", "sort_order": "5"})
    assert resp.json()["success"] is True
    db_session.expire_all()
    updated = db_session.get(Sauce, sauce.id)
    assert updated.name == "Нова назва"
    assert float(updated.price) == 25.0
    assert updated.active is False  # no "active" field sent -> unchecked


def test_update_missing_sauce_is_404(api, db_session):
    login_admin(api, db_session)
    assert api.post("/api/admin/sauces/99", data={"name": "X"}).status_code == 404


def test_toggle_sauce(api, db_session):
    login_admin(api, db_session)
    sauce = Sauce(name="Соус", price=10, active=True, sort_order=0, image="")
    db_session.add(sauce)
    db_session.commit()
    assert api.patch(f"/api/admin/sauces/{sauce.id}/active", json={"active": False}).json()["success"] is True
    db_session.expire_all()
    assert db_session.get(Sauce, sauce.id).active is False


def test_delete_sauce(api, db_session):
    login_admin(api, db_session)
    sauce = Sauce(name="Соус", price=10, active=True, sort_order=0, image="")
    db_session.add(sauce)
    db_session.commit()
    sauce_id = sauce.id
    assert api.delete(f"/api/admin/sauces/{sauce_id}").json()["success"] is True
    assert db_session.get(Sauce, sauce_id) is None


def test_add_sauce_with_image_upload(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(sauces_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/sauces", data={"name": "Барбекю", "price": "18"},
        files={"image": ("sauce.png", b"\x89PNG" + b"0" * 50, "image/png")},
    )
    sauce = resp.json()["sauce"]
    assert sauce["has_photo"] is True
    assert sauce["image"].startswith("/static/images/menu_items/sauces/") and sauce["image"].endswith(".png")
    assert (tmp_path / sauce["image"].lstrip("/")).exists()


def test_add_sauce_ignores_oversized_image(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(sauces_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sauces_module, "MAX_UPLOAD_SIZE", 10)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/sauces", data={"name": "Завеликий", "price": "18"},
        files={"image": ("sauce.png", b"0" * 100, "image/png")},
    )
    assert resp.status_code == 201
    assert resp.json()["sauce"]["image"] == ""  # oversized upload silently ignored
