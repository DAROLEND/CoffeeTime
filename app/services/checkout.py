"""Checkout cart-resolution and prep-time estimate. The order-creation
logic itself lives in the router since it's mostly sequential INSERT
statements, not reusable branching."""
from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory

# Deliberately excludes ice_cream_items and sauces: ice cream travels
# inside a fast_food/dessert variant rather than as its own line, and
# sauces are add-ons, not top-level checkout products.
CHECKOUT_CATEGORIES = {
    "coffee_items", "fast_food_items", "pizza_items", "mini_pizza_items",
    "cold_drink_items", "dessert_items", "sushi_items", "sushi_sets",
    "salad_items", "cake_items",
}

_PREP_MINUTES_PER_UNIT = {
    "pizza_items": 6, "mini_pizza_items": 5, "sushi_items": 12,
    "fast_food_items": 7, "salad_items": 5, "coffee_items": 3,
    "cold_drink_items": 2, "ice_cream_items": 2,
}


def resolve_order_details(db: Session, cart: list[dict]) -> tuple[list[dict], float]:
    items = []
    total = 0.0
    for ci in cart:
        table = ci.get("category")
        item_id = ci.get("id")
        if table not in CHECKOUT_CATEGORIES or not item_id:
            continue
        item_id = int(item_id)
        model = CATEGORY_MODEL_MAP[ProductCategory(table)]
        row = db.get(model, item_id)
        if not row:
            continue

        entry = {"id": row.id, "name": row.name, "image": row.image, "price": float(row.price), "category": table}
        if table == "sushi_sets":
            entry["pieces_count"] = row.pieces_count

        qty = int(ci.get("quantity", 1))
        entry["quantity"] = qty
        if "price_override" in ci:
            entry["price"] = float(ci["price_override"])
            entry["weight"] = ci.get("weight", 1)
        if "selected_size" in ci:
            entry["selected_size"] = ci["selected_size"]
        if "cheese_crust" in ci:
            entry["cheese_crust"] = int(ci["cheese_crust"])
        if "takeaway" in ci:
            entry["takeaway"] = int(ci["takeaway"])
        if "selected_variant" in ci:
            entry["selected_variant"] = ci["selected_variant"]

        entry["subtotal"] = entry["price"] * qty
        total += entry["subtotal"]
        items.append(entry)
    return items, total


def estimate_prep_minutes(order_details: list[dict]) -> int:
    """Kitchen works in parallel; total time is driven by the heaviest
    item type, rounded up to a 15-minute slot, capped at 90 minutes."""
    prep = 0
    for item in order_details:
        qty = int(item.get("quantity", 1))
        category = item.get("category")
        if category == "sushi_sets":
            pieces = int(item.get("pieces_count") or 0)
            # ~0.7 min/piece, minimum 20 min per set if pieces_count is unset
            per_set = math.ceil(pieces * 0.7) if pieces > 0 else 20
            prep += qty * per_set
        else:
            prep += qty * _PREP_MINUTES_PER_UNIT.get(category, 0)
    return min(90, -(-prep // 15) * 15)
