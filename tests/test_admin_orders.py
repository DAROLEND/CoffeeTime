"""Admin orders: list/filter/pagination, detail, status transitions
(single + bulk), and delete."""
from __future__ import annotations

from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem
from tests.helpers import login_admin


def _ids(data) -> set[int]:
    return {o["order_id"] for o in data["orders"]}


def test_orders_list_requires_orders_view_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["products"]')
    resp = api.get("/api/admin/orders")
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


def test_orders_list_shows_orders_and_respects_filters(api, db_session):
    login_admin(api, db_session)
    o_new = Order(total=100, status="new", customer_name="Іван", customer_surname="Петренко", phone="0991112233")
    o_done = Order(total=200, status="done", customer_name="Марія", customer_surname="Коваль", phone="0997778899")
    db_session.add_all([o_new, o_done])
    db_session.commit()

    data = api.get("/api/admin/orders").json()
    assert _ids(data) == {o_new.order_id, o_done.order_id}
    assert data["counts"]["new"] == 1 and data["counts"]["done"] == 1
    assert data["status_labels"]["processing"] == "В обробці"

    assert _ids(api.get("/api/admin/orders?status=done").json()) == {o_done.order_id}
    assert _ids(api.get("/api/admin/orders?search=Петренко").json()) == {o_new.order_id}
    assert _ids(api.get("/api/admin/orders?search=7778899").json()) == {o_done.order_id}  # by phone


def test_orders_type_filter_uses_order_type(api, db_session):
    login_admin(api, db_session)
    hall = Order(total=10, status="new", order_type="dine_in")
    takeaway = Order(total=20, status="new", order_type="takeaway")
    db_session.add_all([hall, takeaway])
    db_session.commit()
    assert _ids(api.get("/api/admin/orders?type=takeout").json()) == {takeaway.order_id}
    assert _ids(api.get("/api/admin/orders?type=hall").json()) == {hall.order_id}


def test_orders_pagination(api, db_session):
    login_admin(api, db_session)
    db_session.add_all([Order(total=i, status="new") for i in range(25)])
    db_session.commit()
    page2 = api.get("/api/admin/orders?page=2").json()
    assert page2["total"] == 25 and page2["total_pages"] == 2 and len(page2["orders"]) == 5


def test_view_order_shows_items(api, db_session):
    login_admin(api, db_session)
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.flush()
    order = Order(total=120, status="new", customer_name="Тест", payment_method="cash_on_pickup")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=2, price=60))
    db_session.commit()

    data = api.get(f"/api/admin/orders/{order.order_id}").json()
    assert data["line_items"][0]["product_name"] == "Латте"
    assert data["payment_method_label"] == "При отриманні"
    assert data["next_allowed"] == ["processing", "done", "cancelled"]


def test_view_order_allows_orders_view_staff(api, db_session):
    login_admin(api, db_session, username="staffer", role="staff", perms='["orders_view"]')
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()
    assert api.get(f"/api/admin/orders/{order.order_id}").status_code == 200


def test_view_missing_order_is_404(api, db_session):
    login_admin(api, db_session)
    assert api.get("/api/admin/orders/999").status_code == 404


def test_status_transition_allowed(api, db_session):
    login_admin(api, db_session)
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()

    data = api.post(f"/api/admin/orders/{order.order_id}/status", json={"status": "processing"}).json()
    assert data["success"] is True
    assert data["label"] == "В обробці"
    assert data["new_count"] == 0
    db_session.expire_all()
    assert db_session.get(Order, order.order_id).status.value == "processing"


def test_status_transition_rejects_invalid_jump(api, db_session):
    login_admin(api, db_session)
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()
    data = api.post(f"/api/admin/orders/{order.order_id}/status", json={"status": "ready"}).json()
    assert data["success"] is False
    assert "заборонений" in data["error"]


def test_status_transition_requires_orders_edit_permission(api, db_session):
    login_admin(api, db_session, role="staff", perms='["orders_view"]')
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.commit()
    resp = api.post(f"/api/admin/orders/{order.order_id}/status", json={"status": "processing"})
    assert resp.status_code == 403


def test_bulk_status_updates_valid_and_skips_invalid(api, db_session):
    login_admin(api, db_session)
    o1 = Order(total=10, status="new")
    o2 = Order(total=20, status="ready")  # ready -> processing is not allowed
    db_session.add_all([o1, o2])
    db_session.commit()
    data = api.post("/api/admin/orders/bulk-status", json={"order_ids": [o1.order_id, o2.order_id], "status": "processing"}).json()
    assert data["updated"] == 1
    assert data["skipped"] == 1


def test_delete_order_removes_order_and_items(api, db_session):
    login_admin(api, db_session)
    order = Order(total=10, status="new")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=1, category="coffee_items", quantity=1, price=10))
    db_session.commit()
    order_id = order.order_id

    assert api.delete(f"/api/admin/orders/{order_id}").json() == {"success": True, "error": None}
    assert db_session.get(Order, order_id) is None
    assert db_session.query(OrderItem).filter_by(order_id=order_id).count() == 0
