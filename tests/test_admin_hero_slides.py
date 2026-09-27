"""Admin hero-slider management endpoints."""
from __future__ import annotations

import app.routers.admin.hero_slides as hero_slides_module
from app.models.cms import HeroSlide
from tests.helpers import login_admin


def test_hero_slides_require_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.get("/api/admin/hero-slides").status_code == 403


def test_hero_slides_seed_defaults_when_empty(api, db_session):
    login_admin(api, db_session)
    slides = api.get("/api/admin/hero-slides").json()
    assert db_session.query(HeroSlide).count() == 3
    assert slides[0]["title"].startswith("Кожен ковток")


def test_hero_slides_list_existing_without_reseeding(api, db_session):
    login_admin(api, db_session)
    db_session.add(HeroSlide(image="static/images/slides/x.jpg", title="Існуючий слайд", subtitle="Sub", sort_order=0))
    db_session.commit()
    slides = api.get("/api/admin/hero-slides").json()
    assert [s["title"] for s in slides] == ["Існуючий слайд"]
    assert slides[0]["image"] == "/static/images/slides/x.jpg"
    assert db_session.query(HeroSlide).count() == 1


def test_add_slide_requires_title(api, db_session):
    login_admin(api, db_session)
    resp = api.post("/api/admin/hero-slides", data={"title": ""})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Заголовок обовʼязковий."


def test_add_slide_requires_image(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post("/api/admin/hero-slides", data={"title": "Новий"})
    assert resp.json()["detail"] == "Оберіть зображення."
    assert db_session.query(HeroSlide).filter_by(title="Новий").count() == 0


def test_add_slide_with_file_upload(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/hero-slides",
        data={"label": "Лейбл", "title": "Мій слайд", "subtitle": "Підзаголовок"},
        files={"image": ("hero.jpg", b"x" * 100, "image/jpeg")},
    )
    assert resp.status_code == 201
    created = db_session.query(HeroSlide).filter_by(title="Мій слайд").one()
    assert created.label == "Лейбл"
    assert (tmp_path / created.image).exists()


def test_add_slide_with_cropped_base64(api, db_session, monkeypatch, tmp_path):
    import base64
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    b64 = "data:image/png;base64," + base64.b64encode(b"x" * 150).decode()
    resp = api.post("/api/admin/hero-slides", data={"title": "Кроп", "image_b64": b64})
    assert resp.json()["image"].endswith(".png")


def test_add_slide_rejects_oversized_file(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(hero_slides_module, "MAX_UPLOAD_SIZE", 10)
    login_admin(api, db_session)
    resp = api.post("/api/admin/hero-slides", data={"title": "Завеликий"}, files={"image": ("hero.jpg", b"x" * 100, "image/jpeg")})
    assert "занадто великий" in resp.json()["detail"]
    assert db_session.query(HeroSlide).filter_by(title="Завеликий").count() == 0


def test_edit_slide_updates_text_without_touching_image(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    slide = HeroSlide(image="static/images/slides/orig.jpg", title="Старий", subtitle="Old", sort_order=0)
    db_session.add(slide)
    db_session.commit()
    api.post(f"/api/admin/hero-slides/{slide.id}", data={"title": "Новий заголовок", "subtitle": "New"})
    db_session.expire_all()
    updated = db_session.get(HeroSlide, slide.id)
    assert updated.title == "Новий заголовок"
    assert updated.image == "static/images/slides/orig.jpg"


def test_edit_slide_requires_title(api, db_session):
    login_admin(api, db_session)
    slide = HeroSlide(image="x.jpg", title="Незмінний", subtitle="", sort_order=0)
    db_session.add(slide)
    db_session.commit()
    assert api.post(f"/api/admin/hero-slides/{slide.id}", data={"title": ""}).status_code == 400
    db_session.expire_all()
    assert db_session.get(HeroSlide, slide.id).title == "Незмінний"


def test_delete_slide(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    slides_dir = tmp_path / "static" / "images" / "slides"
    slides_dir.mkdir(parents=True)
    (slides_dir / "todelete.jpg").write_bytes(b"x")
    slide = HeroSlide(image="static/images/slides/todelete.jpg", title="Видалити", subtitle="", sort_order=0)
    db_session.add(slide)
    db_session.commit()
    slide_id = slide.id
    api.delete(f"/api/admin/hero-slides/{slide_id}")
    assert db_session.get(HeroSlide, slide_id) is None
    assert not (slides_dir / "todelete.jpg").exists()


def test_toggle_slide(api, db_session):
    login_admin(api, db_session)
    slide = HeroSlide(image="x.jpg", title="T", subtitle="", sort_order=0, active=True)
    db_session.add(slide)
    db_session.commit()
    assert api.post(f"/api/admin/hero-slides/{slide.id}/toggle").json() == {"ok": True, "active": False}
    db_session.expire_all()
    assert db_session.get(HeroSlide, slide.id).active is False


def test_move_slide_renumbers_all(api, db_session):
    login_admin(api, db_session)
    s1 = HeroSlide(image="a.jpg", title="A", subtitle="", sort_order=0)
    s2 = HeroSlide(image="b.jpg", title="B", subtitle="", sort_order=1)
    s3 = HeroSlide(image="c.jpg", title="C", subtitle="", sort_order=2)
    db_session.add_all([s1, s2, s3])
    db_session.commit()
    assert api.post(f"/api/admin/hero-slides/{s2.id}/move", json={"dir": "up"}).json()["success"] is True
    db_session.expire_all()
    ordered = db_session.query(HeroSlide).order_by(HeroSlide.sort_order.asc()).all()
    assert [s.title for s in ordered] == ["B", "A", "C"]
    assert [s.sort_order for s in ordered] == [0, 1, 2]


def test_move_slide_at_boundary_is_noop(api, db_session):
    login_admin(api, db_session)
    s1 = HeroSlide(image="a.jpg", title="A", subtitle="", sort_order=0)
    db_session.add(s1)
    db_session.commit()
    assert api.post(f"/api/admin/hero-slides/{s1.id}/move", json={"dir": "up"}).json()["success"] is True
    db_session.expire_all()
    assert db_session.get(HeroSlide, s1.id).sort_order == 0


def test_hero_slides_action_requires_content_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    assert api.delete("/api/admin/hero-slides/1").status_code == 403
