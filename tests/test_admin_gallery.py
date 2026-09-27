"""Admin gallery management endpoints."""
from __future__ import annotations

import app.routers.admin.gallery as gallery_module
from app.models.cms import Gallery
from tests.helpers import login_admin


def test_gallery_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.get("/api/admin/gallery").status_code == 403


def test_gallery_empty(api, db_session):
    login_admin(api, db_session)
    data = api.get("/api/admin/gallery").json()
    assert data["images"] == [] and data["counts"] == {"all": 0, "food": 0, "interior": 0}


def test_gallery_lists_photos_and_counts(api, db_session):
    login_admin(api, db_session)
    db_session.add_all([
        Gallery(filename="a.jpg", alt="A", category="food"),
        Gallery(filename="b.jpg", alt="B", category="interior"),
    ])
    db_session.commit()

    data = api.get("/api/admin/gallery").json()
    assert {i["url"] for i in data["images"]} == {"/static/images/gallery/a.jpg", "/static/images/gallery/b.jpg"}
    assert data["counts"] == {"all": 2, "food": 1, "interior": 1}

    data = api.get("/api/admin/gallery?cat=food").json()
    assert [i["url"] for i in data["images"]] == ["/static/images/gallery/a.jpg"]
    assert data["filter"] == "food"


def test_gallery_upload_creates_rows(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/gallery",
        data={"category": "interior", "alt": "Затишний куточок"},
        files=[("photos", ("photo1.jpg", b"x" * 50, "image/jpeg"))],
    )
    assert resp.json() == {"uploaded": 1, "errors": []}
    created = db_session.query(Gallery).one()
    assert created.alt == "Затишний куточок"
    assert created.category.value == "interior"
    assert (tmp_path / "static" / "images" / "gallery" / created.filename).exists()


def test_gallery_upload_multiple_uses_file_name_as_alt(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/gallery", data={"category": "food"},
        files=[("photos", ("tiramisu.jpg", b"x" * 50, "image/jpeg")), ("photos", ("latte.png", b"x" * 50, "image/png"))],
    )
    assert resp.json()["uploaded"] == 2
    assert sorted(g.alt for g in db_session.query(Gallery).all()) == ["latte", "tiramisu"]


def test_gallery_upload_rejects_bad_extension(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post("/api/admin/gallery", data={"category": "food"},
                    files=[("photos", ("virus.exe", b"x" * 50, "application/octet-stream"))])
    assert resp.json()["uploaded"] == 0
    assert "непідтримуваний формат" in resp.json()["errors"][0]
    assert db_session.query(Gallery).count() == 0


def test_gallery_delete_removes_row_and_file(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(gallery_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    gdir = tmp_path / "static" / "images" / "gallery"
    gdir.mkdir(parents=True)
    (gdir / "todelete.jpg").write_bytes(b"x")
    photo = Gallery(filename="todelete.jpg", alt="", category="food")
    db_session.add(photo)
    db_session.commit()
    photo_id = photo.id

    assert api.delete(f"/api/admin/gallery/{photo_id}").json()["success"] is True
    assert db_session.get(Gallery, photo_id) is None
    assert not (gdir / "todelete.jpg").exists()


def test_gallery_set_category_and_alt(api, db_session):
    login_admin(api, db_session)
    photo = Gallery(filename="x.jpg", alt="", category="food")
    db_session.add(photo)
    db_session.commit()

    assert api.patch(f"/api/admin/gallery/{photo.id}", json={"category": "interior"}).json()["success"] is True
    assert api.patch(f"/api/admin/gallery/{photo.id}", json={"alt": "  Новий підпис  "}).json()["success"] is True
    db_session.expire_all()
    updated = db_session.get(Gallery, photo.id)
    assert updated.category.value == "interior"
    assert updated.alt == "Новий підпис"
    assert api.patch(f"/api/admin/gallery/{photo.id}", json={"category": "cats"}).status_code == 422


def test_gallery_delete_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.delete("/api/admin/gallery/1").status_code == 403
