"""Phase 8 (6/n) verification: admin/hero_slides.php port. No permission
fix needed here — PHP already had require_perm('content')."""
from __future__ import annotations

import re

import app.routers.admin.hero_slides as hero_slides_module
from app.models.auth import AdminUser
from app.models.cms import HeroSlide
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_hero_slides_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/hero-slides", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_hero_slides_seeds_defaults_when_empty(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/hero-slides")
    assert resp.status_code == 200
    assert db_session.query(HeroSlide).count() == 3
    assert "Кожен ковток" in resp.text


def test_hero_slides_lists_existing_without_reseeding(client, db_session):
    _login_admin(client, db_session)
    db_session.add(HeroSlide(image="static/images/slides/x.jpg", title="Існуючий слайд", subtitle="Sub", sort_order=0))
    db_session.commit()

    resp = client.get("/admin/hero-slides")
    assert "Існуючий слайд" in resp.text
    assert db_session.query(HeroSlide).count() == 1


def test_add_slide_requires_title(client, db_session):
    """Table starts empty, so the self-healing seed (see
    test_hero_slides_seeds_defaults_when_empty) fires on this very POST
    too, exactly like PHP running it unconditionally at the top of the
    file — the failed add contributes no 4th row on top of those 3."""
    _login_admin(client, db_session)
    resp = client.post("/admin/hero-slides", data={"action": "add", "title": ""}, follow_redirects=True)
    assert "Заголовок обовʼязковий" in resp.text
    assert db_session.query(HeroSlide).count() == 3


def test_add_slide_requires_image(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    resp = client.post("/admin/hero-slides", data={"action": "add", "title": "Новий"}, follow_redirects=True)
    assert "Оберіть зображення" in resp.text
    assert db_session.query(HeroSlide).filter_by(title="Новий").count() == 0


def test_add_slide_with_file_upload(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/hero-slides",
        data={"action": "add", "label": "Лейбл", "title": "Мій слайд", "subtitle": "Підзаголовок"},
        files={"image": ("hero.jpg", b"x" * 100, "image/jpeg")},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    created = db_session.query(HeroSlide).filter_by(title="Мій слайд").one()
    assert created.label == "Лейбл"
    assert (tmp_path / created.image).exists()


def test_add_slide_rejects_oversized_file(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(hero_slides_module, "MAX_UPLOAD_SIZE", 10)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/hero-slides",
        data={"action": "add", "title": "Завеликий"},
        files={"image": ("hero.jpg", b"x" * 100, "image/jpeg")},
        follow_redirects=True,
    )
    assert "занадто великий" in resp.text
    assert db_session.query(HeroSlide).filter_by(title="Завеликий").count() == 0


def test_edit_slide_updates_text_without_touching_image(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    slide = HeroSlide(image="static/images/slides/orig.jpg", title="Старий", subtitle="Old", sort_order=0)
    db_session.add(slide)
    db_session.commit()
    slide_id = slide.id

    client.post("/admin/hero-slides", data={"action": "edit", "id": slide_id, "title": "Новий заголовок", "subtitle": "New"})
    db_session.expire_all()
    updated = db_session.get(HeroSlide, slide_id)
    assert updated.title == "Новий заголовок"
    assert updated.image == "static/images/slides/orig.jpg"


def test_edit_slide_silently_noops_without_title(client, db_session):
    """Preserves an existing PHP quirk: if id or title is falsy, the edit
    branch does nothing at all — not even a flash message."""
    _login_admin(client, db_session)
    slide = HeroSlide(image="x.jpg", title="Незмінний", subtitle="", sort_order=0)
    db_session.add(slide)
    db_session.commit()
    slide_id = slide.id

    resp = client.post("/admin/hero-slides", data={"action": "edit", "id": slide_id, "title": ""}, follow_redirects=True)
    assert "Збережено." not in resp.text
    db_session.expire_all()
    assert db_session.get(HeroSlide, slide_id).title == "Незмінний"


def test_delete_slide(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(hero_slides_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    slides_dir = tmp_path / "static" / "images" / "slides"
    slides_dir.mkdir(parents=True)
    (slides_dir / "todelete.jpg").write_bytes(b"x")
    slide = HeroSlide(image="static/images/slides/todelete.jpg", title="Видалити", subtitle="", sort_order=0)
    db_session.add(slide)
    db_session.commit()
    slide_id = slide.id

    # follow_redirects=False: the auto-followed GET would otherwise see an
    # (now-empty) table and reseed 3 defaults, whose first row can reuse
    # this same autoincrement id in SQLite — a test-harness artifact, not
    # a router bug (see the admin_users tests for the same pattern).
    client.post("/admin/hero-slides", data={"action": "delete", "id": slide_id}, follow_redirects=False)
    assert db_session.get(HeroSlide, slide_id) is None
    assert not (slides_dir / "todelete.jpg").exists()


def test_toggle_slide_ajax(client, db_session):
    _login_admin(client, db_session)
    slide = HeroSlide(image="x.jpg", title="T", subtitle="", sort_order=0, active=True)
    db_session.add(slide)
    db_session.commit()
    slide_id = slide.id

    resp = client.post("/admin/hero-slides", data={"action": "toggle", "id": slide_id, "ajax": "1"})
    assert resp.json() == {"ok": True, "active": 0}
    db_session.expire_all()
    assert db_session.get(HeroSlide, slide_id).active is False


def test_move_slide_renumbers_all(client, db_session):
    _login_admin(client, db_session)
    s1 = HeroSlide(image="a.jpg", title="A", subtitle="", sort_order=0)
    s2 = HeroSlide(image="b.jpg", title="B", subtitle="", sort_order=1)
    s3 = HeroSlide(image="c.jpg", title="C", subtitle="", sort_order=2)
    db_session.add_all([s1, s2, s3])
    db_session.commit()
    s2_id = s2.id

    resp = client.post("/admin/hero-slides", data={"action": "move", "id": s2_id, "dir": "up", "ajax": "1"})
    assert resp.json() == {"ok": True}

    db_session.expire_all()
    ordered = db_session.query(HeroSlide).order_by(HeroSlide.sort_order.asc()).all()
    assert [s.title for s in ordered] == ["B", "A", "C"]
    assert [s.sort_order for s in ordered] == [0, 1, 2]


def test_move_slide_at_boundary_is_noop(client, db_session):
    _login_admin(client, db_session)
    s1 = HeroSlide(image="a.jpg", title="A", subtitle="", sort_order=0)
    db_session.add(s1)
    db_session.commit()

    resp = client.post("/admin/hero-slides", data={"action": "move", "id": s1.id, "dir": "up", "ajax": "1"})
    assert resp.json() == {"ok": True}
    db_session.expire_all()
    assert db_session.get(HeroSlide, s1.id).sort_order == 0


def test_hero_slides_action_requires_content_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.post("/admin/hero-slides", data={"action": "delete", "id": 1}, follow_redirects=False)
    assert resp.status_code == 303
