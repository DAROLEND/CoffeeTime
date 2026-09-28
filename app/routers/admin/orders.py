"""Admin order management: list/filter, detail view, status transitions
(single and bulk), and deletion."""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.auth import User
from app.models.orders import Order, OrderItem
from app.schemas.admin import (
    AdminOrderDetail, AdminOrdersPage, BulkStatusRequest, BulkStatusResult,
    StatusChangeRequest, StatusChangeResult,
)
from app.schemas.common import SuccessResponse
from app.services.dashboard import payment_badge
from app.services.enum_utils import enum_value
from app.services.orders_admin import (
    NEXT_LABELS, PAYMENT_METHOD_LABELS, STATUS_LABELS, TRANSITIONS, build_orders_where,
    count_new_orders, get_order_rating, order_counts, resolve_order_items_for_display, transition_status,
)
from app.services.permissions import require_perm

router = APIRouter(prefix="/admin/orders", tags=["admin"], dependencies=[Depends(get_current_admin)])

PER_PAGE = 20


def _line_item_out(it: dict) -> dict:
    return {
        "product_name": it["product_name"], "product_image": it["product_image_url"], "category": it["category"],
        "quantity": it["quantity"], "price": it["price"], "opts": it["opts"],
    }


def _row_out(db: Session, o: Order, items_count: int) -> dict:
    status = enum_value(o.status) or "new"
    payment_status = enum_value(o.payment_status)
    return {
        "order_id": o.order_id, "items_count": items_count,
        "full_name": f"{o.customer_name or ''} {o.customer_surname or ''}".strip() or "—",
        "phone": o.phone or "—", "total": float(o.total), "status": status,
        "payment_status": payment_status, "payment_method": o.payment_method or "",
        "order_type": enum_value(o.order_type) or "dine_in", "ready_time": o.ready_time or "",
        "comment": o.comment or "", "created_at": o.created_at.isoformat(timespec="seconds"),
        "pay_badge": dict(zip(("cls", "icon", "label"), payment_badge({"payment_status": payment_status, "payment_method": o.payment_method}))),
        "next_allowed": TRANSITIONS.get(status, []),
        "line_items": [_line_item_out(it) for it in resolve_order_items_for_display(db, o.order_id)],
    }


@router.get("", response_model=AdminOrdersPage, dependencies=[Depends(require_perm("orders_view"))])
def orders_list(
    db: Session = Depends(get_db),
    status: str = "", payment: str = "", method: str = "", type: str = "", search: str = "",
    date_from: str = "", date_to: str = "", time_from: str = "", time_to: str = "",
    page: int = 1,
):
    filters = {
        "status": status, "payment": payment, "method": method, "type": type, "search": search,
        "date_from": date_from, "date_to": date_to, "time_from": time_from, "time_to": time_to,
    }
    clauses = build_orders_where(filters)
    total_rows = db.execute(select(func.count()).select_from(Order).where(*clauses)).scalar_one()
    total_pages = max(1, math.ceil(total_rows / PER_PAGE))
    page = min(max(1, page), total_pages)

    rows = db.execute(
        select(Order, func.count(OrderItem.id).label("items_count"))
        .outerjoin(OrderItem, OrderItem.order_id == Order.order_id)
        .where(*clauses).group_by(Order.order_id).order_by(Order.created_at.desc(), Order.order_id.desc())
        .limit(PER_PAGE).offset((page - 1) * PER_PAGE)
    ).all()

    return {
        "orders": [_row_out(db, row.Order, row.items_count) for row in rows],
        "total": total_rows, "page": page, "total_pages": total_pages,
        "counts": order_counts(db), "status_labels": STATUS_LABELS, "next_labels": NEXT_LABELS,
    }


@router.get("/{order_id}", response_model=AdminOrderDetail, dependencies=[Depends(require_perm("orders_view"))])
def view_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise not_found("Замовлення не знайдено.")
    items_count = db.execute(select(func.count()).select_from(OrderItem).where(OrderItem.order_id == order_id)).scalar_one()

    user = db.get(User, order.user_id) if order.user_id else None
    client_name = (
        f"{(user.client_name if user else '') or order.customer_name or ''} {(user.client_surname if user else '') or ''}".strip()
        or order.customer_name or "—"
    )
    rating = get_order_rating(db, order_id)
    return {
        **_row_out(db, order, items_count),
        "customer_email": order.customer_email or "",
        "client_name": client_name,
        "client_email": user.email if user else None,
        "paid_at": order.paid_at.isoformat(timespec="seconds") if order.paid_at else None,
        "payment_method_label": PAYMENT_METHOD_LABELS.get(order.payment_method or "", order.payment_method or "—"),
        "rating": rating.rating if rating else None,
    }


@router.post("/{order_id}/status", response_model=StatusChangeResult, dependencies=[Depends(require_perm("orders_edit"))])
def update_order_status(order_id: int, body: StatusChangeRequest, db: Session = Depends(get_db)):
    result = transition_status(db, order_id, body.status.strip())
    result["new_count"] = count_new_orders(db)
    return result


@router.post("/bulk-status", response_model=BulkStatusResult, dependencies=[Depends(require_perm("orders_edit"))])
def bulk_order_status(body: BulkStatusRequest, db: Session = Depends(get_db)):
    new_status = body.status.strip()
    order_ids = set(body.order_ids)
    if not order_ids or new_status not in STATUS_LABELS:
        return {"success": False, "error": "Невірні дані"}

    updated = sum(1 for order_id in order_ids if transition_status(db, order_id, new_status)["success"])
    return {
        "success": updated > 0, "updated": updated, "skipped": len(order_ids) - updated,
        "new_count": count_new_orders(db), "label": STATUS_LABELS[new_status],
    }


@router.delete("/{order_id}", response_model=SuccessResponse, dependencies=[Depends(require_perm("orders_edit"))])
def delete_order(order_id: int, db: Session = Depends(get_db)):
    # order_items.order_id has ON DELETE CASCADE; the explicit delete keeps
    # SQLite (tests) and any FK-less setup consistent too.
    db.execute(delete(OrderItem).where(OrderItem.order_id == order_id))
    result = db.execute(delete(Order).where(Order.order_id == order_id))
    db.commit()
    return {"success": result.rowcount > 0}
