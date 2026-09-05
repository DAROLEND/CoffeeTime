"""Integration smoke test for the /cart page and its AJAX endpoints,
driven through FastAPI's TestClient (router + Jinja template wiring, not
just the service-layer unit tests in test_cart_logic.py)."""
from __future__ import annotations

from app.models.catalog import CakeItem, CoffeeItem, PizzaItem


def test_cart_quick_add_then_render(client, db_session):
    coffee = CoffeeItem(name="Латте", description="Класична кава", image="", price=60)
    db_session.add(coffee)
    db_session.commit()

    resp = client.get(f"/cart?action=add&category=coffee_items&id={coffee.id}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/cart"

    resp = client.get("/cart")
    assert resp.status_code == 200
    assert "Латте" in resp.text
    assert "1 товар" in resp.text or "товар" in resp.text


def test_cart_empty_state_renders(client, db_session):
    resp = client.get("/cart")
    assert resp.status_code == 200
    assert "Ваша корзина порожня" in resp.text


def test_add_to_cart_ajax_endpoint(client, db_session):
    coffee = CoffeeItem(name="Капучино", description="", image="", price=65)
    db_session.add(coffee)
    db_session.commit()

    resp = client.post("/forms/add_to_cart.php", data={"category": "coffee_items", "id": coffee.id, "quantity": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] == 2


def test_cart_preview_and_remove_ajax(client, db_session):
    coffee = CoffeeItem(name="Еспресо", description="", image="", price=40)
    db_session.add(coffee)
    db_session.commit()

    client.post("/forms/add_to_cart.php", data={"category": "coffee_items", "id": coffee.id, "quantity": 1})

    preview = client.get("/forms/get_cart_preview.php")
    assert preview.status_code == 200
    pdata = preview.json()
    assert pdata["ok"] is True
    assert pdata["total"] == 40
    assert len(pdata["items"]) == 1

    remove = client.post("/forms/remove_from_cart.php", data={"session_index": 0})
    assert remove.status_code == 200
    rdata = remove.json()
    assert rdata["ok"] is True
    assert rdata["cart_count"] == 0


def test_cart_page_renders_with_pizza_and_cake(client, db_session):
    pizza = PizzaItem(name="Гавайська", description="Ананас, шинка", image="", price=190, price_large=270, has_size_choice=True)
    cake = CakeItem(name="Медовик", description="На замовлення", image="", price=1000, price_per_kg=1000, min_weight=1.0)
    db_session.add_all([pizza, cake])
    db_session.commit()

    client.post("/forms/add_to_cart.php", data={"category": "pizza_items", "id": pizza.id, "selected_size": "large", "price_override": 270})
    client.post("/forms/add_to_cart.php", data={"category": "cake_items", "id": cake.id, "weight": 1.5})

    resp = client.get("/cart")
    assert resp.status_code == 200
    assert "Гавайська" in resp.text
    assert "Медовик" in resp.text
    assert "40 см" in resp.text  # large-size opt tag
    assert "1.5 кг" in resp.text  # cake weight opt tag


def test_clear_cart_ajax(client, db_session):
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.commit()
    client.post("/forms/add_to_cart.php", data={"category": "coffee_items", "id": coffee.id, "quantity": 1})

    resp = client.post("/forms/clear_cart.php")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    preview = client.get("/forms/get_cart_preview.php")
    assert preview.json()["count"] == 0
