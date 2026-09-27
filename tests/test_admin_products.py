"""Admin product management: list, read, create (cropper base64 or raw
file), update, delete. `require_perm('products')` guards every route."""
from __future__ import annotations

import base64
import json

import app.routers.admin.products as products_module
from app.models.catalog import CakeItem, CoffeeItem, IceCreamItem, SushiSet
from tests.helpers import login_admin

_FAKE_B64 = "data:image/jpeg;base64," + base64.b64encode(b"x" * 150).decode()


def test_products_require_products_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["orders_view"]')
    resp = api.get("/api/admin/products")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "У вас немає доступу до цього розділу."


def test_create_requires_products_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["orders_view"]')
    resp = api.post("/api/admin/products/coffee_items", data={"name": "X", "price": "10"})
    assert resp.status_code == 403


def test_list_shows_items_and_tab_counts(api, db_session):
    login_admin(api, db_session)
    db_session.add(CoffeeItem(name="Латте", image="static/images/menu_items/default.jpg", price=60))
    db_session.commit()

    data = api.get("/api/admin/products").json()
    assert data["is_all"] is True
    assert data["products"][0]["name"] == "Латте"
    assert data["products"][0]["price"] == 60
    assert data["products"][0]["has_photo"] is False
    assert {c["key"]: c["count"] for c in data["categories"]}["coffee_items"] == 1
    assert data["total_count"] == 1

    data = api.get("/api/admin/products?category=coffee_items").json()
    assert data["title"] == "Кава" and data["products"][0]["name"] == "Латте"
    assert api.get("/api/admin/products?category=nope").status_code == 404


def test_create_product(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)

    resp = api.post(
        "/api/admin/products/coffee_items",
        data={"name": "Еспресо", "price": "35", "description": "Міцна кава", "image_b64": _FAKE_B64},
    )
    assert resp.status_code == 201
    assert resp.json()["product"]["name"] == "Еспресо"

    created = db_session.query(CoffeeItem).filter_by(name="Еспресо").one()
    assert float(created.price) == 35.0
    assert created.image.startswith("static/images/menu_items/coffee/")
    assert (tmp_path / created.image).exists()


def test_create_product_with_raw_file_upload(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/products/coffee_items",
        data={"name": "Раф", "price": "70"},
        files={"image": ("photo.png", b"\x89PNG" + b"0" * 50, "image/png")},
    )
    assert resp.status_code == 201
    created = db_session.query(CoffeeItem).filter_by(name="Раф").one()
    assert created.image.endswith(".png")
    assert (tmp_path / created.image).exists()


def test_create_validation_errors(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post("/api/admin/products/coffee_items", data={"name": "", "price": "0"})
    assert resp.status_code == 400
    assert resp.json()["errors"] == [
        "Введіть назву товару.", "Ціна має бути більша за 0.", "Оберіть зображення для завантаження.",
    ]
    assert db_session.query(CoffeeItem).count() == 0


def test_create_rejects_bad_file_type(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post("/api/admin/products/coffee_items", data={"name": "Х", "price": "10"},
                    files={"image": ("virus.exe", b"MZ" * 40, "application/octet-stream")})
    assert resp.status_code == 400
    assert "Дозволені формати" in resp.json()["detail"]


def test_create_cake_uses_price_per_kg(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/products/cake_items",
        data={"name": "Медовик", "price_per_kg": "1200", "min_weight": "1.5", "image_b64": _FAKE_B64},
    )
    assert resp.status_code == 201
    created = db_session.query(CakeItem).filter_by(name="Медовик").one()
    assert float(created.price_per_kg) == 1200.0
    assert float(created.min_weight) == 1.5


def test_create_ice_cream_builds_variant_options(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    resp = api.post(
        "/api/admin/products/ice_cream_items",
        data={"name": "Ванільне", "price": "45", "scoop_diff_2": "20", "scoop_diff_3": "40", "image_b64": _FAKE_B64},
    )
    assert resp.json()["product"]["scoop_diff_2"] == 20
    created = db_session.query(IceCreamItem).filter_by(name="Ванільне").one()
    vo = json.loads(created.variant_options)
    assert vo["type"] == "scoops"
    assert vo["options"][1]["price_diff"] == 20.0
    assert vo["options"][2]["price_diff"] == 40.0


def test_update_product_fields(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    item = CoffeeItem(name="Капучино", image="static/images/menu_items/default.jpg", price=50)
    db_session.add(item)
    db_session.commit()

    resp = api.post(f"/api/admin/products/coffee_items/{item.id}", data={"name": "Капучино Гранде", "price": "65", "description": "Більша порція"})
    assert resp.status_code == 200
    db_session.expire_all()
    updated = db_session.get(CoffeeItem, item.id)
    assert updated.name == "Капучино Гранде"
    assert float(updated.price) == 65.0
    assert api.get(f"/api/admin/products/coffee_items/{item.id}").json()["description"] == "Більша порція"


def test_update_cake_price_per_kg(api, db_session, monkeypatch, tmp_path):
    """Editing a cake used to overwrite only the unused `price` column."""
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    cake = CakeItem(name="Наполеон", image="", price=1000, price_per_kg=1000, min_weight=1)
    db_session.add(cake)
    db_session.commit()
    api.post(f"/api/admin/products/cake_items/{cake.id}", data={"name": "Наполеон", "price_per_kg": "1300", "min_weight": "2"})
    db_session.expire_all()
    updated = db_session.get(CakeItem, cake.id)
    assert float(updated.price_per_kg) == 1300 and float(updated.min_weight) == 2


def test_update_remove_image(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    img_dir = tmp_path / "static" / "images" / "menu_items" / "coffee"
    img_dir.mkdir(parents=True)
    img_file = img_dir / "existing.jpg"
    img_file.write_bytes(b"fake")
    item = CoffeeItem(name="Мокко", image="static/images/menu_items/coffee/existing.jpg", price=55)
    db_session.add(item)
    db_session.commit()

    api.post(f"/api/admin/products/coffee_items/{item.id}", data={"name": "Мокко", "price": "55", "remove_image": "1"})
    db_session.expire_all()
    assert db_session.get(CoffeeItem, item.id).image == ""
    assert not img_file.exists()


def test_update_sushi_set_pieces_count(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    item = SushiSet(name="Філадельфія сет", image="static/images/menu_items/default.jpg", price=350, pieces_count=8)
    db_session.add(item)
    db_session.commit()
    api.post(f"/api/admin/products/sushi_sets/{item.id}", data={"name": "Філадельфія сет", "price": "350", "pieces_count": "12"})
    db_session.expire_all()
    assert db_session.get(SushiSet, item.id).pieces_count == 12


def test_delete_removes_product_and_image(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(products_module, "PROJECT_ROOT", tmp_path)
    login_admin(api, db_session)
    img_dir = tmp_path / "static" / "images" / "menu_items" / "coffee"
    img_dir.mkdir(parents=True)
    img_file = img_dir / "todelete.jpg"
    img_file.write_bytes(b"fake")
    item = CoffeeItem(name="Americano", image="static/images/menu_items/coffee/todelete.jpg", price=40)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    assert api.delete(f"/api/admin/products/coffee_items/{item_id}").json()["success"] is True
    assert db_session.get(CoffeeItem, item_id) is None
    assert not img_file.exists()


def test_delete_requires_products_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["orders_view"]')
    assert api.delete("/api/admin/products/coffee_items/1").status_code == 403
