"""Checkout: the form's data (cart summary, schedule, prefill) and order
creation with cash-vs-card branching and pickup-time validation."""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.errors import ApiError, bad_request
from app.db.session import get_db
from app.models.orders import Order
from app.schemas.checkout import CheckoutRequest, CheckoutResult, CheckoutView
from app.schemas.common import OkResponse
from app.services.checkout import (
    KYIV_TZ, MAX_DAYS_AHEAD, clean_email, create_order, estimate_prep_minutes,
    resolve_order_details, validate_ready_time,
)
from app.services.media import item_img
from app.services.reminders import schedule_reminders
from app.services.schedule import get_cafe_schedule, get_next_available_time
from app.services.telegram import notify_new_order

router = APIRouter(prefix="/checkout", tags=["checkout"])

PAYMENT_METHODS = {"cash_on_pickup", "card_online"}
MISSING_FIELDS = "Будь ласка, заповніть усі обов'язкові поля."


def _require_cart(session) -> list[dict]:
    cart = session.get("cart")
    if not cart:
        raise ApiError(409, "Кошик порожній.", code="cart_empty")
    return cart


@router.get("", response_model=CheckoutView)
def checkout_view(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    cart = _require_cart(session)
    user = session.get("user") or {}
    order_details, total = resolve_order_details(db, cart)

    # A card payment the customer backed out of: prefill what they typed.
    draft = session.get("checkout_draft") or {}
    order_type = draft.get("order_type") if draft.get("order_type") in ("dine_in", "takeaway") else "dine_in"
    next_available = get_next_available_time()

    return {
        "items": [
            {"id": it["id"], "category": it["category"], "name": it["name"], "image": item_img(it.get("image")),
             "price": it["price"], "quantity": it["quantity"], "subtotal": it["subtotal"]}
            for it in order_details
        ],
        "total": total,
        "has_cakes": any(it["category"] == "cake_items" for it in order_details),
        "prep_minutes": estimate_prep_minutes(order_details),
        "schedule": {str(k): v for k, v in get_cafe_schedule().items()},
        "next_available": (
            {"time": next_available["time"], "label": next_available["date_label"] or next_available["date"],
             "is_today": next_available["is_today"]}
            if next_available else None
        ),
        "server_now": datetime.datetime.now(KYIV_TZ).strftime("%Y-%m-%dT%H:%M:%S"),
        "max_days_ahead": MAX_DAYS_AHEAD,
        "prefill": {
            "first_name": draft.get("first_name") or user.get("client_name") or "",
            "last_name": draft.get("last_name") or user.get("client_surname") or "",
            "phone": draft.get("phone") or user.get("client_PhoneNumber") or "",
            "customer_email": clean_email(draft.get("customer_email") or user.get("email")),
            "ready_time": draft.get("ready_time") or "",
            "comment": draft.get("comment") or "",
            "payment": draft.get("payment") or "",
            "order_type": order_type,
        },
        "user_email": user.get("email") or "",
        "has_pending_order": bool(session.get("pending_order_id")),
    }


@router.post("", response_model=CheckoutResult)
def place_order(body: CheckoutRequest, request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    cart = _require_cart(session)
    user = session.get("user")
    order_details, total = resolve_order_details(db, cart)
    if not order_details:
        raise ApiError(409, "Кошик порожній.", code="cart_empty")

    fields = {
        "first_name": body.first_name.strip(),
        "last_name": body.last_name.strip(),
        "phone": body.phone.strip(),
        "customer_email": clean_email(body.customer_email),
        "ready_time": body.ready_time.strip(),
        "comment": body.comment,
        "payment": body.payment,
        "order_type": body.order_type if body.order_type in ("dine_in", "takeaway") else "dine_in",
    }
    if not all(fields[k] for k in ("first_name", "last_name", "phone", "ready_time", "payment")):
        raise bad_request(MISSING_FIELDS, code="missing_fields")
    if fields["payment"] not in PAYMENT_METHODS:
        raise bad_request("Оберіть спосіб оплати.", code="invalid_payment")
    error = validate_ready_time(fields["ready_time"], fields["payment"], estimate_prep_minutes(order_details), body.travel_minutes)
    if error:
        raise bad_request(error, code="invalid_ready_time")

    order_id = create_order(db, user_id=user.get("client_id") if user else None, order_details=order_details, total=total, fields=fields)
    schedule_reminders(db, order_id, fields["ready_time"], fields["customer_email"] or None)

    if fields["payment"] != "card_online":
        notify_new_order(
            order_id, fields["first_name"], fields["last_name"], fields["phone"], fields["ready_time"],
            fields["payment"], total,
            [{"name": it["name"], "quantity": it["quantity"], "price": it["price"]} for it in order_details],
        )
        session.pop("cart", None)
        session.pop("checkout_draft", None)
        session["pending_order_id"] = order_id
        return {"order_id": order_id, "next": "success"}

    # card_online: keep the cart until payment succeeds, and remember the
    # form in case the customer backs out of LiqPay (see cancel_pending).
    session["checkout_draft"] = {k: v for k, v in fields.items()}
    session["pending_order_id"] = order_id
    session["pending_order_total"] = total
    db.execute(update(Order).where(Order.order_id == order_id).values(payment_status="pending", liqpay_order_id=f"coffeetime_{order_id}"))
    db.commit()
    return {"order_id": order_id, "next": "liqpay"}


@router.post("/cancel-pending", response_model=OkResponse)
def cancel_pending(request: Request, db: Session = Depends(get_db)):
    """The customer went back from the LiqPay page: cancel the unpaid order
    so it doesn't linger as "new", and let them edit and resubmit."""
    session = request.state.session
    order_id = int(session.get("pending_order_id") or 0)
    if order_id:
        db.execute(
            update(Order)
            .where(Order.order_id == order_id, Order.payment_status.in_(["pending", ""]), Order.status == "new")
            .values(status="cancelled", payment_status="failed")
        )
        db.commit()
    session.pop("pending_order_id", None)
    session.pop("pending_order_total", None)
    return {"ok": True}
