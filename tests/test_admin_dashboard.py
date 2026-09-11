"""Tests for the admin dashboard: staff-home vs full dashboard split, and
the AJAX endpoints it depends on."""
from __future__ import annotations

import re

from app.models.auth import AdminUser
from app.models.catalog import CoffeeItem
from app.models.orders import Order
from app.services.auth import hash_password


def _csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', html)
    assert m
    return m.group(1)


def _login_admin(client, db_session, username="admin1", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = _csrf_token(resp.text)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_dashboard_requires_admin_login(client, db_session):
    resp = client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_super_admin_sees_full_dashboard(client, db_session):
    _login_admin(client, db_session, role="super")
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    assert "Графік замовлень" in resp.text
    assert "Останні замовлення" in resp.text


def test_staff_without_orders_view_sees_staff_home(client, db_session):
    _login_admin(client, db_session, username="staffer", role="staff", perms='["products"]')
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    assert "Вітаємо" in resp.text
    assert "Швидкий перехід" in resp.text
    assert "Графік замовлень" not in resp.text


def test_staff_with_orders_view_sees_full_dashboard(client, db_session):
    _login_admin(client, db_session, username="staffer2", role="staff", perms='["orders_view"]')
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    assert "Графік замовлень" in resp.text


def test_dashboard_shows_recent_order(client, db_session):
    _login_admin(client, db_session)
    db_session.add(Order(total=150, status="new", payment_status="pending", customer_name="Тест", customer_surname="Клієнт", phone="+380991234567"))
    db_session.commit()

    resp = client.get("/admin/dashboard")
    assert "Тест Клієнт" in resp.text
    assert "#1" in resp.text


def test_check_new_orders_endpoint(client, db_session):
    _login_admin(client, db_session)
    db_session.add(Order(total=100, status="new"))
    db_session.add(Order(total=50, status="done"))
    db_session.commit()

    resp = client.get("/admin/check-new-orders")
    assert resp.json() == {"count": 1}


def test_get_chart_data_validates_date_format(client, db_session):
    _login_admin(client, db_session)
    resp = client.get("/admin/get-chart-data?date=not-a-date")
    assert resp.json() == {"success": False}

    resp = client.get("/admin/get-chart-data?date=2026-01-01")
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) == 24


def test_get_top_products_ranks_by_quantity(client, db_session):
    _login_admin(client, db_session)
    from app.models.orders import OrderItem

    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.flush()
    order = Order(total=180, status="done")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=3, price=60))
    db_session.commit()

    resp = client.get("/admin/get-top-products?period=all")
    data = resp.json()
    assert data["success"] is True
    assert data["products"][0]["name"] == "Латте"
    assert data["products"][0]["total_qty"] == 3


def test_get_order_counts_breakdown(client, db_session):
    _login_admin(client, db_session)
    db_session.add(Order(total=10, status="new", payment_status="pending", payment_method="card_online"))
    db_session.add(Order(total=20, status="done", payment_status="paid", payment_method="card_online"))
    db_session.add(Order(total=30, status="new", payment_status="cash", payment_method="cash_on_pickup"))
    db_session.commit()

    resp = client.get("/admin/get-order-counts")
    data = resp.json()
    assert data["all"] == 3
    assert data["new"] == 2
    assert data["done"] == 1
    assert data["paid"] == 1
    assert data["cash"] == 1
    assert data["unpaid"] == 1
