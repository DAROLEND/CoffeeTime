"""Admin dessert-banner editor."""
from __future__ import annotations

import app.routers.admin.dessert_banner as dessert_banner_module
from app.models.catalog import DessertItem
from app.models.cms import SiteSetting
from tests.helpers import login_admin


def test_dessert_banner_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.get("/api/admin/dessert-banner").status_code == 403


def test_dessert_banner_with_custom_image(api, db_session):
    login_admin(api, db_session)
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/main/dessert-banner.jpg"))
    db_session.commit()
    data = api.get("/api/admin/dessert-banner").json()
    assert data["has_custom_image"] is True
    assert data["image"].startswith("/static/images/main/dessert-banner.jpg?v=")
    assert data["random_image"] is None


def test_dessert_banner_without_image_previews_a_random_dessert(api, db_session):
    login_admin(api, db_session)
    db_session.add(DessertItem(name="Тарт", image="static/images/menu_items/desserts/tart.webp", price=90))
    db_session.commit()
    data = api.get("/api/admin/dessert-banner").json()
    assert data["has_custom_image"] is False
    assert data["random_image"] == "/static/images/menu_items/desserts/tart.webp"


def test_dessert_banner_updates_text_fields(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/dessert-banner", data={
        "dessert_banner_label": "Нове", "dessert_banner_title": "Новий десерт",
        "dessert_banner_desc": "опис", "dessert_banner_btn": "Дивитись",
    })
    assert resp.json()["dessert_banner_title"] == "Новий десерт"
    db_session.expire_all()
    assert db_session.get(SiteSetting, "dessert_banner_title").value == "Новий десерт"


def test_dessert_banner_photo_upload(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(dessert_banner_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    api.post(
        "/api/admin/dessert-banner",
        data={"dessert_banner_label": "L", "dessert_banner_title": "T", "dessert_banner_desc": "", "dessert_banner_btn": "B"},
        files={"dessert_banner_image": ("banner.png", b"x" * 50, "image/png")},
    )
    db_session.expire_all()
    image = db_session.get(SiteSetting, "dessert_banner_image")
    assert image.value == "static/images/main/dessert-banner.png"
    assert (tmp_path / image.value).exists()


def test_dessert_banner_clear_image(api, db_session):
    login_admin(api, db_session)
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/main/dessert-banner.jpg"))
    db_session.commit()
    resp = api.post("/api/admin/dessert-banner", data={
        "dessert_banner_label": "L", "dessert_banner_title": "T", "dessert_banner_desc": "",
        "dessert_banner_btn": "B", "clear_image": "true",
    })
    assert resp.json()["has_custom_image"] is False
    db_session.expire_all()
    assert db_session.get(SiteSetting, "dessert_banner_image").value == ""


def test_dessert_banner_save_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.post("/api/admin/dessert-banner", data={"dessert_banner_title": "x"}).status_code == 403
