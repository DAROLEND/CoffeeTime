"""Checkout: cart -> order lines, prep-time estimate, pickup-time
validation and order creation."""
from __future__ import annotations

import datetime
import math
import re
from zoneinfo import ZoneInfo

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.models.orders import Order, OrderItem
from app.services.cart import resolve_cart_lines
from app.services.schedule import get_next_available_time, is_cafe_open_at

KYIV_TZ = ZoneInfo("Europe/Kyiv")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
READY_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$")
MAX_DAYS_AHEAD = 14

# Every orderable category. Ice cream and sauces used to be left out here,
# which meant they showed in the cart (and its total) but were silently
# dropped from the order itself.
CHECKOUT_CATEGORIES = {
    "coffee_items", "fast_food_items", "pizza_items", "mini_pizza_items",
    "cold_drink_items", "dessert_items", "sushi_items", "sushi_sets",
    "salad_items", "cake_items", "ice_cream_items", "sauces",
}

_PREP_MINUTES_PER_UNIT = {
    "pizza_items": 6, "mini_pizza_items": 5, "sushi_items": 12,
    "fast_food_items": 7, "salad_items": 5, "coffee_items": 3,
    "cold_drink_items": 2, "ice_cream_items": 2,
}


def resolve_order_details(db: Session, cart: list[dict]) -> tuple[list[dict], float]:
    """Cart lines -> order lines with prices re-derived from the DB."""
    items = []
    total = 0.0
    for line in resolve_cart_lines(db, cart, CHECKOUT_CATEGORIES):
        row, it, table = line["row"], line["line"], line["category"]
        entry = {
            "id": row.id, "name": row.name, "image": row.image, "category": table,
            "price": line["price"], "quantity": line["quantity"], "subtotal": line["subtotal"],
        }
        if table == "sushi_sets":
            entry["pieces_count"] = row.pieces_count
        for key in ("selected_size", "selected_variant", "weight"):
            if key in it:
                entry[key] = it[key]
        for key in ("cheese_crust", "takeaway"):
            if key in it:
                entry[key] = int(it[key])
        total += entry["subtotal"]
        items.append(entry)
    return items, round(total, 2)


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


def clean_email(raw: str | None) -> str:
    email = (raw or "").strip()
    return email if EMAIL_RE.match(email) else ""


def validate_ready_time(ready_time: str, payment: str, prep_minutes: int, travel_minutes: int) -> str:
    """Returns an error message, or '' if the pickup time is acceptable:
    well-formed, not in the past (allowing for prep + travel time), at
    most 14 days ahead, inside opening hours, and paid online if it's not
    for today."""
    if not READY_TIME_RE.match(ready_time):
        return "Вкажіть коректний час готовності"
    order_date = datetime.datetime.strptime(ready_time, "%Y-%m-%d %H:%M").replace(tzinfo=KYIV_TZ)
    now_tz = datetime.datetime.now(KYIV_TZ)
    travel_minutes = max(0, min(60, travel_minutes))
    min_time = now_tz + datetime.timedelta(minutes=prep_minutes + travel_minutes)

    if order_date.date() < now_tz.date() or (order_date.date() == now_tz.date() and order_date < min_time):
        return "Обраний час вже минув. Оберіть пізніший час."
    max_date = (now_tz + datetime.timedelta(days=MAX_DAYS_AHEAD)).replace(hour=23, minute=59, second=59)
    if order_date > max_date:
        return "Можна замовити не більше ніж на 14 днів вперед."
    if not is_cafe_open_at(order_date):
        next_t = get_next_available_time()
        suggest = ""
        if next_t:
            label = (next_t["date_label"] + " ") if next_t["date_label"] else ""
            suggest = f" Найближчий час: {label}{next_t['time']}"
        return f"Кафе не працює в цей час.{suggest}"
    if order_date.date() > now_tz.date() and payment == "cash_on_pickup":
        return "Замовлення на майбутній день приймаються лише з передоплатою карткою онлайн."
    return ""


def create_order(db: Session, *, user_id: int | None, order_details: list[dict], total: float, fields: dict) -> int:
    """Insert the order + its lines and bump product popularity."""
    order = Order(
        user_id=user_id, total=total, delivery_address="", phone=fields["phone"], status="new",
        customer_name=fields["first_name"], customer_surname=fields["last_name"],
        customer_email=fields["customer_email"], comment=fields["comment"], ready_time=fields["ready_time"],
        payment_method=fields["payment"], order_type=fields["order_type"],
    )
    db.add(order)
    db.flush()

    for item in order_details:
        db.add(OrderItem(
            order_id=order.order_id, product_id=item["id"], category=item["category"],
            quantity=item["quantity"], price=item["price"],
            selected_size=item.get("selected_size", "small"),
            selected_variant=item.get("selected_variant"),
            cheese_crust=bool(item.get("cheese_crust", 0)),
            takeaway=bool(item.get("takeaway", 0)),
        ))
        model = CATEGORY_MODEL_MAP[ProductCategory(item["category"])]
        if hasattr(model, "popularity"):  # sauces don't track it
            db.execute(update(model).where(model.id == item["id"]).values(popularity=model.popularity + item["quantity"]))
    db.commit()
    return order.order_id
