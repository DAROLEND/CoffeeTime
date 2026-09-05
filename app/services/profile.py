"""Port of pages/profile.php's local helper functions: profPayBadge(),
profStatusBadge(), needsPayment(), plus the order-history aggregation
(preview item names, ratings, today/week/earlier grouping) factored out
of the route for testability."""
from __future__ import annotations

import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.models.orders import Order, OrderItem, OrderRating

_STATUS_LABELS = {"processing": "В обробці", "ready": "Готово", "done": "Виконано"}


def _enum_value(x) -> str:
    """SQLAlchemy's Enum type converts DB values back to the Python enum on
    read, but an object still attached to the session with a plain string
    assigned in Python (e.g. `Order(status="done")`, common in tests and
    any in-memory-only construction) keeps that literal string until the
    row is expired/refreshed. Guard against both shapes uniformly."""
    return x.value if hasattr(x, "value") else (x or "")

# profile.php's own whitelist for resolving order_items -> product name previews
PREVIEW_CATEGORIES = {
    "coffee_items", "fast_food_items", "pizza_items", "cold_drink_items",
    "dessert_items", "sushi_items", "sushi_sets", "salad_items", "cake_items",
    "ice_cream_items", "mini_pizza_items",
}


def pay_badge_label(order: Order) -> tuple[str, str]:
    """Returns (css_class, label) for profPayBadge()."""
    ps = _enum_value(order.payment_status)
    pm = order.payment_method or ""
    if ps == "paid":
        return "ppay-paid", "Оплачено"
    if "cash" in pm:
        return "ppay-cash", "Готівка"
    return "ppay-pending", "Не оплачено"


def status_badge_label(status: str) -> str | None:
    return _STATUS_LABELS.get(status)


def needs_payment(order: Order) -> bool:
    if order.payment_method != "card_online":
        return False
    if _enum_value(order.payment_status) == "paid":
        return False
    if _enum_value(order.status) == "cancelled":
        return False
    # Only show "Pay" for orders less than 24h old
    age = datetime.datetime.utcnow() - order.created_at
    return age.total_seconds() < 86400


def get_order_stats(db: Session, user_id: int) -> tuple[int, float]:
    row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((Order.status != "cancelled", Order.total), else_=0)), 0),
        ).select_from(Order).where(Order.user_id == user_id, Order.status != "cancelled")
    ).first()
    return int(row[0] or 0), float(row[1] or 0)


def get_orders_with_previews(db: Session, user_id: int) -> list[dict]:
    orders = db.execute(
        select(Order, func.count(OrderItem.id).label("items_count"))
        .outerjoin(OrderItem, OrderItem.order_id == Order.order_id)
        .where(Order.user_id == user_id, Order.status != "cancelled")
        .group_by(Order.order_id)
        .order_by(Order.created_at.desc())
    ).all()
    if not orders:
        return []

    order_ids = [o.Order.order_id for o in orders]
    item_rows = db.execute(
        select(OrderItem.order_id, OrderItem.product_id, OrderItem.category)
        .where(OrderItem.order_id.in_(order_ids))
        .order_by(OrderItem.order_id, OrderItem.id)
    ).all()

    by_order: dict[int, list] = {}
    for r in item_rows:
        bucket = by_order.setdefault(r.order_id, [])
        if len(bucket) < 2:
            bucket.append(r)

    preview_names: dict[int, list[str]] = {}
    for oid, rows in by_order.items():
        names = []
        for r in rows:
            if r.category not in PREVIEW_CATEGORIES:
                names.append("Позиція")
                continue
            model = CATEGORY_MODEL_MAP[ProductCategory(r.category)]
            product = db.get(model, r.product_id)
            if product and product.name:
                names.append(product.name)
        preview_names[oid] = names

    ratings = {}
    rating_rows = db.execute(
        select(OrderRating).where(OrderRating.user_id == user_id, OrderRating.order_id.in_(order_ids))
    ).scalars().all()
    for r in rating_rows:
        ratings[r.order_id] = r.rating

    result = []
    for row in orders:
        order = row.Order
        names = preview_names.get(order.order_id, [])
        result.append({
            "order": order,
            "items_count": row.items_count,
            "preview_names": names,
            "preview_remaining": max(0, row.items_count - len(names)),
            "rating": ratings.get(order.order_id),
            "is_pending": needs_payment(order),
            "is_done": _enum_value(order.status) == "done",
            "status_value": _enum_value(order.status),
            "payment_status_value": _enum_value(order.payment_status),
            "pay_badge": pay_badge_label(order),
            "status_label": status_badge_label(_enum_value(order.status)),
        })
    return result


def group_by_recency(orders: list[dict]) -> dict[str, list[dict]]:
    today = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    grouped: dict[str, list[dict]] = {"today": [], "week": [], "earlier": []}
    for o in orders:
        created = o["order"].created_at
        if created >= today:
            grouped["today"].append(o)
        elif created >= week_ago:
            grouped["week"].append(o)
        else:
            grouped["earlier"].append(o)
    return grouped
