"""
Cart business logic — ports of forms/add_to_cart.php, update_cart.php,
update_cart_item.php, update_cart_variant.php, remove_from_cart.php,
get_cart_item.php, get_cart_preview.php, and the item-resolution half of
pages/cart.php.

Session cart shape (unchanged from PHP): `session["cart"]` is a flat list
of dicts:
    {category, id, quantity,
     [price_override], [weight], [selected_size], [cheese_crust],
     [takeaway], [selected_variant: JSON string]}

Per-category whitelist sets below are intentionally NOT unified into one
constant — they reproduce the ~15 slightly different ad-hoc PHP arrays
faithfully (see app/constants/categories.py's module docstring), each
named after the endpoint whose exact membership it preserves. This
includes one confirmed-harmless PHP quirk: get_cart_item.php's whitelist
omits `sauces` (a real inconsistency vs. every other cart endpoint), but
sauces never reach the "edit" UI flow in cart.php in the first place, so
it's dead-path behavior, not a bug worth silently correcting.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.middleware.session import SessionData
from app.models.catalog import CakeItem, IceCreamItem, MiniPizzaItem, PizzaItem, Sauce
from app.services.media import item_img

ALL_CATEGORIES = {c.value for c in ProductCategory}  # 12
QTY_STEPPER_CATEGORIES = {  # update_cart.php
    "coffee_items", "fast_food_items", "pizza_items",
    "mini_pizza_items", "cold_drink_items", "dessert_items",
}
VARIANT_UPDATE_CATEGORIES = ALL_CATEGORIES - {"ice_cream_items", "sauces"}  # update_cart_variant.php
CART_ITEM_LOOKUP_CATEGORIES = ALL_CATEGORIES - {"sauces"}  # get_cart_item.php


def _total_qty(cart: list[dict]) -> int:
    return sum(int(ci.get("quantity", 0)) for ci in cart)


def _get_cart(session: SessionData) -> list[dict]:
    cart = session.get("cart")
    if not isinstance(cart, list):
        cart = []
    return cart


def get_price(db: Session, category: str, item_id: int) -> float | None:
    """Generic `SELECT price FROM \\`$cat\\` WHERE id=?` — every one of the
    12 category models has a plain `price` column (cake_items keeps one
    alongside price_per_kg), so this single helper replaces the dynamic
    per-file query used throughout the PHP cart endpoints."""
    try:
        model = CATEGORY_MODEL_MAP[ProductCategory(category)]
    except ValueError:
        return None
    row = db.execute(select(model.price).where(model.id == item_id)).first()
    return float(row[0]) if row else None


def add_to_cart(session: SessionData, db: Session, category: str, item_id: int, qty: int, form: dict) -> dict:
    if category not in ALL_CATEGORIES or item_id <= 0:
        return {"ok": False}
    cart = _get_cart(session)
    qty = max(1, min(99, qty))

    if category == "cake_items":
        weight = max(1.0, float(form.get("weight") or 1.0))
        cake = db.get(CakeItem, item_id)
        if not cake:
            return {"ok": False}
        weight = max(float(cake.min_weight), weight)
        price_override = round(weight * float(cake.price_per_kg), 2)
        for it in cart:
            if it.get("category") == "cake_items" and int(it.get("id", -1)) == item_id:
                it.update(weight=weight, price_override=price_override, quantity=1)
                session["cart"] = cart
                return {"ok": True, "count": _total_qty(cart)}
        cart.append({"category": category, "id": item_id, "quantity": 1, "weight": weight, "price_override": price_override})
        session["cart"] = cart
        return {"ok": True, "count": _total_qty(cart)}

    if category in ("pizza_items", "mini_pizza_items"):
        selected_size = form.get("selected_size") if form.get("selected_size") in ("small", "large") else "small"
        cheese_crust = 1 if str(form.get("cheese_crust")) == "1" else 0
        takeaway = 1 if str(form.get("takeaway")) == "1" else 0
        raw_price_override = form.get("price_override")
        price_override = float(raw_price_override) if raw_price_override else None

        if price_override is not None:
            if category == "mini_pizza_items":
                row = db.get(MiniPizzaItem, item_id)
                base_price = float(row.price) if row else None
            else:
                row = db.get(PizzaItem, item_id)
                if not row:
                    base_price = None
                else:
                    base_price = float(row.price_large) if selected_size == "large" else float(row.price)
            if base_price is None:
                return {"ok": False}
            if cheese_crust and category == "pizza_items":
                base_price += 100 if selected_size == "large" else 65
            price_override = base_price

        found = None
        for i, it in enumerate(cart):
            if (
                it.get("category") in ("pizza_items", "mini_pizza_items")
                and int(it.get("id", -1)) == item_id
                and it.get("selected_size", "small") == selected_size
                and it.get("cheese_crust", 0) == cheese_crust
            ):
                found = i
                break

        entry = {"category": category, "id": item_id, "quantity": qty, "selected_size": selected_size, "cheese_crust": cheese_crust}
        if takeaway:
            entry["takeaway"] = takeaway
        if price_override is not None:
            entry["price_override"] = price_override

        if found is not None:
            cart[found]["quantity"] += qty
        else:
            cart.append(entry)
        session["cart"] = cart
        return {"ok": True, "count": _total_qty(cart)}

    if category == "sauces":
        sauce = db.execute(
            select(Sauce).where(Sauce.id == item_id, Sauce.active == True)  # noqa: E712
        ).scalar_one_or_none()
        if not sauce:
            return {"ok": False}
        found = None
        for i, it in enumerate(cart):
            if it.get("category") == "sauces" and int(it.get("id", -1)) == item_id:
                found = i
                break
        if found is not None:
            cart[found]["quantity"] += qty
        else:
            cart.append({"category": "sauces", "id": item_id, "quantity": qty})
        session["cart"] = cart
        return {"ok": True, "count": _total_qty(cart)}

    if category == "ice_cream_items":
        selected_variant = (form.get("selected_variant") or "").strip()
        price_diff = 0.0
        if selected_variant:
            try:
                var = json.loads(selected_variant)
                price_diff = float(var.get("price_diff", 0)) if isinstance(var, dict) else 0.0
            except ValueError:
                pass
        row = db.get(IceCreamItem, item_id)
        if not row:
            return {"ok": False}
        price_override = float(row.price) + price_diff

        found = None
        for i, it in enumerate(cart):
            if (
                it.get("category") == "ice_cream_items"
                and int(it.get("id", -1)) == item_id
                and it.get("selected_variant", "") == selected_variant
            ):
                found = i
                break
        if found is not None:
            cart[found]["quantity"] += qty
        else:
            entry = {"category": category, "id": item_id, "quantity": qty, "price_override": price_override}
            if selected_variant:
                entry["selected_variant"] = selected_variant
            cart.append(entry)
        session["cart"] = cart
        return {"ok": True, "count": _total_qty(cart)}

    # Default/catch-all: coffee, cold drinks, fast food, sushi, salads, desserts
    selected_variant = (form.get("selected_variant") or "").strip()
    raw_price_override = form.get("price_override")
    price_override = float(raw_price_override) if raw_price_override else None

    found = None
    for i, it in enumerate(cart):
        if (
            it.get("category") == category
            and int(it.get("id", -1)) == item_id
            and it.get("selected_variant", "") == selected_variant
        ):
            found = i
            break
    if found is not None:
        cart[found]["quantity"] += qty
    else:
        entry = {"category": category, "id": item_id, "quantity": qty}
        if selected_variant:
            entry["selected_variant"] = selected_variant
        if price_override is not None:
            entry["price_override"] = price_override
        cart.append(entry)
    session["cart"] = cart
    return {"ok": True, "count": _total_qty(cart)}


def update_qty_stepper(session: SessionData, db: Session, category: str, item_id: int, action: str, qty_field: int | None) -> dict:
    if category not in QTY_STEPPER_CATEGORIES or item_id <= 0 or action not in ("increase", "decrease", "set_qty"):
        return {"ok": False}
    cart = _get_cart(session)
    found = None
    for i, ci in enumerate(cart):
        if ci.get("category") == category and int(ci.get("id", -1)) == item_id:
            found = i
            break
    if found is None:
        return {"ok": False}

    if action == "increase":
        cart[found]["quantity"] = int(cart[found].get("quantity", 1)) + 1
    elif action == "set_qty":
        cart[found]["quantity"] = max(1, min(99, int(qty_field or 1)))
    else:
        cart[found]["quantity"] = int(cart[found].get("quantity", 1)) - 1

    new_qty = cart[found]["quantity"]
    removed = False
    if new_qty <= 0:
        cart.pop(found)
        removed = True

    item_total = 0.0
    if not removed:
        price = get_price(db, category, item_id) or 0.0
        item_total = round(price * new_qty, 2)

    cart_total, cart_count = 0.0, 0
    for ci in cart:
        if ci.get("category") not in QTY_STEPPER_CATEGORIES:
            continue
        price = get_price(db, ci["category"], int(ci["id"])) or 0.0
        cart_total += price * int(ci.get("quantity", 1))
        cart_count += int(ci.get("quantity", 1))

    session["cart"] = cart
    return {
        "ok": True, "removed": removed, "new_qty": new_qty, "item_total": item_total,
        "cart_total": round(cart_total, 2), "cart_count": cart_count,
    }


def update_cart_item(session: SessionData, db: Session, index: int, form: dict) -> dict:
    cart = _get_cart(session)
    if index < 0 or index >= len(cart):
        return {"ok": False, "error": "invalid_index"}
    item = cart[index]
    table = item.get("category", "")
    item_id = int(item.get("id", 0))
    if table not in ALL_CATEGORIES:  # update_cart_item.php's own whitelist is the full 12
        return {"ok": False}

    existing_qty = int(item.get("quantity", 1))
    raw_qty = form.get("quantity")
    qty = max(1, min(99, int(raw_qty))) if raw_qty not in (None, "") else existing_qty

    if table == "pizza_items":
        size = form.get("selected_size") if form.get("selected_size") in ("small", "large") else "small"
        crust = 1 if str(form.get("cheese_crust", "0")) == "1" else 0
        row = db.get(PizzaItem, item_id)
        if not row:
            return {"ok": False}
        new_price = float(row.price_large) if size == "large" else float(row.price)
        if crust:
            new_price += 100 if size == "large" else 65
        item["selected_size"] = size
        item["cheese_crust"] = crust
        item["price_override"] = round(new_price, 2)
        item["quantity"] = qty

    elif table in ("fast_food_items", "ice_cream_items"):
        sv_raw = (form.get("selected_variant") or "").strip()
        sv = None
        if sv_raw:
            try:
                sv = json.loads(sv_raw)
            except ValueError:
                sv = None
        model = CATEGORY_MODEL_MAP[ProductCategory(table)]
        row = db.get(model, item_id)
        if not row:
            return {"ok": False}
        price_diff = float(sv.get("price_diff", 0)) if isinstance(sv, dict) else 0.0
        new_price = float(row.price) + price_diff
        if sv_raw:
            item["selected_variant"] = sv_raw
        else:
            item.pop("selected_variant", None)
        item["price_override"] = round(new_price, 2)
        item["quantity"] = qty

    elif table == "cake_items":
        weight = max(0.5, float(form.get("weight") or 1.0))
        row = db.get(CakeItem, item_id)
        if not row:
            return {"ok": False}
        weight = max(float(row.min_weight), weight)
        new_price = round(weight * float(row.price_per_kg), 2)
        item["weight"] = weight
        item["price_override"] = new_price
        item["quantity"] = 1
        qty = 1

    else:
        item["quantity"] = qty
        if item.get("price_override", 0) and float(item["price_override"]) > 0:
            new_price = float(item["price_override"])
        else:
            new_price = get_price(db, table, item_id) or 0.0

    session["cart"] = cart
    return {
        "ok": True,
        "new_price": round(new_price, 2),
        "new_subtotal": round(new_price * qty, 2),
        "new_qty": qty,
        "selected_size": item.get("selected_size"),
        "cheese_crust": int(item["cheese_crust"]) if "cheese_crust" in item else None,
        "selected_variant": item.get("selected_variant"),
    }


def update_cart_variant(session: SessionData, category: str, item_id: int, variant: str) -> dict:
    variant = (variant or "").strip()
    if category not in VARIANT_UPDATE_CATEGORIES or item_id <= 0 or not variant:
        return {"ok": False}
    cart = _get_cart(session)
    found = None
    for i, it in enumerate(cart):
        if it.get("category") == category and int(it.get("id", -1)) == item_id:
            found = i  # keep scanning — PHP keeps the LAST match
    if found is None:
        return {"ok": False}
    cart[found]["selected_variant"] = variant
    session["cart"] = cart
    return {"ok": True}


def remove_from_cart(session: SessionData, db: Session, session_index: int | None, category: str, item_id: int) -> dict:
    cart = _get_cart(session)
    if session_index is not None and 0 <= session_index < len(cart):
        cart.pop(session_index)
    elif category in ALL_CATEGORIES and item_id > 0:
        for i, ci in enumerate(cart):
            if ci.get("category") == category and int(ci.get("id", -1)) == item_id:
                cart.pop(i)
                break
    else:
        return {"ok": False}

    cart_total, cart_count = 0.0, 0
    for ci in cart:
        if ci.get("category") not in ALL_CATEGORIES:
            continue
        price = ci["price_override"] if "price_override" in ci else get_price(db, ci["category"], int(ci["id"]))
        if price is None:
            continue
        cart_total += float(price) * int(ci.get("quantity", 1))
        cart_count += int(ci.get("quantity", 1))

    session["cart"] = cart
    return {"ok": True, "cart_total": round(cart_total, 2), "cart_count": cart_count}


def clear_cart(session: SessionData) -> None:
    session["cart"] = []


def get_cart_preview(session: SessionData, db: Session) -> dict:
    cart = _get_cart(session)
    items = []
    total, count = 0.0, 0
    for si, it in enumerate(cart):
        cat, item_id, qty = it.get("category", ""), int(it.get("id", 0)), int(it.get("quantity", 1))
        if cat not in ALL_CATEGORIES or item_id <= 0:
            continue
        model = CATEGORY_MODEL_MAP[ProductCategory(cat)]
        row = db.execute(select(model.name, model.price, model.image).where(model.id == item_id)).first()
        if not row:
            continue
        price = float(it["price_override"]) if "price_override" in it else float(row.price)
        items.append({
            "session_index": si, "category": cat, "id": item_id,
            "name": row.name, "image": item_img(row.image, prefix=""),
            "price": round(price, 2), "qty": qty,
        })
        total += price * qty
        count += qty
    return {"ok": True, "items": items, "total": round(total, 2), "count": count}


def get_cart_item(session: SessionData, db: Session, index: int | None, category: str, item_id: int, variant: str, selected_size: str, cheese_crust: int) -> dict:
    cart = _get_cart(session)
    cart_entry, cart_index = None, -1

    if index is not None and index >= 0 and index < len(cart):
        cart_entry, cart_index = cart[index], index
    else:
        if category not in CART_ITEM_LOOKUP_CATEGORIES or item_id <= 0:
            return {"ok": False, "error": "invalid_params"}
        for si, it in enumerate(cart):
            if it.get("category") != category or int(it.get("id", 0)) != item_id:
                continue
            if variant:
                if it.get("selected_variant", "") == variant:
                    cart_entry, cart_index = it, si
                    break
            elif category == "pizza_items":
                if it.get("selected_size", "") == selected_size and int(it.get("cheese_crust", 0)) == cheese_crust:
                    cart_entry, cart_index = it, si
                    break
            else:
                cart_entry, cart_index = it, si
                break

    if cart_entry is None:
        return {"ok": False, "error": "item_not_found"}

    category = cart_entry.get("category", "")
    item_id = int(cart_entry.get("id", 0))
    model = CATEGORY_MODEL_MAP[ProductCategory(category)]
    row = db.get(model, item_id)
    if not row:
        return {"ok": False, "error": "db_not_found"}

    result = {
        "ok": True, "cart_index": cart_index, "category": category, "id": row.id,
        "name": row.name, "desc": getattr(row, "description", "") or "",
        "image": item_img(getattr(row, "image", "") or ""),
        "price": float(getattr(row, "price", 0) or 0),
        "quantity": int(cart_entry.get("quantity", 1)),
        "selected_size": cart_entry.get("selected_size"),
        "cheese_crust": int(cart_entry.get("cheese_crust", 0)),
        "selected_variant": cart_entry.get("selected_variant"),
        "weight": float(cart_entry["weight"]) if "weight" in cart_entry else None,
        "price_override": float(cart_entry["price_override"]) if "price_override" in cart_entry else None,
    }
    if category == "pizza_items":
        result["price_large"] = float(row.price_large or 0)
        result["has_size_choice"] = int(bool(row.has_size_choice))
    if category in ("fast_food_items", "ice_cream_items"):
        result["variant_options"] = row.variant_options
    if category == "cake_items":
        result["price_per_kg"] = float(row.price_per_kg or 0)
        result["min_weight"] = float(row.min_weight or 1)

    return result


def resolve_cart_items_full(db: Session, cart: list[dict]) -> list[dict]:
    """Port of pages/cart.php's per-category resolution loop: fetch the
    category-specific column set for each line, overlay session-stored
    overrides (price_override/weight/selected_size/etc.), and compute the
    per-line subtotal. Used by the full /cart page."""
    items: list[dict] = []
    for si, it in enumerate(cart):
        category, item_id = it.get("category"), it.get("id")
        if category not in ALL_CATEGORIES or not item_id:
            continue
        item_id = int(item_id)
        model = CATEGORY_MODEL_MAP[ProductCategory(category)]
        row = db.get(model, item_id)
        if not row:
            continue

        entry = {
            "id": row.id, "name": row.name,
            "description": "" if category == "sauces" else (getattr(row, "description", "") or ""),
            "image": row.image, "price": float(row.price),
        }
        if category == "coffee_items":
            entry["is_cold"] = bool(row.is_cold)
        elif category == "pizza_items":
            entry["is_spicy"] = bool(row.is_spicy)
            entry["has_size_choice"] = bool(row.has_size_choice)
        elif category == "mini_pizza_items":
            entry["is_spicy"] = bool(row.is_spicy)
        elif category in ("fast_food_items", "ice_cream_items"):
            entry["variant_options"] = row.variant_options

        qty = int(it.get("quantity", 1))
        entry["quantity"] = qty
        entry["category"] = category
        if "price_override" in it:
            entry["price"] = float(it["price_override"])
        if "weight" in it:
            entry["weight"] = float(it["weight"])
        if "selected_size" in it:
            entry["selected_size"] = it["selected_size"]
        if "cheese_crust" in it:
            entry["cheese_crust"] = int(it["cheese_crust"])
        if "takeaway" in it:
            entry["takeaway"] = int(it["takeaway"])
        if "selected_variant" in it:
            entry["selected_variant"] = it["selected_variant"]

        entry["session_index"] = si
        entry["subtotal"] = entry["price"] * qty
        items.append(entry)
    return items
