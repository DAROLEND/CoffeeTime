"""Tests for the admin dessert-banner editor."""
from __future__ import annotations

import re

import app.routers.admin.dessert_banner as dessert_banner_module
from app.models.auth import AdminUser
from app.models.cms import SiteSetting
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_dessert_banner_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/dessert-banner", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


# The "no custom image" state falls back to a random dessert photo
# (`ORDER BY RANDOM()`, matching the identical query in
# app/routers/public/pages.py) and is deliberately left uncovered —
# there's no stable value to assert against. Every test here seeds a
# dessert_banner_image setting to take the deterministic path instead,
# same as tests/test_public_pages_smoke.py does for the public banner.


def test_dessert_banner_with_custom_image_hides_random_hint(client, db_session):
    _login_admin(client, db_session)
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/main/dessert-banner.jpg"))
    db_session.commit()

    resp = client.get("/admin/dessert-banner")
    assert "рандомний десерт із меню" not in resp.text
    assert "Поточне фото" in resp.text


def test_dessert_banner_updates_text_fields(client, db_session):
    _login_admin(client, db_session)
    resp = client.post("/admin/dessert-banner", data={
        "dessert_banner_label": "Нове", "dessert_banner_title": "Новий десерт",
        "dessert_banner_desc": "опис", "dessert_banner_btn": "Дивитись",
    }, follow_redirects=False)
    assert resp.status_code == 303
    db_session.expire_all()
    assert db_session.get(SiteSetting, "dessert_banner_title").value == "Новий десерт"


def test_dessert_banner_photo_upload(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(dessert_banner_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/dessert-banner",
        data={"dessert_banner_label": "L", "dessert_banner_title": "T", "dessert_banner_desc": "", "dessert_banner_btn": "B"},
        files={"dessert_banner_image": ("banner.png", b"x" * 50, "image/png")},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    db_session.expire_all()
    image = db_session.get(SiteSetting, "dessert_banner_image")
    assert image.value == "static/images/main/dessert-banner.png"
    assert (tmp_path / image.value).exists()


def test_dessert_banner_clear_image(client, db_session):
    _login_admin(client, db_session)
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/main/dessert-banner.jpg"))
    db_session.commit()

    # follow_redirects=False: clearing the image means the auto-followed
    # GET would have no custom image and hit the RAND() branch, which
    # SQLite can't run (see the module-level note above).
    client.post("/admin/dessert-banner", data={
        "dessert_banner_label": "L", "dessert_banner_title": "T", "dessert_banner_desc": "",
        "dessert_banner_btn": "B", "clear_image": "1",
    }, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(SiteSetting, "dessert_banner_image").value == ""


def test_dessert_banner_action_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.post("/admin/dessert-banner", data={"dessert_banner_title": "x"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"
