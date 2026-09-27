"""Unit tests for app/services/cart.py and app/services/pricing.py.
Subtle dedup-key mistakes are the easiest way to silently break "same
pizza different size" vs "duplicate line" behavior, and every price must
come from the DB, never from the client."""
from __future__ import annotations

import json

from app.middleware.session import SessionData
from app.models.catalog import CakeItem, CoffeeItem, FastFoodItem, IceCreamItem, PizzaItem, Sauce
from app.services import cart as cart_service

SCOOPS = json.dumps({
    "type": "scoops", "label": "Кількість кульок",
    "options": [
        {"id": "1", "label": "1 кулька", "price_diff": 0},
        {"id": "2", "label": "2 кульки", "price_diff": 15},
        {"id": "3", "label": "3 кульки", "price_diff": 30},
    ],
}, ensure_ascii=False)

FILLINGS = json.dumps({
    "type": "filling", "label": "Начинка",
    "options": [
        {"id": "meat", "label": "М'ясна", "price_diff": 10, "sizes": [
            {"label": "Мала", "price_diff": 0}, {"label": "Велика", "price_diff": 25},
        ]},
        {"id": "veg", "label": "Овочева", "price_diff": 0},
    ],
}, ensure_ascii=False)


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


def test_ice_cream_dedups_by_selected_option(db_session):
    ic = IceCreamItem(name="Пломбір", description="", image="", price=40, variant_options=SCOOPS)
    db_session.add(ic)
    db_session.commit()

    session = _session()
    v2 = json.dumps({"type": "scoops", "scoop_id": "2"})
    v3 = json.dumps({"type": "scoops", "scoop_id": "3"})
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 1, {"selected_variant": v2})
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 1, {"selected_variant": v3})
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 2, {"selected_variant": v2})

    cart = session["cart"]
    assert len(cart) == 2
    line1 = next(c for c in cart if json.loads(c["selected_variant"])["scoop_id"] == "2")
    assert line1["quantity"] == 3
    assert line1["price_override"] == 55  # 40 + 15
    assert json.loads(line1["selected_variant"])["scoop_label"] == "2 кульки"  # label copied from the DB
    line2 = next(c for c in cart if json.loads(c["selected_variant"])["scoop_id"] == "3")
    assert line2["price_override"] == 70  # 40 + 30


def test_client_supplied_prices_are_ignored(db_session):
    """A tampered `price_diff` inside the variant JSON, or a
    `price_override` form field, has no effect on the price."""
    ic = IceCreamItem(name="Пломбір", description="", image="", price=40, variant_options=SCOOPS)
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add_all([ic, coffee])
    db_session.commit()

    session = _session()
    cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 1, {
        "selected_variant": json.dumps({"type": "scoops", "scoop_id": "3", "price_diff": -39}),
        "price_override": "1",
    })
    cart_service.add_to_cart(session, db_session, "coffee_items", coffee.id, 1, {"price_override": "1"})

    ice, latte = session["cart"]
    assert ice["price_override"] == 70
    assert json.loads(ice["selected_variant"])["price_diff"] == 30
    assert latte["price_override"] == 60
    preview = cart_service.get_cart_preview(session, db_session)
    assert preview["total"] == 130


def test_unknown_variant_option_is_rejected(db_session):
    ic = IceCreamItem(name="Пломбір", description="", image="", price=40, variant_options=SCOOPS)
    db_session.add(ic)
    db_session.commit()
    session = _session()
    result = cart_service.add_to_cart(session, db_session, "ice_cream_items", ic.id, 1, {
        "selected_variant": json.dumps({"type": "scoops", "scoop_id": "99"}),
    })
    assert result == {"ok": False, "error": "invalid_variant"}
    assert session["cart"] == []


def test_fast_food_filling_with_nested_size_is_priced_from_db(db_session):
    ff = FastFoodItem(name="Шаурма", description="", image="", price=100, variant_options=FILLINGS)
    db_session.add(ff)
    db_session.commit()
    session = _session()

    cart_service.add_to_cart(session, db_session, "fast_food_items", ff.id, 1, {
        "selected_variant": json.dumps({"type": "filling", "filling_id": "meat", "size_label": "Велика"}),
    })
    # No selection at all defaults to the first option (first size), like the menu UI.
    cart_service.add_to_cart(session, db_session, "fast_food_items", ff.id, 1, {})

    big, default = session["cart"]
    assert big["price_override"] == 135  # 100 + 10 + 25
    assert json.loads(big["selected_variant"])["size_label"] == "Велика"
    assert default["price_override"] == 110  # 100 + 10 + 0
    assert json.loads(default["selected_variant"])["size_label"] == "Мала"


def test_large_pizza_without_client_price_is_charged_large_price(db_session):
    """Previously the server only priced a size when the client also sent
    a price_override; without one a large pizza cost the small price."""
    pizza = PizzaItem(name="Маргарита", description="", image="", price=180, price_large=260, has_size_choice=True)
    db_session.add(pizza)
    db_session.commit()
    session = _session()
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "large"})
    assert session["cart"][0]["price_override"] == 260
    assert cart_service.get_cart_preview(session, db_session)["total"] == 260


def test_pizza_without_size_choice_is_always_small(db_session):
    pizza = PizzaItem(name="Кальцоне", description="", image="", price=150, price_large=0, has_size_choice=False)
    db_session.add(pizza)
    db_session.commit()
    session = _session()
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "large"})
    assert session["cart"][0]["selected_size"] == "small"
    assert session["cart"][0]["price_override"] == 150


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


def test_update_quantity_by_index_targets_the_right_pizza_line(db_session):
    """Two lines share category+id (small and large); editing by index
    must only touch the one that was clicked."""
    pizza = PizzaItem(name="Маргарита", description="", image="", price=180, price_large=260, has_size_choice=True)
    db_session.add(pizza)
    db_session.commit()
    session = _session()
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "small"})
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "large"})

    result = cart_service.update_cart_item(session, db_session, 1, {"quantity": 3})
    assert result["ok"] is True
    assert result["new_subtotal"] == 780
    assert [c["quantity"] for c in session["cart"]] == [1, 3]


def test_update_cart_item_cake_stays_single(db_session):
    cake = CakeItem(name="Медовик", description="", image="", price=1000, price_per_kg=1000, min_weight=1.0)
    db_session.add(cake)
    db_session.commit()
    session = _session()
    cart_service.add_to_cart(session, db_session, "cake_items", cake.id, 1, {"weight": "1.5"})
    result = cart_service.update_cart_item(session, db_session, 0, {"quantity": 5, "weight": 2.5})
    assert result["new_qty"] == 1
    assert result["new_price"] == 2500


def test_update_cart_item_changing_options_merges_duplicate_lines(db_session):
    pizza = PizzaItem(name="Маргарита", description="", image="", price=180, price_large=260, has_size_choice=True)
    db_session.add(pizza)
    db_session.commit()
    session = _session()
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 1, {"selected_size": "small"})
    cart_service.add_to_cart(session, db_session, "pizza_items", pizza.id, 2, {"selected_size": "large"})

    result = cart_service.update_cart_item(session, db_session, 0, {"selected_size": "large", "cheese_crust": "0"})
    assert result["merged"] is True
    assert len(session["cart"]) == 1
    assert session["cart"][0]["quantity"] == 3


def test_update_cart_item_rejects_bad_index(db_session):
    session = _session([{"category": "coffee_items", "id": 1, "quantity": 1}])
    assert cart_service.update_cart_item(session, db_session, 5, {"quantity": 2}) == {"ok": False, "error": "invalid_index"}


def test_fast_food_free_sauce_choice_is_validated(db_session):
    ff = FastFoodItem(name="Хот-дог", description="", image="", price=70, variant_options=json.dumps(
        {"type": "sauce", "label": "Який соус?", "options": ["Кетчуп", "Гірчиця"]}, ensure_ascii=False))
    db_session.add(ff)
    db_session.commit()
    session = _session()
    added = cart_service.add_to_cart(session, db_session, "fast_food_items", ff.id, 1, {})
    assert "selected_variant" not in session["cart"][0]

    ok = cart_service.update_cart_item(session, db_session, added["index"], {"selected_variant": "Гірчиця"})
    assert ok["ok"] is True
    assert json.loads(session["cart"][0]["selected_variant"]) == {"type": "sauce", "label": "Гірчиця"}
    assert ok["new_price"] == 70

    bad = cart_service.update_cart_item(session, db_session, added["index"], {"selected_variant": "Майонез"})
    assert bad == {"ok": False, "error": "invalid_variant"}


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
