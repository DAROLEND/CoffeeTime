"""Tests for admin orders: list/filter/pagination, view_order,
order-details fragment, status transitions (single + bulk), and delete."""
from __future__ import annotations

import re

from app.models.auth import AdminUser
from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def test_orders_list_requires_orders_view_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["products"]')
    resp = client.get("/admin/orders", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_orders_list_shows_orders_and_respects_filters(client, db_session):
    _login_admin(client, db_session)
    o_new = Order(total=100, status="new", customer_name="Іван", customer_surname="Петренко", phone="0991112233")
    o_done = Order(total=200, status="done", customer_name="Марія", customer_surname="Коваль", phone="0997778899")
    db_session.add_all([o_new, o_done])
    db_session.commit()

    def row_present(html: str, order_id: int) -> bool:
        # Check the orders TABLE specifically (not the topbar's "new
        # orders" notification bell, which independently lists any
        # status='new' order regardless of the list's own filters).
        return f'data-order-id="{order_id}"' in html

    resp = client.get("/admin/orders")
    assert resp.status_code == 200
    assert row_present(resp.text, o_new.order_id)
    assert row_present(resp.text, o_done.order_id)

    resp = client.get("/admin/orders?status=done")
    assert row_present(resp.text, o_done.order_id)
    assert not row_present(resp.text, o_new.order_id)

    resp = client.get("/admin/orders?search=Петренко")
    assert row_present(resp.text, o_new.order_id)
    assert not row_present(resp.text, o_done.order_id)


def test_orders_ajax_returns_json_fragment(client, db_session):
    _login_admin(client, db_session)
    db_session.add(Order(total=50, status="new"))
    db_session.commit()

    resp = client.get("/admin/orders?ajax=1")
    data = resp.json()
    assert "html" in data
    assert data["total"] == 1


def test_view_order_shows_items(client, db_session):
    _login_admin(client, db_session)
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.flush()
    order = Order(total=120, status="new", customer_name="Тест")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=2, price=60))
    db_session.commit()

    resp = client.get(f"/admin/orders/{order.order_id}")
    assert resp.status_code == 200
    assert "Латте" in resp.text


def test_view_order_fixed_permission_key_allows_orders_view_staff(client, db_session):
    """Staff with only 'orders_view' can view individual orders."""
    _login_admin(client, db_session, username="staffer", role="staff", perms='["orders_view"]')
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()

    resp = client.get(f"/admin/orders/{order.order_id}")
    assert resp.status_code == 200


def test_order_details_fragment(client, db_session):
    _login_admin(client, db_session)
    order = Order(total=10, status="new", phone="0991112233")
    db_session.add(order)
    db_session.commit()

    resp = client.get(f"/admin/orders/{order.order_id}/details")
    assert resp.status_code == 200
    assert "od-wrap" in resp.text


def test_status_transition_allowed(client, db_session):
    _login_admin(client, db_session)
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()

    resp = client.post(f"/admin/orders/{order.order_id}/status", json={"status": "processing"})
    data = resp.json()
    assert data["success"] is True
    assert data["label"] == "В обробці"

    db_session.expire_all()
    assert db_session.get(Order, order.order_id).status.value == "processing"


def test_status_transition_rejects_invalid_jump(client, db_session):
    _login_admin(client, db_session)
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()

    resp = client.post(f"/admin/orders/{order.order_id}/status", json={"status": "ready"})
    data = resp.json()
    assert data["success"] is False
    assert "заборонений" in data["error"]


def test_status_transition_requires_orders_edit_permission(client, db_session):
    _login_admin(client, db_session, role="staff", perms='["orders_view"]')
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()
    resp = client.post(f"/admin/orders/{order.order_id}/status", json={"status": "processing"}, follow_redirects=False)
    assert resp.status_code == 303


def test_bulk_status_updates_valid_and_skips_invalid(client, db_session):
    _login_admin(client, db_session)
    o1 = Order(total=10, status="new")
    o2 = Order(total=20, status="ready")  # ready -> processing is not allowed
    db_session.add_all([o1, o2])
    db_session.commit()

    resp = client.post("/admin/orders/bulk-status", json={"order_ids": [o1.order_id, o2.order_id], "status": "processing"})
    data = resp.json()
    assert data["updated"] == 1
    assert data["skipped"] == 1


def test_delete_order_removes_order_and_items(client, db_session):
    _login_admin(client, db_session)
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=1, category="coffee_items", quantity=1, price=10))
    db_session.commit()
    order_id = order.order_id

    resp = client.post(f"/admin/orders/{order_id}/delete")
    assert resp.json() == {"success": True}
    assert db_session.get(Order, order_id) is None
    assert db_session.query(OrderItem).filter_by(order_id=order_id).count() == 0
