"""Admin shell data (sidebar badges, notifications, permissions) and the
dashboard with its chart / top-products / order-count endpoints."""
from __future__ import annotations

import datetime
import re

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.auth import AdminUser
from app.models.orders import Order
from app.schemas.admin import (
    AdminLayout, ChartData, CountResponse, DashboardResponse, OrderCounts, TopProductsResponse,
)
from app.services.admin_common import admin_layout_context
from app.services.dashboard import (
    dashboard_payload, get_chart_data_for_date, get_top_products_for_period, top_product_out,
)
from app.services.orders_admin import order_counts as count_orders
from app.services.permissions import require_perm

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.get("/layout", response_model=AdminLayout)
def layout(request: Request, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return admin_layout_context(request, db, admin)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(request: Request, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return dashboard_payload(request, db)


orders_view = [Depends(require_perm("orders_view"))]


@router.get("/dashboard/new-orders-count", response_model=CountResponse, dependencies=orders_view)
def check_new_orders(db: Session = Depends(get_db)):
    """Polled every 30s by the admin shell to announce new orders."""
    return {"count": db.execute(select(func.count()).select_from(Order).where(Order.status == "new")).scalar_one()}


@router.get("/dashboard/chart-data", response_model=ChartData, dependencies=orders_view)
def chart_data(date: str, db: Session = Depends(get_db)):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return {"success": False}
    return {"success": True, "data": get_chart_data_for_date(db, datetime.date.fromisoformat(date))}


@router.get("/dashboard/top-products", response_model=TopProductsResponse, dependencies=orders_view)
def top_products(period: str = "all", date_from: str | None = None, date_to: str | None = None, db: Session = Depends(get_db)):
    return {"success": True, "products": [top_product_out(p) for p in get_top_products_for_period(db, period, date_from, date_to)]}


@router.get("/dashboard/order-counts", response_model=OrderCounts, dependencies=orders_view)
def order_counts(db: Session = Depends(get_db)):
    return count_orders(db)
