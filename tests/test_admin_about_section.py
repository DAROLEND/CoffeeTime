"""Tests for the admin About-section editor."""
from __future__ import annotations

import re

import app.routers.admin.about_section as about_section_module
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


def test_about_section_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/about-section", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_about_section_seeds_defaults(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/about-section")
    assert resp.status_code == 200
    assert "Місце, де час зупиняється" in resp.text
    assert db_session.get(SiteSetting, "about_title") is not None


def test_about_section_shows_years_open(client, db_session):
    import datetime
    _login_admin(client, db_session)
    db_session.add(SiteSetting(key="about_founded_year", value="2016"))
    db_session.commit()
    resp = client.get("/admin/about-section")
    expected_years = datetime.date.today().year - 2016
    assert f"{expected_years} р." in resp.text


def test_about_section_updates_fields(client, db_session):
    _login_admin(client, db_session)
    resp = client.post("/admin/about-section", data={
        "about_title": "Новий заголовок", "about_text": "Новий текст",
        "about_founded_year": "2020", "about_menu_count": "80", "about_rating": "4.9",
    }, follow_redirects=False)
    assert resp.status_code == 303

    db_session.expire_all()
    assert db_session.get(SiteSetting, "about_title").value == "Новий заголовок"
    assert db_session.get(SiteSetting, "about_rating").value == "4.9"


def test_about_section_photo_upload(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(about_section_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/about-section",
        data={"about_title": "T", "about_text": "", "about_founded_year": "2016", "about_menu_count": "50", "about_rating": "4.8"},
        files={"about_photo": ("photo.png", b"x" * 50, "image/png")},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    db_session.expire_all()
    photo = db_session.get(SiteSetting, "about_photo")
    assert photo.value == "static/images/main/about-photo.png"
    assert (tmp_path / photo.value).exists()


def test_about_section_action_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.post("/admin/about-section", data={"about_title": "x"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"
