"""Tests for the profile page: order history/stats, rating
(post-delivery, ownership-checked), and repay flow."""
from __future__ import annotations

from app.models.auth import User
from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem, OrderRating
from app.services.auth import hash_password
from tests.helpers import login_user


def _login(api, db_session, login="alice", password="pass1234"):
    return login_user(api, db_session, login=login, password=password)


def test_profile_requires_login(api, db_session):
    resp = api.get("/api/profile")
    assert resp.status_code == 401


def test_profile_shows_order_history_and_stats(api, db_session):
    user = _login(api, db_session)
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.flush()
    order = Order(user_id=user.client_id, total=120, status="done", payment_status="paid", payment_method="cash_on_pickup")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=2, price=60))
    db_session.commit()

    data = api.get("/api/profile").json()
    assert data["order_count"] == 1
    assert data["total_spent"] == 120
    order_out = data["groups"][0]["orders"][0]
    assert order_out["preview_names"] == ["Латте"]
    assert order_out["is_done"] is True
    assert order_out["pay_badge"] == {"cls": "ppay-paid", "label": "Оплачено"}


def test_profile_excludes_cancelled_orders_from_stats(api, db_session):
    user = _login(api, db_session)
    db_session.add(Order(user_id=user.client_id, total=500, status="cancelled"))
    db_session.commit()

    data = api.get("/api/profile").json()
    assert data["has_orders"] is False  # cancelled orders don't count
    assert data["order_count"] == 0


def test_update_profile_fields(api, db_session):
    user = _login(api, db_session)
    resp = api.patch("/api/profile", json={"first_name": "Олена", "last_name": "Шевченко", "phone": "+380991112233"})
    assert resp.json() == {"ok": True}
    me = api.get("/api/session").json()["user"]
    assert me["display_name"] == "Олена Шевченко" and me["initials"] == "ОШ"

    db_session.expire_all()
    db_user = db_session.get(User, user.client_id)
    assert db_user.client_name == "Олена"
    assert db_user.client_PhoneNumber == "+380991112233"


def test_change_password_via_profile(api, db_session):
    user = _login(api, db_session, password="oldpassword1")
    resp = api.post("/api/profile/password", json={
        "current_password": "oldpassword1", "new_password": "newpassword2", "confirm_password": "newpassword2",
    })
    assert resp.status_code == 200
    bad = api.post("/api/profile/password", json={
        "current_password": "wrong", "new_password": "newpassword3", "confirm_password": "newpassword3",
    })
    assert bad.status_code == 400

    from app.services.auth import verify_password
    db_session.expire_all()
    db_user = db_session.get(User, user.client_id)
    assert verify_password("newpassword2", db_user.password)


def test_rate_order_requires_done_status(api, db_session):
    user = _login(api, db_session)
    order = Order(user_id=user.client_id, total=100, status="new")
    db_session.add(order)
    db_session.commit()

    resp = api.post(f"/api/profile/orders/{order.order_id}/rating", json={"rating": 5})
    assert resp.status_code == 404


def test_rate_order_success_and_idempotent_update(api, db_session):
    user = _login(api, db_session)
    order = Order(user_id=user.client_id, total=100, status="done")
    db_session.add(order)
    db_session.commit()

    resp = api.post(f"/api/profile/orders/{order.order_id}/rating", json={"rating": 4})
    assert resp.json() == {"ok": True}

    resp = api.post(f"/api/profile/orders/{order.order_id}/rating", json={"rating": 5})
    assert resp.json() == {"ok": True}
    assert api.post(f"/api/profile/orders/{order.order_id}/rating", json={"rating": 9}).status_code == 400

    ratings = db_session.query(OrderRating).filter_by(order_id=order.order_id, user_id=user.client_id).all()
    assert len(ratings) == 1  # updated in place, not duplicated
    assert ratings[0].rating == 5


def test_rate_order_cannot_rate_another_users_order(api, db_session):
    owner = User(login="owner", email="owner@example.com", password=hash_password("x"))
    db_session.add(owner)
    db_session.flush()
    order = Order(user_id=owner.client_id, total=100, status="done")
    db_session.add(order)
    db_session.commit()

    _login(api, db_session, login="intruder")
    resp = api.post(f"/api/profile/orders/{order.order_id}/rating", json={"rating": 1})
    assert resp.status_code == 404


def test_get_order_items_ownership_check(api, db_session):
    owner = User(login="owner2", email="owner2@example.com", password=hash_password("x"))
    db_session.add(owner)
    db_session.flush()
    order = Order(user_id=owner.client_id, total=50, status="done")
    db_session.add(order)
    db_session.commit()

    _login(api, db_session, login="stranger")
    resp = api.get(f"/api/profile/orders/{order.order_id}/items")
    assert resp.status_code == 404


def test_get_order_items_returns_items_for_owner(api, db_session):
    user = _login(api, db_session)
    coffee = CoffeeItem(name="Капучино", description="", image="", price=65)
    db_session.add(coffee)
    db_session.flush()
    order = Order(user_id=user.client_id, total=65, status="done")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=1, price=65))
    db_session.commit()

    resp = api.get(f"/api/profile/orders/{order.order_id}/items")
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Капучино"


def test_repay_redirects_to_liqpay_for_pending_order(api, db_session):
    user = _login(api, db_session)
    order = Order(user_id=user.client_id, total=200, status="new", payment_status="pending")
    db_session.add(order)
    db_session.commit()

    resp = api.post(f"/api/profile/orders/{order.order_id}/repay")
    assert resp.json() == {"redirect": "/liqpay-checkout?back=profile"}
    assert api.get("/api/liqpay/checkout?back=profile").json()["order_id"] == order.order_id


def test_repay_ignores_already_paid_order(api, db_session):
    user = _login(api, db_session)
    order = Order(user_id=user.client_id, total=200, status="done", payment_status="paid")
    db_session.add(order)
    db_session.commit()

    resp = api.post(f"/api/profile/orders/{order.order_id}/repay")
    assert resp.status_code == 400
    assert resp.json()["code"] == "not_payable"
