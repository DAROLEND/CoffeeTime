"""Port of pages/profile.php, forms/rate_order.php, pages/get_order_items.php."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.db.session import get_db
from app.dependencies import require_user
from app.models.auth import User
from app.models.orders import Order, OrderRating
from app.services.auth import hash_password, verify_password
from app.services.csrf import CSRFError, verify_csrf
from app.services.media import item_img
from app.services.profile import get_order_stats, get_orders_with_previews, group_by_recency
from app.templating import render

router = APIRouter()

_UK_MONTHS = ["", "січ.", "лют.", "бер.", "квіт.", "трав.", "черв.", "лип.", "серп.", "вер.", "жовт.", "лист.", "груд."]


@router.get("/profile")
def profile_page(request: Request, tab: str = "orders", repay: int | None = None, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    session = request.state.session
    user_id = user["client_id"]

    if repay:
        order = db.execute(
            select(Order).where(Order.order_id == repay, Order.user_id == user_id, Order.payment_status.in_(["pending", ""]))
        ).scalar_one_or_none()
        if order:
            session["pending_order_id"] = order.order_id
            session["pending_order_total"] = float(order.total)
            return RedirectResponse("/liqpay-checkout?back=profile", status_code=302)
        return RedirectResponse("/profile?tab=orders", status_code=302)

    saved_flag = session.pop("prof_saved", None)

    db_user = db.get(User, user_id)
    if db_user and db_user.created_at and "created_at" not in user:
        user["created_at"] = db_user.created_at
        session["user"] = user

    order_count, total_spent = get_order_stats(db, user_id)

    joined_at = "—"
    if db_user and db_user.created_at:
        joined_at = f"{_UK_MONTHS[db_user.created_at.month]} {db_user.created_at.year}"

    orders = get_orders_with_previews(db, user_id)
    grouped = group_by_recency(orders)
    group_labels = {"today": "Сьогодні", "week": "Цього тижня", "earlier": "Раніше"}

    first_name = user.get("client_name") or ""
    last_name = user.get("client_surname") or ""
    initials = ((first_name[:1] + last_name[:1]) or user.get("login", "U")[:1]).upper()
    display_name = f"{first_name} {last_name}".strip() or user.get("login", "")

    active_tab = "settings" if tab == "settings" else "orders"

    return render(
        request, "public/profile.html", page="profile", page_title="Профіль — Coffee Time",
        active_tab=active_tab, saved_flag=saved_flag, profile_error="", password_error="",
        user=user, order_count=order_count, total_spent=total_spent, joined_at=joined_at,
        initials=initials, display_name=display_name,
        grouped=grouped, group_labels=group_labels, has_orders=bool(orders),
    )


@router.post("/profile")
async def profile_submit(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    session = request.state.session
    user_id = user["client_id"]

    try:
        await verify_csrf(request)
    except CSRFError as exc:
        session["flash_error"] = exc.message
        return RedirectResponse("/profile", status_code=303)

    form = await request.form()
    action = form.get("action", "")
    profile_error, password_error = "", ""

    if action == "profile":
        first_name = (form.get("first_name") or "").strip()
        last_name = (form.get("last_name") or "").strip()
        phone = (form.get("phone") or "").strip()
        db_user = db.get(User, user_id)
        if db_user:
            db_user.client_name = first_name
            db_user.client_surname = last_name
            db_user.client_PhoneNumber = phone
            db.commit()
            user["client_name"] = first_name
            user["client_surname"] = last_name
            user["client_PhoneNumber"] = phone
            session["user"] = user
            session["prof_saved"] = "profile"
            return RedirectResponse("/profile?tab=settings", status_code=302)
        profile_error = "Помилка оновлення даних."

    elif action == "password":
        current = form.get("current_password") or ""
        new = form.get("new_password") or ""
        confirm = form.get("confirm_password") or ""
        if not current or not new or not confirm:
            password_error = "Заповніть усі поля."
        elif new != confirm:
            password_error = "Паролі не збігаються."
        elif len(new) < 6:
            password_error = "Мінімум 6 символів."
        else:
            db_user = db.get(User, user_id)
            if db_user and verify_password(current, db_user.password):
                db_user.password = hash_password(new)
                db.commit()
                session["prof_saved"] = "password"
                return RedirectResponse("/profile?tab=settings", status_code=302)
            password_error = "Неправильний поточний пароль."

    order_count, total_spent = get_order_stats(db, user_id)
    orders = get_orders_with_previews(db, user_id)
    grouped = group_by_recency(orders)
    db_user = db.get(User, user_id)
    joined_at = f"{_UK_MONTHS[db_user.created_at.month]} {db_user.created_at.year}" if db_user and db_user.created_at else "—"
    first_name = user.get("client_name") or ""
    last_name = user.get("client_surname") or ""
    initials = ((first_name[:1] + last_name[:1]) or user.get("login", "U")[:1]).upper()
    display_name = f"{first_name} {last_name}".strip() or user.get("login", "")

    return render(
        request, "public/profile.html", page="profile", page_title="Профіль — Coffee Time",
        active_tab="settings", saved_flag=None, profile_error=profile_error, password_error=password_error,
        user=user, order_count=order_count, total_spent=total_spent, joined_at=joined_at,
        initials=initials, display_name=display_name,
        grouped=grouped, group_labels={"today": "Сьогодні", "week": "Цього тижня", "earlier": "Раніше"},
        has_orders=bool(orders),
    )


@router.get("/pages/get_order_items.php")
def get_order_items(request: Request, order_id: int = 0, db: Session = Depends(get_db)):
    user = request.state.session.get("user")
    if not user:
        return {"items": []}
    if not order_id:
        return {"items": []}

    order = db.execute(select(Order).where(Order.order_id == order_id, Order.user_id == user["client_id"])).scalar_one_or_none()
    if not order:
        return {"items": []}

    from app.models.orders import OrderItem
    from app.services.profile import PREVIEW_CATEGORIES

    raw_items = db.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
    items = []
    for it in raw_items:
        name, image = "—", None
        if it.category in PREVIEW_CATEGORIES:
            model = CATEGORY_MODEL_MAP[ProductCategory(it.category)]
            product = db.get(model, it.product_id)
            if product:
                name = product.name or "—"
                image = item_img(product.image or "", prefix="") or None
        items.append({"name": name, "image": image, "category": it.category, "quantity": it.quantity, "price": float(it.price)})

    return {"items": items}


@router.post("/forms/rate_order.php")
async def rate_order(request: Request, db: Session = Depends(get_db)):
    user = request.state.session.get("user")
    if not user:
        return {"ok": False}

    form = await request.form()
    order_id = int(form.get("order_id") or 0)
    rating = int(form.get("rating") or 0)
    if not order_id or rating < 1 or rating > 5:
        return {"ok": False, "msg": "invalid"}

    user_id = user["client_id"]
    order = db.execute(select(Order).where(Order.order_id == order_id, Order.user_id == user_id, Order.status == "done")).scalar_one_or_none()
    if not order:
        return {"ok": False, "msg": "not_found"}

    existing = db.execute(select(OrderRating).where(OrderRating.order_id == order_id, OrderRating.user_id == user_id)).scalar_one_or_none()
    if existing:
        existing.rating = rating
    else:
        db.add(OrderRating(order_id=order_id, user_id=user_id, rating=rating))
    db.commit()
    return {"ok": True}
