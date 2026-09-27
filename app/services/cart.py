"""
Cart business logic: add/update/remove cart lines and cart resolution
for the cart page, the header mini-cart and checkout.

`session["cart"]` is a flat list of dicts:
    {category, id, quantity,
     [weight], [selected_size], [cheese_crust], [takeaway],
     [selected_variant: canonical JSON string], [price_override]}

Lines are addressed by their list index everywhere the client edits
them: two lines can share a category+id (a small and a large pizza), so
category+id alone is ambiguous.

`price_override` is only a snapshot of the server-computed unit price at
the time the line was written. Anything that shows or charges a price
re-derives it from the DB via app/services/pricing.py, so a price change
in the admin panel applies to carts that already hold the item.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.middleware.session import SessionData
from app.models.catalog import Sauce
from app.services.media import item_img
from app.services.pricing import (
    InvalidVariant, clamp_cake_weight, parse_variant_options, pizza_size, resolve_variant, unit_price,
)

ALL_CATEGORIES = {c.value for c in ProductCategory}  # 12
PIZZA_CATEGORIES = {"pizza_items", "mini_pizza_items"}

CAT_LABELS = {
    "coffee_items": "Кава", "cold_drink_items": "Холодні напої", "fast_food_items": "Фаст-фуд",
    "pizza_items": "Піца", "mini_pizza_items": "Міні-піца", "sushi_items": "Суші",
    "sushi_sets": "Суші-сети", "salad_items": "Салати", "dessert_items": "Десерти",
    "ice_cream_items": "Морозиво", "cake_items": "Торти", "sauces": "Соуси",
}


def total_qty(cart: list[dict]) -> int:
    return sum(int(ci.get("quantity", 0)) for ci in cart)


def get_cart(session: SessionData) -> list[dict]:
    cart = session.get("cart")
    if not isinstance(cart, list):
        cart = []
    return cart


def cart_keys(cart: list[dict]) -> list[str]:
    """`<category>_<id>` for every line; the menu uses it for "in cart" badges."""
    return sorted({f"{ci['category']}_{ci['id']}" for ci in cart if "category" in ci and "id" in ci})


def _row(db: Session, category: str, item_id: int):
    try:
        model = CATEGORY_MODEL_MAP[ProductCategory(category)]
    except ValueError:
        return None
    return db.get(model, item_id)


def get_price(db: Session, category: str, item_id: int) -> float | None:
    row = _row(db, category, item_id)
    return float(row.price) if row is not None else None


def _qty(raw, default: int = 1) -> int:
    try:
        return max(1, min(99, int(raw)))
    except (TypeError, ValueError):
        return default


def _result(cart: list[dict], index: int) -> dict:
    return {"ok": True, "count": total_qty(cart), "index": index}


def add_to_cart(session: SessionData, db: Session, category: str, item_id: int, qty: int, form: dict) -> dict:
    """Add (or merge into) a cart line. `form` carries only the line's
    parameters (weight, selected_size, cheese_crust, takeaway,
    selected_variant); a `price_override` in it is ignored."""
    if category not in ALL_CATEGORIES or item_id <= 0:
        return {"ok": False}
    cart = get_cart(session)
    qty = _qty(qty)

    if category == "sauces":
        row = db.execute(select(Sauce).where(Sauce.id == item_id, Sauce.active == True)).scalar_one_or_none()  # noqa: E712
    else:
        row = _row(db, category, item_id)
    if row is None:
        return {"ok": False}

    if category == "cake_items":
        # At most one line per cake: re-adding updates the weight.
        weight = clamp_cake_weight(row, form.get("weight"))
        price = unit_price(category, row, {"weight": weight})
        for i, it in enumerate(cart):
            if it.get("category") == "cake_items" and int(it.get("id", -1)) == item_id:
                it.update(weight=weight, price_override=price, quantity=1)
                session["cart"] = cart
                return _result(cart, i)
        cart.append({"category": category, "id": item_id, "quantity": 1, "weight": weight, "price_override": price})
        session["cart"] = cart
        return _result(cart, len(cart) - 1)

    if category in PIZZA_CATEGORIES:
        selected_size = pizza_size(row, form.get("selected_size")) if category == "pizza_items" else "small"
        cheese_crust = 1 if category == "pizza_items" and str(form.get("cheese_crust")) == "1" else 0
        takeaway = 1 if str(form.get("takeaway")) == "1" else 0
        entry = {"category": category, "id": item_id, "quantity": qty, "selected_size": selected_size, "cheese_crust": cheese_crust}
        if takeaway:
            entry["takeaway"] = takeaway
        entry["price_override"] = unit_price(category, row, entry)

        # Same pizza + size + crust merges; any other combination is its own line.
        for i, it in enumerate(cart):
            if (
                it.get("category") == category
                and int(it.get("id", -1)) == item_id
                and it.get("selected_size", "small") == selected_size
                and int(it.get("cheese_crust", 0)) == cheese_crust
            ):
                it["quantity"] = min(99, int(it.get("quantity", 1)) + qty)
                session["cart"] = cart
                return _result(cart, i)
        cart.append(entry)
        session["cart"] = cart
        return _result(cart, len(cart) - 1)

    # Everything else: coffee, cold drinks, desserts, sushi, salads, sauces,
    # plus the variant-priced fast food and ice cream. category + id +
    # canonical variant identify a line.
    selected_variant = None
    if category in ("fast_food_items", "ice_cream_items"):
        try:
            selected_variant, _ = resolve_variant(row.variant_options, form.get("selected_variant"))
        except InvalidVariant:
            return {"ok": False, "error": "invalid_variant"}

    for i, it in enumerate(cart):
        if (
            it.get("category") == category
            and int(it.get("id", -1)) == item_id
            and (it.get("selected_variant") or None) == selected_variant
        ):
            it["quantity"] = min(99, int(it.get("quantity", 1)) + qty)
            session["cart"] = cart
            return _result(cart, i)

    entry = {"category": category, "id": item_id, "quantity": qty}
    if selected_variant:
        entry["selected_variant"] = selected_variant
    if category != "sauces":
        entry["price_override"] = unit_price(category, row, entry)
    cart.append(entry)
    session["cart"] = cart
    return _result(cart, len(cart) - 1)


def update_cart_item(session: SessionData, db: Session, index: int, form: dict) -> dict:
    """Change one line's quantity and/or options. Only the keys present in
    `form` are changed. Cakes always stay at quantity 1."""
    cart = get_cart(session)
    if index < 0 or index >= len(cart):
        return {"ok": False, "error": "invalid_index"}
    item = cart[index]
    category = item.get("category", "")
    if category not in ALL_CATEGORIES:
        return {"ok": False}
    row = _row(db, category, int(item.get("id", 0)))
    if row is None:
        return {"ok": False, "error": "db_not_found"}

    if form.get("quantity") not in (None, ""):
        item["quantity"] = _qty(form.get("quantity"), int(item.get("quantity", 1)))

    if category == "pizza_items":
        if "selected_size" in form:
            item["selected_size"] = pizza_size(row, form.get("selected_size"))
        if "cheese_crust" in form:
            item["cheese_crust"] = 1 if str(form.get("cheese_crust")) == "1" else 0
    elif category in ("fast_food_items", "ice_cream_items") and "selected_variant" in form:
        try:
            canonical, _ = resolve_variant(row.variant_options, form.get("selected_variant"))
        except InvalidVariant:
            return {"ok": False, "error": "invalid_variant"}
        if canonical:
            item["selected_variant"] = canonical
        else:
            item.pop("selected_variant", None)
    elif category == "cake_items":
        if "weight" in form:
            item["weight"] = clamp_cake_weight(row, form.get("weight"))
        item["quantity"] = 1

    new_price = unit_price(category, row, item)
    if category != "sauces":
        item["price_override"] = new_price
    qty = int(item.get("quantity", 1))

    # Two lines can now describe the same product+options; fold them together.
    for j, other in enumerate(cart):
        if j != index and _same_line(other, item):
            other["quantity"] = min(99, int(other.get("quantity", 1)) + qty) if category != "cake_items" else 1
            cart.pop(index)
            session["cart"] = cart
            return {
                "ok": True, "merged": True, "index": j if j < index else j - 1,
                "new_price": new_price, "new_qty": int(other["quantity"]),
                "new_subtotal": round(new_price * int(other["quantity"]), 2),
                "selected_size": other.get("selected_size"),
                "cheese_crust": int(other["cheese_crust"]) if "cheese_crust" in other else None,
                "selected_variant": other.get("selected_variant"),
            }

    session["cart"] = cart
    return {
        "ok": True, "merged": False, "index": index,
        "new_price": new_price, "new_qty": qty, "new_subtotal": round(new_price * qty, 2),
        "selected_size": item.get("selected_size"),
        "cheese_crust": int(item["cheese_crust"]) if "cheese_crust" in item else None,
        "selected_variant": item.get("selected_variant"),
    }


def _same_line(a: dict, b: dict) -> bool:
    return (
        a.get("category") == b.get("category")
        and int(a.get("id", -1)) == int(b.get("id", -2))
        and a.get("selected_size", "small") == b.get("selected_size", "small")
        and int(a.get("cheese_crust", 0)) == int(b.get("cheese_crust", 0))
        and (a.get("selected_variant") or None) == (b.get("selected_variant") or None)
    )


def remove_from_cart(session: SessionData, db: Session, session_index: int | None, category: str = "", item_id: int = 0) -> dict:
    cart = get_cart(session)
    if session_index is not None and 0 <= session_index < len(cart):
        cart.pop(session_index)
    elif category in ALL_CATEGORIES and item_id > 0:
        for i, ci in enumerate(cart):
            if ci.get("category") == category and int(ci.get("id", -1)) == item_id:
                cart.pop(i)
                break
    else:
        return {"ok": False}
    session["cart"] = cart
    lines = resolve_cart_lines(db, cart)
    return {
        "ok": True,
        "cart_total": round(sum(line["subtotal"] for line in lines), 2),
        "cart_count": sum(line["quantity"] for line in lines),
    }


def clear_cart(session: SessionData) -> None:
    session["cart"] = []


def resolve_cart_lines(db: Session, cart: list[dict], categories: set[str] | None = None) -> list[dict]:
    """Pair every cart line with its DB row and a freshly computed unit
    price. Lines whose product no longer exists are skipped."""
    lines = []
    for si, it in enumerate(cart):
        category, item_id = it.get("category"), it.get("id")
        if category not in ALL_CATEGORIES or not item_id:
            continue
        if categories is not None and category not in categories:
            continue
        row = _row(db, category, int(item_id))
        if row is None:
            continue
        qty = int(it.get("quantity", 1))
        price = unit_price(category, row, it)
        lines.append({
            "session_index": si, "category": category, "row": row, "line": it,
            "quantity": qty, "price": price, "subtotal": round(price * qty, 2),
        })
    return lines


def get_cart_preview(session: SessionData, db: Session) -> dict:
    items = []
    total, count = 0.0, 0
    for line in resolve_cart_lines(db, get_cart(session)):
        row = line["row"]
        items.append({
            "session_index": line["session_index"], "category": line["category"], "id": row.id,
            "name": row.name, "image": item_img(row.image),
            "price": line["price"], "qty": line["quantity"],
        })
        total += line["subtotal"]
        count += line["quantity"]
    return {"ok": True, "items": items, "total": round(total, 2), "count": count}


def get_cart_item(session: SessionData, db: Session, index: int) -> dict:
    """Everything the cart page's "edit options" modal needs for one line."""
    cart = get_cart(session)
    if index < 0 or index >= len(cart):
        return {"ok": False, "error": "item_not_found"}
    entry = cart[index]
    category = entry.get("category", "")
    if category not in ALL_CATEGORIES:
        return {"ok": False, "error": "item_not_found"}
    row = _row(db, category, int(entry.get("id", 0)))
    if row is None:
        return {"ok": False, "error": "db_not_found"}

    result = {
        "ok": True, "cart_index": index, "category": category, "id": row.id,
        "name": row.name, "desc": getattr(row, "description", "") or "",
        "image": item_img(getattr(row, "image", "") or ""),
        "price": float(getattr(row, "price", 0) or 0),
        "unit_price": unit_price(category, row, entry),
        "quantity": int(entry.get("quantity", 1)),
        "selected_size": entry.get("selected_size"),
        "cheese_crust": int(entry.get("cheese_crust", 0)),
        "selected_variant": entry.get("selected_variant"),
        "weight": float(entry["weight"]) if "weight" in entry else None,
        "price_large": None, "has_size_choice": None, "variant_options": None,
        "price_per_kg": None, "min_weight": None,
    }
    if category == "pizza_items":
        result["price_large"] = float(row.price_large or 0)
        result["has_size_choice"] = bool(row.has_size_choice)
    if category in ("fast_food_items", "ice_cream_items"):
        result["variant_options"] = parse_variant_options(row.variant_options)
    if category == "cake_items":
        result["price_per_kg"] = float(row.price_per_kg or 0)
        result["min_weight"] = float(row.min_weight or 1)
    return result


def opt_tags(category: str, line: dict, row) -> list[str]:
    """Short human-readable labels for a line's options ("40 см",
    "Сирний бортик", "1.5 кг", the chosen filling, ...)."""
    tags = []
    if line.get("selected_size") and category in PIZZA_CATEGORIES:
        tags.append("20 см" if category == "mini_pizza_items" else ("40 см" if line["selected_size"] == "large" else "30 см"))
    if int(line.get("cheese_crust") or 0):
        tags.append("Сирний бортик")
    if int(line.get("takeaway") or 0):
        tags.append("З собою")
    if line.get("weight"):
        tags.append(f"{float(line['weight'])} кг")
    if category in PIZZA_CATEGORIES and getattr(row, "is_spicy", False):
        tags.append("Гостра")
    if category == "coffee_items" and getattr(row, "is_cold", False):
        tags.append("Холодна")
    if line.get("selected_variant"):
        try:
            sv = json.loads(line["selected_variant"])
        except ValueError:
            sv = None
        if isinstance(sv, dict):
            if sv.get("type") == "filling":
                fl = sv.get("filling_label", "")
                if sv.get("size_label"):
                    fl += " · " + sv["size_label"]
                if fl:
                    tags.append(fl)
            elif sv.get("type") == "sauce" and sv.get("label"):
                tags.append(sv["label"])
            elif "scoop_label" in sv:
                tags.append(sv["scoop_label"])
    return tags


def item_word(n: int) -> str:
    n = abs(n) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return "товарів"
    if n1 == 1:
        return "товар"
    if 2 <= n1 <= 4:
        return "товари"
    return "товарів"


def build_cart_view(session: SessionData, db: Session) -> dict:
    """The full cart page: lines grouped by category (mini pizza shows
    under pizza), totals, and the menu category to go back to."""
    lines = resolve_cart_lines(db, get_cart(session))
    items = []
    for line in lines:
        row, category = line["row"], line["category"]
        it = line["line"]
        show_edit = (category == "pizza_items" and bool(row.has_size_choice)) or (
            category in ("fast_food_items", "ice_cream_items") and bool(row.variant_options)
        )
        items.append({
            "session_index": line["session_index"], "category": category, "id": row.id,
            "name": row.name,
            "description": "" if category == "sauces" else (getattr(row, "description", "") or ""),
            "image": item_img(row.image), "price": line["price"], "quantity": line["quantity"],
            "subtotal": line["subtotal"], "opt_tags": opt_tags(category, it, row),
            "editable": show_edit, "weight": float(it["weight"]) if "weight" in it else None,
        })

    groups: dict[str, list[dict]] = {}
    for it in items:
        key = "pizza_items" if it["category"] == "mini_pizza_items" else it["category"]
        groups.setdefault(key, []).append(it)

    total_q = sum(it["quantity"] for it in items)
    return {
        "items": items,
        "groups": [{"key": k, "label": CAT_LABELS.get(k, k), "items": v} for k, v in groups.items()],
        "total": round(sum(it["subtotal"] for it in items), 2),
        "total_qty": total_q,
        "item_count": len(items),
        "item_word": item_word(len(items)),
        "back_category": session.get("lastCategory", "coffee_items"),
    }
