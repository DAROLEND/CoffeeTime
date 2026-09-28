"""Admin About-section editor."""
from __future__ import annotations

import datetime

import app.routers.admin.about_section as about_section_module
from app.models.cms import SiteSetting
from tests.helpers import login_admin


def test_about_section_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.get("/api/admin/about-section").status_code == 403


def test_about_section_seeds_defaults(api, db_session):
    login_admin(api, db_session)
    data = api.get("/api/admin/about-section").json()
    assert data["about_title"] == "Місце, де час зупиняється"
    assert db_session.get(SiteSetting, "about_title") is not None


def test_about_section_years_open(api, db_session):
    login_admin(api, db_session)
    db_session.add(SiteSetting(key="about_founded_year", value="2016"))
    db_session.commit()
    assert api.get("/api/admin/about-section").json()["years_open"] == datetime.date.today().year - 2016


def test_about_section_updates_fields(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/about-section", data={
        "about_title": "Новий заголовок", "about_text": "Новий текст",
        "about_founded_year": "2020", "about_menu_count": "80", "about_rating": "4.9",
    })
    assert resp.json()["about_title"] == "Новий заголовок"
    db_session.expire_all()
    assert db_session.get(SiteSetting, "about_title").value == "Новий заголовок"
    assert db_session.get(SiteSetting, "about_rating").value == "4.9"
    assert api.get("/api/about").json()["title"] == "Новий заголовок"  # public side sees it


def test_about_section_photo_upload(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(about_section_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/about-section",
        data={"about_title": "T", "about_text": "", "about_founded_year": "2016", "about_menu_count": "50", "about_rating": "4.8"},
        files={"about_photo": ("photo.png", b"x" * 50, "image/png")},
    )
    assert resp.json()["about_photo"] == "/static/images/main/about-photo.png"
    db_session.expire_all()
    photo = db_session.get(SiteSetting, "about_photo")
    assert photo.value == "static/images/main/about-photo.png"
    assert (tmp_path / photo.value).exists()


def test_about_section_save_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.post("/api/admin/about-section", data={"about_title": "x"}).status_code == 403
