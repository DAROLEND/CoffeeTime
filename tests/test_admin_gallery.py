"""Phase 8 (4/n) verification: admin/admin_gallery.php port. No permission
fix needed here — PHP already had require_perm('content')."""
from __future__ import annotations

import re

import app.routers.admin.gallery as gallery_module
from app.models.auth import AdminUser
from app.models.cms import Gallery
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_gallery_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/gallery", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_gallery_empty_state(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/gallery")
    assert "Галерея порожня" in resp.text


def test_gallery_lists_photos_and_counts(client, db_session):
    _login_admin(client, db_session)
    db_session.add_all([
        Gallery(filename="a.jpg", alt="A", category="food"),
        Gallery(filename="b.jpg", alt="B", category="interior"),
    ])
    db_session.commit()

    resp = client.get("/admin/gallery")
    assert resp.status_code == 200
    assert "/static/images/gallery/a.jpg" in resp.text
    assert "2 фото" in resp.text

    resp = client.get("/admin/gallery?cat=food")
    assert "a.jpg" in resp.text
    assert "b.jpg" not in resp.text


def test_gallery_upload_creates_rows(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/gallery",
        data={"category": "interior", "alt": "Затишний куточок"},
        files=[("photos[]", ("photo1.jpg", b"x" * 50, "image/jpeg"))],
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/gallery?uploaded=1"

    created = db_session.query(Gallery).one()
    assert created.alt == "Затишний куточок"
    assert created.category.value == "interior"
    assert (tmp_path / "static" / "images" / "gallery" / created.filename).exists()


def test_gallery_upload_rejects_bad_extension(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/gallery",
        data={"category": "food"},
        files=[("photos[]", ("virus.exe", b"x" * 50, "application/octet-stream"))],
    )
    assert resp.status_code == 200
    assert "непідтримуваний формат" in resp.text
    assert db_session.query(Gallery).count() == 0


def test_gallery_delete_removes_row_and_file(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    gdir = tmp_path / "static" / "images" / "gallery"
    gdir.mkdir(parents=True)
    (gdir / "todelete.jpg").write_bytes(b"x")
    photo = Gallery(filename="todelete.jpg", alt="", category="food")
    db_session.add(photo)
    db_session.commit()
    photo_id = photo.id

    resp = client.post(
        "/admin/gallery",
        headers={"X-Requested-With": "XMLHttpRequest"},
        json={"action": "delete", "id": photo_id},
    )
    assert resp.json() == {"success": True}
    assert db_session.get(Gallery, photo_id) is None
    assert not (gdir / "todelete.jpg").exists()


def test_gallery_set_category(client, db_session):
    _login_admin(client, db_session)
    photo = Gallery(filename="x.jpg", alt="", category="food")
    db_session.add(photo)
    db_session.commit()
    photo_id = photo.id

    resp = client.post(
        "/admin/gallery",
        headers={"X-Requested-With": "XMLHttpRequest"},
        json={"action": "set_category", "id": photo_id, "category": "interior"},
    )
    assert resp.json() == {"success": True}
    db_session.expire_all()
    assert db_session.get(Gallery, photo_id).category.value == "interior"


def test_gallery_set_alt(client, db_session):
    _login_admin(client, db_session)
    photo = Gallery(filename="x.jpg", alt="", category="food")
    db_session.add(photo)
    db_session.commit()
    photo_id = photo.id

    resp = client.post(
        "/admin/gallery",
        headers={"X-Requested-With": "XMLHttpRequest"},
        json={"action": "set_alt", "id": photo_id, "alt": "  Новий підпис  "},
    )
    assert resp.json() == {"success": True}
    db_session.expire_all()
    assert db_session.get(Gallery, photo_id).alt == "Новий підпис"


def test_gallery_delete_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.post(
        "/admin/gallery",
        headers={"X-Requested-With": "XMLHttpRequest"},
        json={"action": "delete", "id": 1},
        follow_redirects=False,
    )
    assert resp.status_code == 303
