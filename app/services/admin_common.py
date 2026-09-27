"""Shared data for the admin shell: sidebar badges, the new-orders bell,
and the admin's effective permissions (for showing/hiding UI only — every
endpoint enforces its own permission server-side)."""
from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models.auth import AdminUser
from app.models.cms import SiteReview
from app.models.orders import Order
from app.services.enum_utils import enum_value
from app.services.permissions import ALL_PERMS, has_perm, is_super


def admin_layout_context(request: Request, db: Session, admin: AdminUser) -> dict:
    can_see_orders = has_perm(request, "orders_view")
    new_orders_count = 0
    notif_orders = []
    if can_see_orders:
        new_orders_count = db.execute(select(func.count()).select_from(Order).where(Order.status == "new")).scalar_one()
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

    display = admin.display_name or admin.username
    return {
        "username": admin.username,
        "initial": (admin.username[:1] or "A").upper(),
        "display_name": display,
        "role": enum_value(admin.role) or "staff",
        "is_super": is_super(request),
        "perms": {key: has_perm(request, key) for key in ALL_PERMS},
        "can_see_orders": can_see_orders,
        "new_orders_count": new_orders_count,
        "notif_orders": notif_orders,
        "pending_reviews": pending_reviews,
    }
