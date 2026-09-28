"""Integration tests for the /api/cart endpoints, driven through the
TestClient (routing + session persistence + response models), on top of
the service-level unit tests in test_cart_logic.py."""
from __future__ import annotations

from app.models.catalog import CakeItem, CoffeeItem, PizzaItem, Sauce


def test_add_then_view_cart(api, db_session):
    coffee = CoffeeItem(name="Латте", description="Класична кава", image="", price=60)
    db_session.add(coffee)
    db_session.commit()

    resp = api.post("/api/cart/items", json={"category": "coffee_items", "id": coffee.id})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "count": 1, "index": 0, "error": None}

    view = api.get("/api/cart").json()
    assert view["item_count"] == 1
    assert view["item_word"] == "товар"
    assert view["groups"][0]["label"] == "Кава"
    assert view["items"][0]["name"] == "Латте"
    assert view["total"] == 60
    assert view["back_category"] == "coffee_items"


def test_cart_empty_state(api):
    view = api.get("/api/cart").json()
    assert view["items"] == [] and view["total"] == 0 and view["item_count"] == 0


def test_add_quantity_and_session_badge(api, db_session):
    coffee = CoffeeItem(name="Капучино", description="", image="", price=65)
    db_session.add(coffee)
    db_session.commit()
    resp = api.post("/api/cart/items", json={"category": "coffee_items", "id": coffee.id, "quantity": 2})
    assert resp.json()["count"] == 2
    session = api.get("/api/session").json()
    assert session["cart"] == {"count": 2, "keys": [f"coffee_items_{coffee.id}"]}


def test_add_unknown_product_is_400(api):
    resp = api.post("/api/cart/items", json={"category": "coffee_items", "id": 999})
    assert resp.status_code == 400
    assert resp.json()["code"] == "unavailable"


def test_request_has_no_price_field(api, db_session):
    """Extra fields like a price are simply not part of the request model."""
    coffee = CoffeeItem(name="Лате", description="", image="", price=60)
    db_session.add(coffee)
    db_session.commit()
    api.post("/api/cart/items", json={"category": "coffee_items", "id": coffee.id, "price_override": 1, "price": 1})
    assert api.get("/api/cart").json()["total"] == 60


def test_cart_preview_and_remove(api, db_session):
    coffee = CoffeeItem(name="Еспресо", description="", image="", price=40)
    db_session.add(coffee)
    db_session.commit()
    api.post("/api/cart/items", json={"category": "coffee_items", "id": coffee.id})

    pdata = api.get("/api/cart/preview").json()
    assert pdata["total"] == 40
    assert len(pdata["items"]) == 1

    rdata = api.delete("/api/cart/items/0").json()
    assert rdata == {"ok": True, "cart_total": 0, "cart_count": 0}
    assert api.delete("/api/cart/items/0").status_code == 404


def test_cart_with_pizza_and_cake_opt_tags(api, db_session):
    pizza = PizzaItem(name="Гавайська", description="Ананас, шинка", image="", price=190, price_large=270, has_size_choice=True)
    cake = CakeItem(name="Медовик", description="На замовлення", image="", price=1000, price_per_kg=1000, min_weight=1.0)
    db_session.add_all([pizza, cake])
    db_session.commit()

    api.post("/api/cart/items", json={"category": "pizza_items", "id": pizza.id, "selected_size": "large", "cheese_crust": True})
    api.post("/api/cart/items", json={"category": "cake_items", "id": cake.id, "weight": 1.5})

    view = api.get("/api/cart").json()
    by_name = {it["name"]: it for it in view["items"]}
    assert by_name["Гавайська"]["opt_tags"] == ["40 см", "Сирний бортик"]
    assert by_name["Гавайська"]["price"] == 370  # 270 + 100 crust
    assert by_name["Гавайська"]["editable"] is True
    assert by_name["Медовик"]["opt_tags"] == ["1.5 кг"]
    assert by_name["Медовик"]["subtotal"] == 1500
    assert view["total"] == 1870


def test_edit_item_via_patch(api, db_session):
    pizza = PizzaItem(name="Маргарита", description="", image="", price=180, price_large=260, has_size_choice=True)
    db_session.add(pizza)
    db_session.commit()
    api.post("/api/cart/items", json={"category": "pizza_items", "id": pizza.id})

    detail = api.get("/api/cart/items/0").json()
    assert detail["price_large"] == 260 and detail["has_size_choice"] is True

    resp = api.patch("/api/cart/items/0", json={"selected_size": "large", "quantity": 2})
    body = resp.json()
    assert body["new_price"] == 260 and body["new_qty"] == 2 and body["new_subtotal"] == 520
    assert api.get("/api/cart").json()["total"] == 520


def test_patch_validates_quantity_range(api, db_session):
    db_session.add(CoffeeItem(name="Лате", image="", price=60))
    db_session.commit()
    api.post("/api/cart/items", json={"category": "coffee_items", "id": 1})
    resp = api.patch("/api/cart/items/0", json={"quantity": 500})
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_request"


def test_sauces_are_their_own_lines(api, db_session):
    db_session.add(Sauce(name="Часниковий", price=15, active=True, sort_order=1, image=""))
    db_session.commit()
    api.post("/api/cart/items", json={"category": "sauces", "id": 1, "quantity": 2})
    view = api.get("/api/cart").json()
    assert view["groups"][0]["label"] == "Соуси"
    assert view["total"] == 30


def test_clear_cart(api, db_session):
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.commit()
    api.post("/api/cart/items", json={"category": "coffee_items", "id": coffee.id})

    assert api.delete("/api/cart").json() == {"ok": True}
    assert api.get("/api/cart/preview").json()["count"] == 0
