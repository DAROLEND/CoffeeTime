"""Read-only public endpoints (home, menu, gallery, reviews, about) against
a seeded SQLite DB, plus review submission."""
from __future__ import annotations

import json

from app.models.catalog import (
    CakeItem, ColdDrinkItem, CoffeeItem, FastFoodItem, IceCreamItem,
    MiniPizzaItem, PizzaItem, SaladItem, Sauce, SushiItem, SushiSet,
)
from app.models.cms import Gallery, GalleryCategory, HeroSlide, SiteReview, SiteSetting
from tests.helpers import login_user


def _seed_minimal(db_session):
    # Avoids the homepage's ORDER BY RANDOM() dessert-image fallback so the
    # banner image is deterministic.
    db_session.add(SiteSetting(key="dessert_banner_image", value="static/images/menu_items/desserts/tart.webp"))
    db_session.add(CoffeeItem(name="Лате", description="Класична кава з молоком", image="", price=60, popularity=5))
    db_session.add(PizzaItem(name="Маргарита", description="Томати, моцарела", image="", price=180, price_large=260, popularity=3))
    db_session.add(Gallery(filename="photo1.webp", alt="Кафе", category=GalleryCategory.FOOD))
    db_session.add(SiteReview(name="Оксана", text="Дуже смачна кава і затишна атмосфера тут щоразу!", rating=5))
    db_session.commit()


def test_home(api, db_session):
    _seed_minimal(db_session)
    data = api.get("/api/home").json()
    assert len(data["hero_slides"]) == 3  # fallback slides when none are configured
    assert data["hero_slides"][0]["image"].startswith("/static/")
    assert data["food_items"][0]["name"] == "Маргарита"
    assert data["drink_items"][0]["name"] == "Лате"
    assert data["dessert_banner"]["image"] == "/static/images/menu_items/desserts/tart.webp"
    assert data["reviews"][0]["name"] == "Оксана"
    assert data["about"]["title"] == "Місце, де час зупиняється"
    assert data["about"]["years_open"] >= 10


def test_home_uses_active_hero_slides(api, db_session):
    _seed_minimal(db_session)
    db_session.add(HeroSlide(image="static/images/slides/a.jpg", title="Мій слайд", subtitle="", active=True))
    db_session.add(HeroSlide(image="static/images/slides/b.jpg", title="Вимкнений", subtitle="", active=False))
    db_session.commit()
    slides = api.get("/api/home").json()["hero_slides"]
    assert [s["text"] for s in slides] == ["Мій слайд"]


def test_menu(api, db_session):
    _seed_minimal(db_session)
    data = api.get("/api/menu").json()
    assert data["current"] == "coffee_items"
    assert data["current_group"] == "drinks"
    assert [g["id"] for g in data["groups"]] == ["drinks", "food", "fastfood", "sushi"]
    assert data["sections"]["coffee_items"][0]["name"] == "Лате"
    assert data["sections"]["pizza_items"][0]["name"] == "Маргарита"


def test_menu_all_category_branches(api, db_session):
    """Exercises the less-common card branches: pizza with a real size
    choice, cake (weight-priced), ice cream (scoop variant), mini pizza,
    fast food with a size variant, sushi set with pieces_count, salad,
    cold drink, and an active sauce."""
    db_session.add(PizzaItem(
        name="Пепероні", description="Гостра", image="", price=200, price_large=280,
        has_size_choice=True, is_spicy=True, sauce_type="bbq", ingredients_tags="пепероні,сир", popularity=1,
    ))
    db_session.add(MiniPizzaItem(name="Міні Маргарита", description="", image="", price=90, popularity=0))
    db_session.add(CakeItem(name="Медовик", description="На замовлення", image="", price=1000, price_per_kg=1000, min_weight=1.0))
    db_session.add(IceCreamItem(
        name="Пломбір", description="", image="", price=40,
        variant_options=json.dumps({"type": "scoops", "options": [{"id": "1", "label": "1 кулька", "price_diff": 0}]}),
    ))
    db_session.add(FastFoodItem(
        name="Хот-дог", description="", image="", price=70,
        variant_options=json.dumps({"type": "size", "options": [{"id": 1, "label": "Малий", "price_diff": 0}, {"id": 2, "label": "Великий", "price_diff": 20}]}),
    ))
    db_session.add(SushiSet(name="Філадельфія сет", description="", image="", price=450, weight="500г", pieces_count=32))
    db_session.add(SushiItem(name="Каліфорнія рол", description="", image="", price=180, weight="200г"))
    db_session.add(SaladItem(name="Цезар", description="", image="", price=150))
    db_session.add(ColdDrinkItem(name="Лимонад", description="", image="", price=55))
    db_session.add(Sauce(name="Часниковий", price=15, emoji="🧄", active=True, sort_order=1))
    db_session.commit()

    data = api.get("/api/menu?category=pizza_items").json()
    assert data["current"] == "pizza_items" and data["current_group"] == "food"
    sections = data["sections"]

    pizza, mini = sections["pizza_items"]
    assert pizza["has_size"] and pizza["is_spicy"] and pizza["sauce_type"] == "bbq"
    assert pizza["tags"] == ["пепероні", "сир"]
    assert mini["category"] == "mini_pizza_items" and mini["label"] == "Міні-піца"  # merged into pizza

    assert sections["cake_items"][0]["price_per_kg"] == 1000
    ice = next(c for c in sections["dessert_items"] if c["category"] == "ice_cream_items")  # merged into desserts
    assert ice["has_ice_cream_scoop"] is True
    hotdog = sections["fast_food_items"][0]
    assert hotdog["has_fast_food_size"] is True  # '"type": "size"' with a space is still recognized
    assert hotdog["ff_large_price"] == 90 and hotdog["ff_size_str"] == "Малий / Великий"
    assert hotdog["variant_options"]["options"][1] == {"id": "2", "label": "Великий", "price_diff": 20.0, "sizes": []}
    assert sections["sushi_sets"][0]["sushi_tags"] == ["500г", "32 шт"]
    assert data["sauces"][0]["name"] == "Часниковий"
    assert "пепероні" in data["ingredient_tags"]
    tabs = {t["key"]: t["count"] for t in data["tabs"]}
    assert tabs["pizza_items"] == 2 and tabs["dessert_items"] == 1


def test_menu_subcategory_resolves_to_parent_tab(api, db_session):
    assert api.get("/api/menu?category=mini_pizza_items").json()["current"] == "pizza_items"
    assert api.get("/api/menu?category=ice_cream_items").json()["current"] == "dessert_items"
    assert api.get("/api/menu?category=bogus").json()["current"] == "coffee_items"


def test_menu_single_category(api, db_session):
    _seed_minimal(db_session)
    assert [c["name"] for c in api.get("/api/menu/pizza_items").json()] == ["Маргарита"]
    assert api.get("/api/menu/nope").status_code == 404


def test_gallery(api, db_session):
    _seed_minimal(db_session)
    data = api.get("/api/gallery").json()
    assert data["photos"][0]["url"] == "/static/images/gallery/photo1.webp"
    assert data["food_count"] == 1 and data["interior_count"] == 0


def test_reviews_page(api, db_session):
    _seed_minimal(db_session)
    data = api.get("/api/reviews").json()
    assert data["reviews"][0]["name"] == "Оксана"
    assert data["avg_rating"] == 5.0
    assert data["distribution"][0] == {"stars": 5, "count": 1, "pct": 100}


def test_reviews_filter_sort_and_pagination(api, db_session):
    for i in range(8):
        db_session.add(SiteReview(name=f"Гість {i}", text="Текст відгуку номер " + str(i), rating=(i % 5) + 1))
    db_session.commit()
    page2 = api.get("/api/reviews?page=2").json()
    assert page2["page"] == 2 and page2["total_pages"] == 2 and len(page2["reviews"]) == 2
    fives = api.get("/api/reviews?filter=5").json()
    assert {r["rating"] for r in fives["reviews"]} == {5}
    worst = api.get("/api/reviews?sort=worst").json()
    assert worst["reviews"][0]["rating"] == 1


def test_declined_reviews_are_hidden(api, db_session):
    db_session.add(SiteReview(name="Спамер", text="Спам спам спам спам", rating=1, status="declined"))
    db_session.add(SiteReview(name="Гість", text="Все було дуже смачно", rating=5))
    db_session.commit()
    data = api.get("/api/reviews").json()
    assert [r["name"] for r in data["reviews"]] == ["Гість"]
    assert data["total_count"] == 1


def test_submit_review_requires_login(api):
    resp = api.post("/api/reviews", json={"name": "Іван", "text": "Все дуже смачно!", "rating": 5})
    assert resp.status_code == 401


def test_submit_review(api, db_session):
    login_user(api, db_session)
    bad = api.post("/api/reviews", json={"name": "І", "text": "коротко", "rating": 0})
    assert bad.status_code == 400 and len(bad.json()["errors"]) == 3
    ok = api.post("/api/reviews", json={"name": "Іван", "text": "Все дуже смачно!", "rating": 5})
    assert ok.status_code == 201
    assert api.get("/api/reviews").json()["reviewed_already"] is True


def test_about(api, db_session):
    db_session.add(SiteSetting(key="about_title", value="Наша історія"))
    db_session.commit()
    data = api.get("/api/about").json()
    assert data["title"] == "Наша історія"
    assert data["photo"] == "/static/images/main/about-photo.png"
