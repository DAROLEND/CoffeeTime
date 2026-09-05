"""Port of admin/dashboard.php + get_chart_data.php + get_top_products.php
+ get_order_counts.php + check_new_orders.php."""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.orders import Order
from app.services.dashboard import (
    get_chart_data_for_date, get_full_dashboard_stats, get_staff_home_stats,
    get_top_products_for_period, payment_badge, stat_compare, status_info,
)
from app.services.permissions import has_perm, is_super
from app.templating import admin_render

router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    is_staff_home = not is_super(request) and not has_perm(request, "orders_view")

    if is_staff_home:
        staff_stats, cat_counts = get_staff_home_stats(db, request)
        weekday = ["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][int(datetime.date.today().strftime("%w"))]
        role_labels = []
        if has_perm(request, "products"):
            role_labels.append("Товари")
        if has_perm(request, "reviews"):
            role_labels.append("Відгуки")
        if has_perm(request, "content"):
            role_labels.append("Контент")
        return admin_render(
            request, db, "admin/dashboard_staff.html", page_title="Головна", active_page="dashboard",
            staff_stats=staff_stats, cat_counts=cat_counts, weekday=weekday,
            today_str=datetime.date.today().strftime("%d.%m.%Y"),
            role_label=" · ".join(role_labels) or "Адмін",
        )

    stats = get_full_dashboard_stats(db)
    _, cat_counts = get_staff_home_stats(db, request)  # products/content cards also shown on full dashboard
    staff_stats, _ = get_staff_home_stats(db, request)

    return admin_render(
        request, db, "admin/dashboard.html", page_title="Головна", active_page="dashboard",
        show_reviews_stat=is_super(request) or has_perm(request, "reviews"),
        stat_compare=stat_compare, status_info=status_info, payment_badge=payment_badge,
        cat_counts=cat_counts, staff_stats=staff_stats, today_iso=datetime.date.today().isoformat(),
        **stats,
    )


@router.get("/check-new-orders")
def check_new_orders(db: Session = Depends(get_db)):
    count = db.execute(select(func.count()).select_from(Order).where(Order.status == "new")).scalar_one()
    return {"count": count}


@router.get("/get-chart-data")
def get_chart_data(date: str, db: Session = Depends(get_db)):
    import re

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return {"success": False}
    return {"success": True, "data": get_chart_data_for_date(db, datetime.date.fromisoformat(date))}


@router.get("/get-top-products")
def get_top_products(period: str = "all", date_from: str | None = None, date_to: str | None = None, db: Session = Depends(get_db)):
    products = get_top_products_for_period(db, period, date_from, date_to)
    for p in products:
        p["total_qty"] = p.pop("sold")
        p["total_revenue_fmt"] = f"{p['total_revenue']:,.0f}".replace(",", " ")
    return {"success": True, "products": products}


@router.get("/get-order-counts")
def get_order_counts(db: Session = Depends(get_db)):
    def count(*where):
        return db.execute(select(func.count()).select_from(Order).where(*where)).scalar_one()

    return {
        "all": count(),
        "new": count(Order.status == "new"),
        "done": count(Order.status == "done"),
        "cancelled": count(Order.status == "cancelled"),
        "paid": count(Order.payment_status == "paid"),
        "cash": count(Order.payment_method.like("%cash%")),
        "unpaid": count(Order.payment_status.notin_(["paid"]), Order.payment_method.notlike("%cash%")),
    }
