"""Checkout: order creation, cash-vs-card branching, working-hours/
lead-time validation for the pickup time."""
from __future__ import annotations

import datetime
import json
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalog import (
    CakeItem, CoffeeItem, ColdDrinkItem, DessertItem, FastFoodItem,
    MiniPizzaItem, PizzaItem, SaladItem, SushiItem, SushiSet,
)
from app.models.orders import Order, OrderItem
from app.services.checkout import CHECKOUT_CATEGORIES, estimate_prep_minutes, resolve_order_details
from app.services.csrf import CSRFError, verify_csrf
from app.services.media import item_img
from app.services.reminders import schedule_reminders
from app.services.schedule import get_cafe_schedule, get_next_available_time, is_cafe_open_at
from app.services.telegram import notify_new_order
from app.templating import render

router = APIRouter()

KYIV_TZ = ZoneInfo("Europe/Kyiv")
_READY_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$")

_CATEGORY_MODELS = {
    "coffee_items": CoffeeItem, "fast_food_items": FastFoodItem, "pizza_items": PizzaItem,
    "mini_pizza_items": MiniPizzaItem, "cold_drink_items": ColdDrinkItem, "dessert_items": DessertItem,
    "sushi_items": SushiItem, "sushi_sets": SushiSet, "salad_items": SaladItem, "cake_items": CakeItem,
}


@router.get("/checkout")
def checkout_page(request: Request, cancel_order: int | None = None, db: Session = Depends(get_db)):
    session = request.state.session

    if cancel_order:
        db.execute(
            update(Order)
            .where(Order.order_id == cancel_order, Order.payment_status.in_(["pending", ""]), Order.status == "new")
            .values(status="cancelled", payment_status="failed")
        )
        db.commit()
        session.pop("pending_order_id", None)
        session.pop("pending_order_total", None)
        return RedirectResponse("/checkout", status_code=302)

    cart = session.get("cart")
    if not cart:
        return RedirectResponse("/cart", status_code=302)

    if request.method != "POST":
        session.pop("flash_error", None)

    return _render_checkout_form(request, db, cart, error_message="")


def _render_checkout_form(request: Request, db: Session, cart: list[dict], error_message: str, form: dict | None = None):
    session = request.state.session
    user = session.get("user")
    order_details, total = resolve_order_details(db, cart)
    prep_minutes = estimate_prep_minutes(order_details)

    draft = {}
    if request.method != "POST" and session.get("checkout_draft"):
        draft = session.pop("checkout_draft")

    form = form or {}
    first_name = form.get("first_name") or draft.get("first_name") or (user or {}).get("client_name") or ""
    last_name = form.get("last_name") or draft.get("last_name") or (user or {}).get("client_surname") or ""
    phone = form.get("phone") or draft.get("phone") or (user or {}).get("client_PhoneNumber") or ""
    email = (form.get("customer_email") or draft.get("customer_email") or (user or {}).get("email") or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""):
        email = ""
    ready_time = form.get("ready_time") or draft.get("ready_time") or ""
    comment = form.get("comment") or draft.get("comment") or ""
    payment = form.get("payment") or draft.get("payment") or ""
    order_type = form.get("order_type") or draft.get("order_type") or ""
    if order_type not in ("dine_in", "takeaway"):
        order_type = "dine_in"

    next_available = get_next_available_time()
    next_json = json.dumps(
        {"time": next_available["time"], "label": next_available["date_label"] or next_available["date"], "is_today": next_available["is_today"]}
        if next_available else None
    )
    schedule_json = json.dumps(get_cafe_schedule())

    for it in order_details:
        it["image_url"] = item_img(it.get("image", ""))

    has_cakes = any(od["category"] == "cake_items" for od in order_details)

    return render(
        request, "public/checkout.html", page="checkout", page_title="Оформлення замовлення — Coffee Time",
        error_message=error_message, order_details=order_details, total=total, has_cakes=has_cakes,
        first_name=first_name, last_name=last_name, phone=phone, email=email,
        ready_time=ready_time, comment=comment, payment=payment, order_type=order_type,
        schedule_json=schedule_json, next_json=next_json, prep_minutes=prep_minutes,
        user_email=(user or {}).get("email", ""),
        has_pending_order=bool(session.get("pending_order_id")),
    )


@router.post("/checkout")
async def checkout_submit(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    cart = session.get("cart")
    if not cart:
        return RedirectResponse("/cart", status_code=302)

    try:
        await verify_csrf(request)
    except CSRFError as exc:
        session["flash_error"] = exc.message
        return RedirectResponse("/checkout", status_code=303)

    form = dict(await request.form())
    user = session.get("user")
    order_details, total = resolve_order_details(db, cart)
    prep_minutes = estimate_prep_minutes(order_details)

    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()
    phone = (form.get("phone") or "").strip()
    email = (form.get("customer_email") or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""):
        email = ""
    ready_time = (form.get("ready_time") or "").strip()
    comment = form.get("comment") or ""
    payment = form.get("payment") or ""
    order_type = form.get("order_type") if form.get("order_type") in ("dine_in", "takeaway") else "dine_in"

    error_message = ""
    if not first_name or not last_name or not phone or not ready_time or not payment:
        error_message = "Будь ласка, заповніть усі обов'язкові поля."
    else:
        m = _READY_TIME_RE.match(ready_time)
        if not m:
            error_message = "Вкажіть коректний час готовності"
        else:
            order_date = datetime.datetime.strptime(ready_time, "%Y-%m-%d %H:%M").replace(tzinfo=KYIV_TZ)
            now_tz = datetime.datetime.now(KYIV_TZ)
            travel_minutes = max(0, min(60, int(form.get("travel_minutes") or 15)))
            min_time = now_tz + datetime.timedelta(minutes=prep_minutes + travel_minutes)

            if order_date.date() == now_tz.date() and order_date < min_time:
                error_message = "Обраний час вже минув. Оберіть пізніший час."

            if not error_message:
                max_date = (now_tz + datetime.timedelta(days=14)).replace(hour=23, minute=59, second=59)
                if order_date > max_date:
                    error_message = "Можна замовити не більше ніж на 14 днів вперед."

            if not error_message and not is_cafe_open_at(order_date):
                next_t = get_next_available_time()
                suggest = ""
                if next_t:
                    label = (next_t["date_label"] + " ") if next_t["date_label"] else ""
                    suggest = f" Найближчий час: {label}{next_t['time']}"
                error_message = f"Кафе не працює в цей час.{suggest}"

            if not error_message and order_date.date() > now_tz.date() and payment == "cash_on_pickup":
                error_message = "Замовлення на майбутній день приймаються лише з передоплатою карткою онлайн."

    if error_message:
        return _render_checkout_form(request, db, cart, error_message, form)

    user_id = user.get("client_id") if user else None
    order = Order(
        user_id=user_id, total=total, delivery_address="", phone=phone, status="new",
        customer_name=first_name, customer_surname=last_name, customer_email=email,
        comment=comment, ready_time=ready_time, payment_method=payment, order_type=order_type,
    )
    db.add(order)
    db.flush()
    order_id = order.order_id

    for item in order_details:
        db.add(OrderItem(
            order_id=order_id, product_id=item["id"], category=item["category"],
            quantity=item["quantity"], price=item["price"],
            selected_size=item.get("selected_size", "small"),
            selected_variant=item.get("selected_variant"),
            cheese_crust=bool(item.get("cheese_crust", 0)),
            takeaway=bool(item.get("takeaway", 0)),
        ))
        model = _CATEGORY_MODELS[item["category"]]
        db.execute(update(model).where(model.id == item["id"]).values(popularity=model.popularity + item["quantity"]))
    db.commit()

    schedule_reminders(db, order_id, ready_time, email or None)

    if payment != "card_online":
        notify_new_order(
            order_id, first_name, last_name, phone, ready_time, payment, total,
            [{"name": it["name"], "quantity": it["quantity"], "price": it["price"]} for it in order_details],
        )
        session.pop("cart", None)
        session["pending_order_id"] = order_id
        return RedirectResponse("/payment-success", status_code=302)

    # card_online: stash the form for a potential re-render if the user cancels
    # LiqPay and comes back via ?cancel_order=, and go start the LiqPay flow.
    session["checkout_draft"] = {
        "first_name": first_name, "last_name": last_name, "phone": phone,
        "customer_email": email, "ready_time": ready_time, "comment": comment,
        "payment": payment, "order_type": order_type,
    }
    session["pending_order_id"] = order_id
    session["pending_order_total"] = total

    liqpay_oid = f"coffeetime_{order_id}"
    db.execute(update(Order).where(Order.order_id == order_id).values(payment_status="pending", liqpay_order_id=liqpay_oid))
    db.commit()

    return RedirectResponse("/liqpay-checkout", status_code=302)
