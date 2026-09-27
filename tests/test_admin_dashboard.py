"""Admin shell + dashboard: staff-home vs full dashboard split, and the
endpoints the dashboard polls."""
from __future__ import annotations

from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem
from tests.helpers import login_admin


def test_dashboard_requires_admin_login(api):
    resp = api.get("/api/admin/dashboard")
    assert resp.status_code == 401
    assert resp.json()["code"] == "auth_required"


def test_customer_session_is_not_an_admin(api, db_session):
    from tests.helpers import login_user
    login_user(api, db_session)
    assert api.get("/api/admin/layout").status_code == 401


def test_layout_reports_permissions(api, db_session):
    login_admin(api, db_session, username="staffer", role="staff", perms='["products", "reviews"]')
    layout = api.get("/api/admin/layout").json()
    assert layout["perms"] == {"orders_view": False, "orders_edit": False, "products": True, "content": False, "reviews": True}
    assert layout["is_super"] is False and layout["can_see_orders"] is False


def test_super_admin_sees_full_dashboard(api, db_session):
    login_admin(api, db_session, role="super")
    data = api.get("/api/admin/dashboard").json()
    assert data["mode"] == "full"
    assert len(data["full"]["hours_data"]) == 24
    assert len(data["full"]["week_labels"]) == 7 and len(data["full"]["month_data"]) == 30


def test_staff_without_orders_view_sees_staff_home(api, db_session):
    login_admin(api, db_session, username="staffer", role="staff", perms='["products"]')
    data = api.get("/api/admin/dashboard").json()
    assert data["mode"] == "staff"
    assert data["full"] is None
    assert data["role_label"] == "Товари"
    assert data["staff_stats"]["products_total"] == 0
    assert data["staff_stats"]["reviews_total"] is None  # no reviews permission -> no reviews block


def test_staff_with_orders_view_sees_full_dashboard(api, db_session):
    login_admin(api, db_session, username="staffer2", role="staff", perms='["orders_view"]')
    assert api.get("/api/admin/dashboard").json()["mode"] == "full"


def test_dashboard_shows_recent_order(api, db_session):
    login_admin(api, db_session)
    db_session.add(Order(total=150, status="new", payment_status="pending", customer_name="Тест", customer_surname="Клієнт", phone="+380991234567"))
    db_session.commit()
    recent = api.get("/api/admin/dashboard").json()["full"]["recent_orders"]
    assert recent[0]["full_name"] == "Тест Клієнт"
    assert recent[0]["order_id"] == 1
    assert recent[0]["status_label"] == "Нове"
    assert recent[0]["pay_badge"]["label"] == "Не оплачено"


def test_check_new_orders_endpoint(api, db_session):
    login_admin(api, db_session)
    db_session.add(Order(total=100, status="new"))
    db_session.add(Order(total=50, status="done"))
    db_session.commit()
    assert api.get("/api/admin/dashboard/new-orders-count").json() == {"count": 1}
    assert api.get("/api/admin/layout").json()["new_orders_count"] == 1


def test_order_stats_endpoints_need_orders_view(api, db_session):
    login_admin(api, db_session, username="staffer", role="staff", perms='["products"]')
    assert api.get("/api/admin/dashboard/new-orders-count").status_code == 403
    assert api.get("/api/admin/dashboard/order-counts").status_code == 403


def test_get_chart_data_validates_date_format(api, db_session):
    login_admin(api, db_session)
    assert api.get("/api/admin/dashboard/chart-data?date=not-a-date").json() == {"success": False, "data": []}
    data = api.get("/api/admin/dashboard/chart-data?date=2026-01-01").json()
    assert data["success"] is True
    assert len(data["data"]) == 24


def test_get_top_products_ranks_by_quantity(api, db_session):
    login_admin(api, db_session)
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.flush()
    order = Order(total=180, status="done")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=3, price=60))
    db_session.commit()

    data = api.get("/api/admin/dashboard/top-products?period=all").json()
    assert data["success"] is True
    assert data["products"][0]["name"] == "Латте"
    assert data["products"][0]["sold"] == 3


def test_get_order_counts_breakdown(api, db_session):
    login_admin(api, db_session)
    db_session.add(Order(total=10, status="new", payment_status="pending", payment_method="card_online"))
    db_session.add(Order(total=20, status="done", payment_status="paid", payment_method="card_online"))
    db_session.add(Order(total=30, status="new", payment_status="cash", payment_method="cash_on_pickup"))
    db_session.commit()
    data = api.get("/api/admin/dashboard/order-counts").json()
    assert data["all"] == 3
    assert data["new"] == 2
    assert data["done"] == 1
    assert data["paid"] == 1
    assert data["cash"] == 1
    assert data["unpaid"] == 1
