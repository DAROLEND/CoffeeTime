"""Shared context for every admin page: sidebar badges and notification bell."""
from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models.cms import SiteReview
from app.models.orders import Order
from app.services.permissions import admin_role, has_perm, is_super


def admin_layout_context(request: Request, db: Session) -> dict:
    session = request.state.session
    admin_username = session.get("admin") or "Admin"
    admin_initial = admin_username[:1].upper()

    can_see_orders = has_perm(request, "orders_view") or admin_role(request) == "super"
    new_orders_count = 0
    notif_orders = []
    if can_see_orders:
        new_orders_count = db.execute(
            select(func.count()).select_from(Order).where(Order.status == "new")
        ).scalar_one()
        rows = db.execute(
            select(Order).where(Order.status == "new").order_by(Order.created_at.desc()).limit(5)
        ).scalars().all()
        for o in rows:
            name = f"{o.customer_name or ''} {o.customer_surname or ''}".strip() or "Анонім"
            is_today = o.created_at.date() == datetime.date.today()
            time_label = o.created_at.strftime("%H:%M") if is_today else o.created_at.strftime("%d.%m %H:%M")
            notif_orders.append({"order_id": o.order_id, "name": name, "total": float(o.total), "time_label": time_label})

    pending_reviews = db.execute(
        select(func.count()).select_from(SiteReview).where(SiteReview.created_at > datetime.datetime.utcnow() - datetime.timedelta(days=7))
    ).scalar_one()

    return {
        "admin_username": admin_username,
        "admin_initial": admin_initial,
        "admin_display": session.get("admin_display") or admin_username,
        "can_see_orders": can_see_orders,
        "new_orders_count": new_orders_count,
        "notif_orders": notif_orders,
        "pending_reviews": pending_reviews,
        "is_super": is_super(request),
        "has_perm_orders_view": has_perm(request, "orders_view"),
        "has_perm_products": has_perm(request, "products"),
        "has_perm_content": has_perm(request, "content"),
        "has_perm_reviews": has_perm(request, "reviews"),
        "admin_flash": session.pop("admin_flash", None),
        "admin_flash_type": session.pop("admin_flash_type", None),
    }
