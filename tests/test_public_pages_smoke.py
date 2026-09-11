"""Renders every public read-only route against a seeded SQLite DB and
confirms it returns 200 with no Jinja/template errors.
"""
from __future__ import annotations

import json

from app.models.catalog import (
    CakeItem, ColdDrinkItem, CoffeeItem, FastFoodItem, IceCreamItem,
    MiniPizzaItem, PizzaItem, SaladItem, Sauce, SushiItem, SushiSet,
)
from app.models.cms import Gallery, GalleryCategory, SiteReview, SiteSetting


def _seed_minimal(db_session):
    # Avoids the index route's ORDER BY RAND() dessert-image fallback,
    # which SQLite can't execute (MySQL-only function) — see conftest.py.
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/menu_items/desserts/tart.webp"))
    db_session.add(CoffeeItem(name="Лате", description="Класична кава з молоком", image="", price=60, popularity=5))
    db_session.add(PizzaItem(name="Маргарита", description="Томати, моцарела", image="", price=180, price_large=260, popularity=3))
    db_session.add(Gallery(filename="photo1.webp", alt="Кафе", category=GalleryCategory.FOOD))
    db_session.add(SiteReview(name="Оксана", text="Дуже смачна кава і затишна атмосфера тут щоразу!", rating=5))
    db_session.commit()


def test_index_page_renders(client, db_session):
    _seed_minimal(db_session)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Coffee Time" in resp.text or "Головна" in resp.text


def test_menu_page_renders(client, db_session):
    _seed_minimal(db_session)
    resp = client.get("/menu")
    assert resp.status_code == 200
    assert "Лате" in resp.text
    assert "Маргарита" in resp.text


def test_menu_page_all_category_branches_render(client, db_session):
    """Exercises the less-common renderCard() branches: pizza with a real
    size choice + cheese crust, cake (weight-priced), ice cream (scoop
    variant), mini pizza, fast food with a size/filling variant, sushi
    set with pieces_count, salad, cold drink, and an active sauce."""
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/menu_items/desserts/tart.webp"))
    db_session.add(PizzaItem(
        name="Пепероні", description="Гостра", image="", price=200, price_large=280,
        has_size_choice=True, is_spicy=True, sauce_type="bbq", ingredients_tags="пепероні,сир", popularity=1,
    ))
    db_session.add(MiniPizzaItem(name="Міні Маргарита", description="", image="", price=90, popularity=0))
    db_session.add(CakeItem(name="Медовик", description="На замовлення", image="", price=1000, price_per_kg=1000, min_weight=1.0))
    db_session.add(IceCreamItem(
        name="Пломбір", description="", image="", price=40,
        variant_options=json.dumps({"scoops": [{"count": 1, "price_diff": 0}]}),
    ))
    db_session.add(FastFoodItem(
        name="Хот-дог", description="", image="", price=70,
        variant_options=json.dumps({"type": "size", "options": [{"label": "Малий", "price_diff": 0}, {"label": "Великий", "price_diff": 20}]}),
    ))
    db_session.add(SushiSet(name="Філадельфія сет", description="", image="", price=450, weight="500г", pieces_count=32))
    db_session.add(SushiItem(name="Каліфорнія рол", description="", image="", price=180, weight="200г"))
    db_session.add(SaladItem(name="Цезар", description="", image="", price=150))
    db_session.add(ColdDrinkItem(name="Лимонад", description="", image="", price=55))
    db_session.add(Sauce(name="Часниковий", price=15, emoji="🧄", active=True, sort_order=1))
    db_session.commit()

    for category in [
        "pizza_items", "dessert_items", "fast_food_items", "sushi_items",
        "sushi_sets", "salad_items", "cold_drink_items",
    ]:
        resp = client.get(f"/menu?category={category}")
        assert resp.status_code == 200, f"category={category} failed"

    resp = client.get("/menu?category=pizza_items")
    assert "Пепероні" in resp.text
    assert "Міні Маргарита" in resp.text  # merged mini-pizza section
    assert "Сирний бортик" in resp.text  # crust option markup present in modal

    resp = client.get("/menu?category=dessert_items")
    assert "Пломбір" in resp.text  # merged ice-cream section

    resp = client.get("/menu?category=fast_food_items")
    assert "Хот-дог" in resp.text

    resp = client.get("/menu?category=sushi_sets")
    assert "32 шт" in resp.text  # pieces_count tag rendered


def test_menu_page_category_redirects(client, db_session):
    _seed_minimal(db_session)
    resp = client.get("/menu?category=mini_pizza_items", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/menu?category=pizza_items"


def test_gallery_page_renders(client, db_session):
    _seed_minimal(db_session)
    resp = client.get("/gallery")
    assert resp.status_code == 200
    assert "photo1.webp" in resp.text


def test_reviews_page_renders(client, db_session):
    _seed_minimal(db_session)
    resp = client.get("/reviews")
    assert resp.status_code == 200
    assert "Оксана" in resp.text


def test_reviews_ajax_returns_json(client, db_session):
    _seed_minimal(db_session)
    resp = client.get("/reviews?ajax=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "Оксана" in data["html"]


def test_about_and_contact_render_empty_shells(client, db_session):
    _seed_minimal(db_session)
    for path in ("/about", "/contact"):
        resp = client.get(path)
        assert resp.status_code == 200
