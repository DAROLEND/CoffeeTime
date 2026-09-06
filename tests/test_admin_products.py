"""Phase 8 (2/n) verification: admin/manage_items.php + add_item.php +
edit_item.php + ajax_delete_item.php port. Confirmed fix applied:
require_perm('products') now guards every route here — PHP only checked
it on the listing page, so any logged-in staff account (regardless of
assigned permissions) could add/edit/delete products by hitting
add_item.php/edit_item.php/ajax_delete_item.php directly."""
from __future__ import annotations

import base64
import json
import re

import app.routers.admin.products as products_module
from app.models.auth import AdminUser
from app.models.catalog import CakeItem, CoffeeItem, IceCreamItem, SushiSet
from app.services.auth import hash_password

_FAKE_B64 = "data:image/jpeg;base64," + base64.b64encode(b"x" * 150).decode()


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_manage_items_requires_products_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["orders_view"]')
    resp = client.get("/admin/manage-items", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_add_item_direct_url_requires_products_permission(client, db_session):
    """Confirmed fix: PHP's add_item.php checked only auth_check.php (any
    logged-in admin), not require_perm('products')."""
    _login_admin(client, db_session, role="staff", perms='["orders_view"]')
    resp = client.post("/admin/manage-items/add?category=coffee_items", data={"name": "X", "price": "10"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_manage_items_list_shows_items_and_tab_counts(client, db_session):
    _login_admin(client, db_session)
    db_session.add(CoffeeItem(name="Латте", image="static/images/menu_items/default.jpg", price=60))
    db_session.commit()

    resp = client.get("/admin/manage-items")
    assert resp.status_code == 200
    assert "Латте" in resp.text
    assert "60.00" in resp.text

    resp = client.get("/admin/manage-items?category=coffee_items")
    assert "Латте" in resp.text


def test_add_item_creates_product(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/manage-items/add?category=coffee_items",
        data={"name": "Еспресо", "price": "35", "description": "Міцна кава", "image_b64": _FAKE_B64},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/manage-items?category=coffee_items&saved=1"

    created = db_session.query(CoffeeItem).filter_by(name="Еспресо").one()
    assert float(created.price) == 35.0
    assert created.image.startswith("static/images/menu_items/coffee/")
    assert (tmp_path / created.image).exists()


def test_add_item_with_raw_file_upload(client, db_session, monkeypatch, tmp_path):
    """Exercises the $_FILES-style branch (real multipart file, not the
    cropper's base64 field)."""
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/manage-items/add?category=coffee_items",
        data={"name": "Раф", "price": "70"},
        files={"image": ("photo.png", b"\x89PNG" + b"0" * 50, "image/png")},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    created = db_session.query(CoffeeItem).filter_by(name="Раф").one()
    assert created.image.endswith(".png")
    assert (tmp_path / created.image).exists()


def test_add_item_validation_errors_redisplay_form(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post("/admin/manage-items/add?category=coffee_items", data={"name": "", "price": "0"})
    assert resp.status_code == 200
    assert "Введіть назву товару." in resp.text
    assert "Ціна має бути більша за 0." in resp.text
    assert "Оберіть зображення для завантаження." in resp.text
    assert db_session.query(CoffeeItem).count() == 0


def test_add_cake_item_uses_price_per_kg(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/manage-items/add?category=cake_items",
        data={"name": "Медовик", "price_per_kg": "1200", "min_weight": "1.5", "image_b64": _FAKE_B64},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    created = db_session.query(CakeItem).filter_by(name="Медовик").one()
    assert float(created.price_per_kg) == 1200.0
    assert float(created.min_weight) == 1.5


def test_add_ice_cream_item_builds_variant_options(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)

    resp = client.post(
        "/admin/manage-items/add?category=ice_cream_items",
        data={"name": "Ванільне", "price": "45", "scoop_diff_2": "20", "scoop_diff_3": "40", "image_b64": _FAKE_B64},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    created = db_session.query(IceCreamItem).filter_by(name="Ванільне").one()
    vo = json.loads(created.variant_options)
    assert vo["type"] == "scoops"
    assert vo["options"][1]["price_diff"] == 20.0
    assert vo["options"][2]["price_diff"] == 40.0


def test_edit_item_updates_fields(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    item = CoffeeItem(name="Капучино", image="static/images/menu_items/default.jpg", price=50)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    resp = client.post(
        f"/admin/manage-items/edit?category=coffee_items&id={item_id}",
        data={"name": "Капучино Гранде", "price": "65", "description": "Більша порція"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    db_session.expire_all()
    updated = db_session.get(CoffeeItem, item_id)
    assert updated.name == "Капучино Гранде"
    assert float(updated.price) == 65.0


def test_edit_item_remove_image(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    img_dir = tmp_path / "static" / "images" / "menu_items" / "coffee"
    img_dir.mkdir(parents=True)
    img_file = img_dir / "existing.jpg"
    img_file.write_bytes(b"fake")
    item = CoffeeItem(name="Мокко", image="static/images/menu_items/coffee/existing.jpg", price=55)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    client.post(
        f"/admin/manage-items/edit?category=coffee_items&id={item_id}",
        data={"name": "Мокко", "price": "55", "remove_image": "1"},
    )
    db_session.expire_all()
    updated = db_session.get(CoffeeItem, item_id)
    assert updated.image == ""
    assert not img_file.exists()


def test_edit_sushi_set_updates_pieces_count(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    item = SushiSet(name="Філадельфія сет", image="static/images/menu_items/default.jpg", price=350, pieces_count=8)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    client.post(
        f"/admin/manage-items/edit?category=sushi_sets&id={item_id}",
        data={"name": "Філадельфія сет", "price": "350", "pieces_count": "12"},
    )
    db_session.expire_all()
    assert db_session.get(SushiSet, item_id).pieces_count == 12


def test_ajax_delete_removes_product_and_image(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    _login_admin(client, db_session)
    img_dir = tmp_path / "static" / "images" / "menu_items" / "coffee"
    img_dir.mkdir(parents=True)
    img_file = img_dir / "todelete.jpg"
    img_file.write_bytes(b"fake")
    item = CoffeeItem(name="Americano", image="static/images/menu_items/coffee/todelete.jpg", price=40)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    resp = client.post("/admin/manage-items/delete", json={"id": item_id, "category": "coffee_items"})
    assert resp.json() == {"success": True}
    assert db_session.get(CoffeeItem, item_id) is None
    assert not img_file.exists()


def test_ajax_delete_requires_products_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["orders_view"]')
    resp = client.post("/admin/manage-items/delete", json={"id": 1, "category": "coffee_items"}, follow_redirects=False)
    assert resp.status_code == 303
