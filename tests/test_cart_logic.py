"""Unit tests for app/services/cart.py. Subtle dedup-key mistakes are the
easiest way to silently break "same pizza different size" vs "duplicate
line" behavior."""
from __future__ import annotations

from app.middleware.session import SessionData
from app.models.catalog import CakeItem, CoffeeItem, IceCreamItem, PizzaItem, Sauce
from app.services import cart as cart_service


def _session(cart=None) -> SessionData:
    return SessionData({"cart": cart or []})


def test_add_plain_item_merges_on_second_add(db_session):
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.commit()

    session = _session()
    r1 = cart_service.add_to_cart(session, db_session, "coffee_items", coffee.id, 1, {})
    r2 = cart_service.add_to_cart(session, db_session, "coffee_items", coffee.id, 2, {})

    assert r1["ok"] and r2["ok"]
    assert len(session["cart"]) == 1
    assert session["cart"][0]["quantity"] == 3
    assert r2["count"] == 3


def test_add_pizza_different_size_creates_separate_lines(db_session):
    pizza = PizzaItem(name="Маргарита", description="", image="", price=180, price_large=260, has_size_choice=True)
    db_session.add(pizza)
    db_session.commit()

    # menu.js always sends a client-computed price_override for sized
    # pizzas; the server re-verifies it against the DB price/price_large
    # rather than trusting it outright (see the crust-surcharge test).
    session = _session()
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "small", "price_override": "180"})
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "large", "price_override": "260"})
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "small", "price_override": "180"})

    cart = session["cart"]
    assert len(cart) == 2  # small merged with small, large is separate
    small = next(c for c in cart if c["selected_size"] == "small")
    large = next(c for c in cart if c["selected_size"] == "large")
    assert small["quantity"] == 2
    assert large["quantity"] == 1
    assert small["price_override"] == 180
    assert large["price_override"] == 260


def test_add_pizza_cheese_crust_surcharge_applied_and_is_separate_key(db_session):
    pizza = PizzaItem(name="Пепероні", description="", image="", price=200, price_large=280, has_size_choice=True)
    db_session.add(pizza)
    db_session.commit()

    session = _session()
    # Client sends a price_override (as menu.js does); server re-verifies it from DB.
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "small", "cheese_crust": "1", "price_override": "999"})
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "small", "cheese_crust": "0", "price_override": "999"})

    cart = session["cart"]
    assert len(cart) == 2  # crust is part of the dedup key
    with_crust = next(c for c in cart if c["cheese_crust"] == 1)
    without_crust = next(c for c in cart if c["cheese_crust"] == 0)
    assert with_crust["price_override"] == 200 + 65  # server ignores the client's bogus 999
    assert without_crust["price_override"] == 200


def test_mini_pizza_has_no_cheese_crust_surcharge(db_session):
    from app.models.catalog import MiniPizzaItem
    mp = MiniPizzaItem(name="Міні Маргарита", description="", image="", price=90)
    db_session.add(mp)
    db_session.commit()

    session = _session()
    cart_service.add_to_cart(session, db_session, "mini_pizza_items", mp.id, 1, {"selected_size": "small", "cheese_crust": "1", "price_override": "500"})

    assert session["cart"][0]["price_override"] == 90  # crust surcharge never applied to mini pizza


def test_add_cake_is_always_a_singleton_line(db_session):
    cake = CakeItem(name="Медовик", description="", image="", price=1000, price_per_kg=1000, min_weight=1.0)
    db_session.add(cake)
    db_session.commit()

    session = _session()
    cart_service.add_to_cart(session, db_session, "cake_items", cake.id, 1, {"weight": "1.5"})
    cart_service.add_to_cart(session, db_session, "cake_items", cake.id, 1, {"weight": "2.0"})

    cart = session["cart"]
    assert len(cart) == 1  # overwritten, not appended
    assert cart[0]["weight"] == 2.0
    assert cart[0]["price_override"] == 2000
    assert cart[0]["quantity"] == 1


def test_add_cake_below_min_weight_is_clamped(db_session):
    cake = CakeItem(name="Наполеон", description="", image="", price=1200, price_per_kg=1200, min_weight=1.5)
    db_session.add(cake)
    db_session.commit()

    session = _session()
    cart_service.add_to_cart(session, db_session, "cake_items", cake.id, 1, {"weight": "0.5"})

    assert session["cart"][0]["weight"] == 1.5  # clamped up to min_weight
    assert session["cart"][0]["price_override"] == 1800


def test_ice_cream_dedups_by_variant_json_equality(db_session):
    ic = IceCreamItem(name="Пломбір", description="", image="", price=40)
    db_session.add(ic)
    db_session.commit()

    session = _session()
    v1 = '{"scoop_label":"2 кульки","price_diff":15}'
    v2 = '{"scoop_label":"3 кульки","price_diff":30}'
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 1, {"selected_variant": v1})
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 1, {"selected_variant": v2})
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 2, {"selected_variant": v1})

    cart = session["cart"]
    assert len(cart) == 2
    line1 = next(c for c in cart if c["selected_variant"] == v1)
    assert line1["quantity"] == 3
    assert line1["price_override"] == 55  # 40 + 15
    line2 = next(c for c in cart if c["selected_variant"] == v2)
    assert line2["price_override"] == 70  # 40 + 30


def test_sauce_requires_active_flag(db_session):
    active_sauce = Sauce(name="Часниковий", price=15, active=True)
    inactive_sauce = Sauce(name="Старий", price=10, active=False)
    db_session.add_all([active_sauce, inactive_sauce])
    db_session.commit()

    session = _session()
    ok = cart_service.add_to_cart(session, db_session, "sauces", active_sauce.id, 1, {})
    bad = cart_service.add_to_cart(session, db_session, "sauces", inactive_sauce.id, 1, {})

    assert ok["ok"] is True
    assert bad["ok"] is False
    assert len(session["cart"]) == 1


def test_remove_from_cart_by_session_index(db_session):
    session = _session([
        {"category": "coffee_items", "id": 1, "quantity": 1},
        {"category": "coffee_items", "id": 2, "quantity": 1},
    ])
    coffee2 = CoffeeItem(id=2, name="Капучино", description="", image="", price=65)
    db_session.merge(coffee2)
    db_session.commit()

    result = cart_service.remove_from_cart(session, db_session, 0, "", 0)
    assert result["ok"] is True
    assert len(session["cart"]) == 1
    assert session["cart"][0]["id"] == 2


def test_update_qty_stepper_removes_at_zero(db_session):
    coffee = CoffeeItem(name="Еспресо", description="", image="", price=40)
    db_session.add(coffee)
    db_session.commit()
    session = _session([{"category": "coffee_items", "id": coffee.id, "quantity": 1}])

    result = cart_service.update_qty_stepper(session, db_session, "coffee_items", coffee.id, "decrease", None)
    assert result["ok"] is True
    assert result["removed"] is True
    assert session["cart"] == []


def test_update_qty_stepper_rejects_cake_category(db_session):
    """cake_items is deliberately excluded from the qty-stepper whitelist."""
    session = _session([{"category": "cake_items", "id": 1, "quantity": 1}])
    result = cart_service.update_qty_stepper(session, db_session, "cake_items", 1, "increase", None)
    assert result == {"ok": False}


def test_update_cart_variant_updates_the_last_matching_line(db_session):
    session = _session([
        {"category": "fast_food_items", "id": 5, "quantity": 1},
        {"category": "fast_food_items", "id": 5, "quantity": 2},
    ])
    result = cart_service.update_cart_variant(session, "fast_food_items", 5, '{"sauces":[]}')
    assert result["ok"] is True
    assert "selected_variant" not in session["cart"][0]
    assert session["cart"][1]["selected_variant"] == '{"sauces":[]}'


def test_get_cart_preview_totals(db_session):
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.commit()
    session = _session([{"category": "coffee_items", "id": coffee.id, "quantity": 3}])

    preview = cart_service.get_cart_preview(session, db_session)
    assert preview["ok"] is True
    assert preview["total"] == 180
    assert preview["count"] == 3
    assert preview["items"][0]["name"] == "Латте"
