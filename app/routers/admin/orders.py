"""Port of admin/orders.php, view_order.php, get_order_details.php,
update_order_status.php, bulk_order_status.php, delete_order.php."""
from __future__ import annotations

import math

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.orders import Order, OrderItem
from app.services.dashboard import payment_badge
from app.services.orders_admin import (
    NEXT_LABELS, STATUS_LABELS, TRANSITIONS, build_orders_where, count_new_orders,
    get_order_rating, resolve_order_items_for_display, transition_status,
)
from app.services.permissions import require_perm
from app.templating import admin_render, templates

router = APIRouter(prefix="/admin/orders", dependencies=[Depends(get_current_admin)])

PER_PAGE = 20


@router.get("")
def orders_list(
    request: Request, db: Session = Depends(get_db), _perm=Depends(require_perm("orders_view")),
    status: str = "", payment: str = "", method: str = "", type: str = "", search: str = "",
    date_from: str = "", date_to: str = "", time_from: str = "", time_to: str = "",
    p: int = 1, ajax: int | None = None,
):
    filters = {
        "status": status, "payment": payment, "method": method, "type": type, "search": search,
        "date_from": date_from, "date_to": date_to, "time_from": time_from, "time_to": time_to,
    }
    clauses = build_orders_where(filters)

    total_rows = db.execute(select(func.count()).select_from(Order).where(*clauses)).scalar_one()
    total_pages = max(1, math.ceil(total_rows / PER_PAGE))
    page = min(max(1, p), total_pages)
    offset = (page - 1) * PER_PAGE

    rows = db.execute(
        select(Order, func.count(OrderItem.id).label("items_count"))
        .outerjoin(OrderItem, OrderItem.order_id == Order.order_id)
        .where(*clauses).group_by(Order.order_id).order_by(Order.created_at.desc())
        .limit(PER_PAGE).offset(offset)
    ).all()

    orders = []
    for row in rows:
        o = row.Order
        orders.append({
            "order_id": o.order_id, "items_count": row.items_count,
            "full_name": f"{o.customer_name or ''} {o.customer_surname or ''}".strip() or "—",
            "phone": o.phone or "—", "total": float(o.total),
            "status": o.status.value if hasattr(o.status, "value") else o.status,
            "payment_status": o.payment_status.value if hasattr(o.payment_status, "value") else o.payment_status,
            "payment_method": o.payment_method, "created_at": o.created_at,
            # NOT "items" — a plain dict's own .items() method shadows a
            # same-named key when Jinja does attribute-style lookup
            # (getattr succeeds before the dict-subscript fallback runs).
            "line_items": resolve_order_items_for_display(db, o.order_id),
        })

    status_counts = dict(db.execute(select(Order.status, func.count()).group_by(Order.status)).all())
    status_counts = {(k.value if hasattr(k, "value") else k): v for k, v in status_counts.items()}
    all_count = sum(status_counts.values())
    paid_count = db.execute(select(func.count()).select_from(Order).where(Order.payment_status == "paid")).scalar_one()
    cash_count = db.execute(select(func.count()).select_from(Order).where(Order.payment_method.like("%cash%"))).scalar_one()
    unpaid_count = db.execute(
        select(func.count()).select_from(Order).where(Order.payment_status.notin_(["paid", "cash"]), Order.payment_method.notlike("%cash%"))
    ).scalar_one()

    def page_url(n: int) -> str:
        qs = {k: v for k, v in filters.items() if v}
        qs["p"] = n
        return "?" + urlencode(qs)

    context = dict(
        page_title="Замовлення", active_page="orders", orders=orders,
        status_labels=STATUS_LABELS, transitions=TRANSITIONS, next_labels=NEXT_LABELS,
        payment_badge=payment_badge, filters=filters, total_rows=total_rows, total_pages=total_pages, page=page,
        status_counts=status_counts, all_count=all_count, paid_count=paid_count, cash_count=cash_count, unpaid_count=unpaid_count,
        page_url=page_url,
    )

    if ajax:
        html = templates.get_template("admin/_orders_results.html").render({"request": request, **context})
        return {"html": html, "total": total_rows}

    return admin_render(request, db, "admin/orders.html", **context)


@router.get("/{order_id}")
def view_order(order_id: int, request: Request, db: Session = Depends(get_db), _perm=Depends(require_perm("orders_view"))):
    row = db.execute(
        select(Order).where(Order.order_id == order_id)
    ).scalar_one_or_none()
    if not row:
        return RedirectResponse("/admin/orders", status_code=302)

    from app.models.auth import User

    user = db.get(User, row.user_id) if row.user_id else None
    client_name = (
        f"{(user.client_name if user else '') or row.customer_name or ''} {(user.client_surname if user else '') or ''}".strip()
        or row.customer_name or "—"
    )

    items = resolve_order_items_for_display(db, order_id)
    rating = get_order_rating(db, order_id)

    return admin_render(
        request, db, "admin/view_order.html", page_title=f"Замовлення #{order_id}", active_page="orders",
        order=row, items=items, rating=rating, client_name=client_name,
        client_email=user.email if user else None, payment_badge=payment_badge,
    )


@router.get("/{order_id}/details", response_class=HTMLResponse)
def order_details_fragment(order_id: int, request: Request, db: Session = Depends(get_db), _perm=Depends(require_perm("orders_view"))):
    order = db.get(Order, order_id)
    if not order:
        return HTMLResponse('<p style="color:#c00;padding:12px">Замовлення не знайдено</p>')

    items = resolve_order_items_for_display(db, order_id)
    html = templates.get_template("admin/_order_details.html").render({
        "request": request, "order": order, "items": items,
    })
    return HTMLResponse(html)


@router.post("/{order_id}/status")
async def update_order_status(order_id: int, request: Request, db: Session = Depends(get_db), _perm=Depends(require_perm("orders_edit"))):
    body = await request.json()
    new_status = (body.get("status") or "").strip()
    result = transition_status(db, order_id, new_status)
    result["new_count"] = count_new_orders(db)
    return result


@router.post("/bulk-status")
async def bulk_order_status(request: Request, db: Session = Depends(get_db), _perm=Depends(require_perm("orders_edit"))):
    body = await request.json()
    order_ids = {int(i) for i in (body.get("order_ids") or []) if str(i).lstrip("-").isdigit()}
    new_status = (body.get("status") or "").strip()

    if not order_ids or new_status not in STATUS_LABELS:
        return {"success": False, "error": "Невірні дані"}

    updated, skipped = 0, 0
    for order_id in order_ids:
        result = transition_status(db, order_id, new_status)
        if result["success"]:
            updated += 1
        else:
            skipped += 1

    return {
        "success": updated > 0, "updated": updated, "skipped": skipped,
        "new_count": count_new_orders(db), "label": STATUS_LABELS.get(new_status, new_status),
    }


@router.post("/{order_id}/delete")
def delete_order(order_id: int, db: Session = Depends(get_db), _perm=Depends(require_perm("orders_edit"))):
    # order_items.order_id has ON DELETE CASCADE, so the explicit item
    # delete below is redundant but kept to mirror the PHP exactly.
    db.execute(delete(OrderItem).where(OrderItem.order_id == order_id))
    result = db.execute(delete(Order).where(Order.order_id == order_id))
    db.commit()
    return {"success": result.rowcount > 0}
