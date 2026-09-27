"""Customer profile: order history + stats, personal data, password, and
per-order items/rating/repay. Every order endpoint is ownership-checked."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import bad_request, not_found
from app.db.session import get_db
from app.dependencies import require_user
from app.models.auth import User
from app.models.orders import Order, OrderRating
from app.routers.public.session import user_display
from app.schemas.auth import ChangePasswordRequest, MessageResponse
from app.schemas.common import OkResponse
from app.schemas.profile import (
    OrderLines, ProfileUpdateRequest, ProfileView, RateOrderRequest, RepayResult,
)
from app.services.auth import hash_password, verify_password
from app.services.orders_admin import resolve_order_items_for_display
from app.services.profile import get_order_stats, get_orders_with_previews, group_by_recency

router = APIRouter(prefix="/profile", tags=["profile"])

_UK_MONTHS = ["", "січ.", "лют.", "бер.", "квіт.", "трав.", "черв.", "лип.", "серп.", "вер.", "жовт.", "лист.", "груд."]
GROUP_LABELS = {"today": "Сьогодні", "week": "Цього тижня", "earlier": "Раніше"}


def _own_order(db: Session, order_id: int, user_id: int) -> Order | None:
    return db.execute(select(Order).where(Order.order_id == order_id, Order.user_id == user_id)).scalar_one_or_none()


@router.get("", response_model=ProfileView)
def profile(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    user_id = user["client_id"]
    db_user = db.get(User, user_id)
    order_count, total_spent = get_order_stats(db, user_id)
    orders = get_orders_with_previews(db, user_id)
    grouped = group_by_recency(orders)
    initials, display_name = user_display(user)

    def order_out(o: dict) -> dict:
        order = o["order"]
        cls, label = o["pay_badge"]
        return {
            "order_id": order.order_id, "items_count": o["items_count"], "preview_names": o["preview_names"],
            "preview_remaining": o["preview_remaining"], "rating": o["rating"], "is_pending": o["is_pending"],
            "is_done": o["is_done"], "status": o["status_value"], "status_label": o["status_label"],
            "payment_status": o["payment_status_value"], "pay_badge": {"cls": cls, "label": label},
            "total": float(order.total), "created_at": order.created_at.isoformat(timespec="seconds"),
            "ready_time": order.ready_time or "", "comment": order.comment or "",
        }

    return {
        "user": {
            "login": user.get("login") or "", "email": user.get("email") or "",
            "client_name": user.get("client_name") or "", "client_surname": user.get("client_surname") or "",
            "client_PhoneNumber": user.get("client_PhoneNumber") or "",
        },
        "initials": initials,
        "display_name": display_name,
        "order_count": order_count,
        "total_spent": total_spent,
        "joined_at": f"{_UK_MONTHS[db_user.created_at.month]} {db_user.created_at.year}" if db_user and db_user.created_at else "—",
        "groups": [
            {"key": key, "label": GROUP_LABELS[key], "orders": [order_out(o) for o in grouped[key]]}
            for key in ("today", "week", "earlier") if grouped[key]
        ],
        "has_orders": bool(orders),
    }


@router.patch("", response_model=OkResponse)
def update_profile(body: ProfileUpdateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    db_user = db.get(User, user["client_id"])
    if db_user is None:
        raise bad_request("Помилка оновлення даних.")
    db_user.client_name = body.first_name.strip()
    db_user.client_surname = body.last_name.strip()
    db_user.client_PhoneNumber = body.phone.strip()
    db.commit()
    user.update(client_name=db_user.client_name, client_surname=db_user.client_surname, client_PhoneNumber=db_user.client_PhoneNumber)
    request.state.session["user"] = user
    return {"ok": True}


@router.post("/password", response_model=MessageResponse)
def change_password(body: ChangePasswordRequest, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    if not body.current_password or not body.new_password or not body.confirm_password:
        raise bad_request("Заповніть усі поля.")
    if body.new_password != body.confirm_password:
        raise bad_request("Паролі не збігаються.")
    if len(body.new_password) < 6:
        raise bad_request("Мінімум 6 символів.")
    db_user = db.get(User, user["client_id"])
    if db_user is None or not verify_password(body.current_password, db_user.password):
        raise bad_request("Неправильний поточний пароль.", code="invalid_credentials")
    db_user.password = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "Пароль успішно змінено"}


@router.get("/orders/{order_id}/items", response_model=OrderLines)
def order_items(order_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    if _own_order(db, order_id, user["client_id"]) is None:
        raise not_found("Замовлення не знайдено.")
    return {"items": [
        {"name": it["product_name"], "image": it["product_image_url"], "category": it["category"],
         "quantity": it["quantity"], "price": it["price"], "opts": it["opts"]}
        for it in resolve_order_items_for_display(db, order_id)
    ]}


@router.post("/orders/{order_id}/rating", response_model=OkResponse)
def rate_order(order_id: int, body: RateOrderRequest, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    if not 1 <= body.rating <= 5:
        raise bad_request("Оцінка має бути від 1 до 5.", code="invalid")
    user_id = user["client_id"]
    order = _own_order(db, order_id, user_id)
    if order is None or getattr(order.status, "value", order.status) != "done":
        raise not_found("Замовлення не знайдено.")
    existing = db.execute(select(OrderRating).where(OrderRating.order_id == order_id, OrderRating.user_id == user_id)).scalar_one_or_none()
    if existing:
        existing.rating = body.rating
    else:
        db.add(OrderRating(order_id=order_id, user_id=user_id, rating=body.rating))
    db.commit()
    return {"ok": True}


@router.post("/orders/{order_id}/repay", response_model=RepayResult)
def repay(order_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """Retry the LiqPay payment of an unpaid online order."""
    order = db.execute(
        select(Order).where(Order.order_id == order_id, Order.user_id == user["client_id"], Order.payment_status.in_(["pending", ""]))
    ).scalar_one_or_none()
    if order is None:
        raise bad_request("Це замовлення не потребує оплати.", code="not_payable")
    session = request.state.session
    session["pending_order_id"] = order.order_id
    session["pending_order_total"] = float(order.total)
    return {"redirect": "/liqpay-checkout?back=profile"}
