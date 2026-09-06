"""Port of admin/orders.php + view_order.php + get_order_details.php +
update_order_status.php + bulk_order_status.php + delete_order.php.

The order status state machine was duplicated three times in PHP
(orders.php's JS, update_order_status.php, bulk_order_status.php) — this
module is the single shared implementation the migration plan calls for.
"""
from __future__ import annotations

import json
import math

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.models.orders import Order, OrderItem, OrderRating

STATUS_LABELS = {"new": "Нове", "processing": "В обробці", "ready": "Готово", "done": "Виконано", "cancelled": "Скасовано"}
NEXT_LABELS = {"processing": "→ В обробці", "ready": "→ Готово", "done": "✓ Виконано", "cancelled": "✕ Скасувати"}
TRANSITIONS = {
    "new": ["processing", "done", "cancelled"],
    "processing": ["ready", "done", "cancelled"],
    "ready": ["done"],
    "done": [],
    "cancelled": [],
}

PAYMENT_METHOD_LABELS = {
    "cash_on_pickup": "При отриманні", "card_online": "Картка онлайн (LiqPay)", "card_on_pickup": "Картка у кафе",
}
SIZE_LABELS = {"small": "30 см", "medium": "35 см", "large": "40 см", "xl": "XL"}
SIZED_CATEGORIES = {"pizza_items", "mini_pizza_items", "sushi_sets"}

# Category whitelist shared by orders.php/view_order.php/get_order_details.php
# (each PHP file re-declared this array; identical membership across all three)
ORDER_ITEM_LOOKUP_CATEGORIES = {
    "coffee_items", "fast_food_items", "pizza_items", "mini_pizza_items", "cold_drink_items",
    "dessert_items", "sushi_items", "sushi_sets", "salad_items", "cake_items", "ice_cream_items",
}


def transition_status(db: Session, order_id: int, new_status: str) -> dict:
    """Single shared status-transition function used by both the
    single-order and bulk endpoints."""
    if new_status not in STATUS_LABELS:
        return {"success": False, "error": "Невірні дані"}

    row = db.execute(select(Order.status).where(Order.order_id == order_id)).first()
    if not row:
        return {"success": False, "error": "Замовлення не знайдено"}

    current = row[0].value if hasattr(row[0], "value") else row[0]
    allowed = TRANSITIONS.get(current, [])
    if new_status not in allowed:
        return {
            "success": False,
            "error": f"Перехід із «{STATUS_LABELS.get(current, current)}» в «{STATUS_LABELS.get(new_status, new_status)}» заборонений",
        }

    db.execute(update(Order).where(Order.order_id == order_id).values(status=new_status))
    db.commit()
    return {"success": True, "label": STATUS_LABELS[new_status], "next_allowed": TRANSITIONS.get(new_status, []), "new_status": new_status}


def count_new_orders(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Order).where(Order.status == "new")).scalar_one()


def _decode_variant_opts(item: dict) -> list[str]:
    opts = []
    raw_size = (item.get("selected_size") or "").strip()
    if raw_size and item.get("category") in SIZED_CATEGORIES:
        opts.append(SIZE_LABELS.get(raw_size.lower(), raw_size))
    if item.get("cheese_crust"):
        opts.append("Сирні бортики")
    raw_variant = (item.get("selected_variant") or "").strip()
    if raw_variant:
        try:
            d = json.loads(raw_variant)
        except ValueError:
            d = None
        if isinstance(d, dict):
            parts = []
            if d.get("filling_label"):
                parts.append(d["filling_label"])
            if d.get("size_label"):
                parts.append(d["size_label"])
            if not parts and d.get("scoop_label"):
                parts.append(d["scoop_label"])
            if isinstance(d.get("sauces"), list):
                parts.append(", ".join(str(s) for s in d["sauces"]))
            if parts:
                opts.append(" · ".join(parts))
        else:
            opts.append(raw_variant)
    return opts


def resolve_order_items_for_display(db: Session, order_id: int) -> list[dict]:
    """Fetch order_items + resolve product name/image, decode size/variant
    options into a display-ready list. Shared by orders.php's preloaded
    rows, view_order.php, and get_order_details.php."""
    rows = db.execute(select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)).scalars().all()
    items = []
    for row in rows:
        name, image = "—", ""
        if row.category in ORDER_ITEM_LOOKUP_CATEGORIES:
            model = CATEGORY_MODEL_MAP[ProductCategory(row.category)]
            product = db.get(model, row.product_id)
            if product:
                name = product.name or "—"
                raw_img = product.image or ""
                image = "" if (not raw_img or raw_img == "static/images/menu_items/default.jpg") else raw_img
        item = {
            "product_name": name, "product_image": image, "category": row.category,
            "quantity": row.quantity, "price": float(row.price),
            "selected_size": row.selected_size, "cheese_crust": row.cheese_crust,
            "selected_variant": row.selected_variant,
        }
        item["opts"] = _decode_variant_opts(item)
        items.append(item)
    return items


def get_order_rating(db: Session, order_id: int) -> OrderRating | None:
    return db.execute(select(OrderRating).where(OrderRating.order_id == order_id)).scalar_one_or_none()


def build_orders_where(filters: dict):
    """Builds the list of SQLAlchemy filter clauses for the orders list
    query — port of orders.php's dynamic $where string builder."""
    clauses = []
    if filters.get("status") in STATUS_LABELS:
        clauses.append(Order.status == filters["status"])
    payment = filters.get("payment")
    if payment == "paid":
        clauses.append(Order.payment_status == "paid")
    elif payment == "cash":
        clauses.append(Order.payment_method.like("%cash%"))
    elif payment == "unpaid":
        clauses.append(Order.payment_status.notin_(["paid", "cash"]))
        clauses.append(Order.payment_method.notlike("%cash%"))
    method = filters.get("method")
    if method == "cash":
        clauses.append(Order.payment_method.like("%cash%"))
    elif method == "liqpay":
        clauses.append(Order.payment_method == "card_online")
    elif method == "card_pickup":
        clauses.append(Order.payment_method == "card_on_pickup")
    order_type = filters.get("type")
    if order_type == "takeout":
        clauses.append((Order.delivery_address.is_(None)) | (Order.delivery_address == ""))
    elif order_type == "hall":
        clauses.append((Order.delivery_address.isnot(None)) & (Order.delivery_address != ""))
    search = (filters.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        try:
            search_id = int(search)
        except ValueError:
            search_id = -1
        clauses.append(
            (Order.customer_name.like(like)) | (Order.customer_surname.like(like)) |
            (Order.phone.like(like)) | (Order.order_id == search_id)
        )
    if filters.get("date_from"):
        clauses.append(func.date(Order.created_at) >= filters["date_from"])
    if filters.get("date_to"):
        clauses.append(func.date(Order.created_at) <= filters["date_to"])
    if filters.get("time_from") not in (None, ""):
        clauses.append(func.extract("hour", Order.created_at) >= int(filters["time_from"]))
    if filters.get("time_to") not in (None, ""):
        clauses.append(func.extract("hour", Order.created_at) <= int(filters["time_to"]))
    return clauses
