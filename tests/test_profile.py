"""Tests for the profile page: order history/stats, rating
(post-delivery, ownership-checked), and repay flow."""
from __future__ import annotations

import re

from app.models.auth import User
from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem, OrderRating
from app.services.auth import hash_password


def _csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', html)
    assert m
    return m.group(1)


def _login(client, db_session, login="alice", password="pass1234"):
    user = User(login=login, email=f"{login}@example.com", password=hash_password(password))
    db_session.add(user)
    db_session.commit()
    resp = client.get("/login")
    token = _csrf_token(resp.text)
    client.post("/login", data={"csrf_token": token, "email": login, "password": password}, follow_redirects=False)
    return user


def test_profile_requires_login(client, db_session):
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_profile_shows_order_history_and_stats(client, db_session):
    user = _login(client, db_session)
    coffee = CoffeeItem(name="Латте", description="", image="", price=60)
    db_session.add(coffee)
    db_session.flush()
    order = Order(user_id=user.client_id, total=120, status="done", payment_status="paid", payment_method="cash_on_pickup")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=2, price=60))
    db_session.commit()

    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "Латте" in resp.text
    assert "120" in resp.text  # total spent stat


def test_profile_excludes_cancelled_orders_from_stats(client, db_session):
    user = _login(client, db_session)
    db_session.add(Order(user_id=user.client_id, total=500, status="cancelled"))
    db_session.commit()

    resp = client.get("/profile")
    assert "Замовлень ще немає" in resp.text  # cancelled orders don't count


def test_update_profile_fields(client, db_session):
    user = _login(client, db_session)
    resp = client.get("/profile?tab=settings")
    token = _csrf_token(resp.text)

    resp = client.post("/profile", data={
        "csrf_token": token, "action": "profile",
        "first_name": "Олена", "last_name": "Шевченко", "phone": "+380991112233",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/profile?tab=settings"

    db_session.expire_all()
    db_user = db_session.get(User, user.client_id)
    assert db_user.client_name == "Олена"
    assert db_user.client_PhoneNumber == "+380991112233"


def test_change_password_via_profile(client, db_session):
    user = _login(client, db_session, password="oldpassword1")
    resp = client.get("/profile?tab=settings")
    token = _csrf_token(resp.text)

    resp = client.post("/profile", data={
        "csrf_token": token, "action": "password",
        "current_password": "oldpassword1", "new_password": "newpassword2", "confirm_password": "newpassword2",
    }, follow_redirects=False)
    assert resp.status_code == 302

    from app.services.auth import verify_password
    db_session.expire_all()
    db_user = db_session.get(User, user.client_id)
    assert verify_password("newpassword2", db_user.password)


def test_rate_order_requires_done_status(client, db_session):
    user = _login(client, db_session)
    order = Order(user_id=user.client_id, total=100, status="new")
    db_session.add(order)
    db_session.commit()

    resp = client.post("/forms/rate_order.php", data={"order_id": order.order_id, "rating": 5})
    assert resp.json() == {"ok": False, "msg": "not_found"}


def test_rate_order_success_and_idempotent_update(client, db_session):
    user = _login(client, db_session)
    order = Order(user_id=user.client_id, total=100, status="done")
    db_session.add(order)
    db_session.commit()

    resp = client.post("/forms/rate_order.php", data={"order_id": order.order_id, "rating": 4})
    assert resp.json() == {"ok": True}

    resp = client.post("/forms/rate_order.php", data={"order_id": order.order_id, "rating": 5})
    assert resp.json() == {"ok": True}

    ratings = db_session.query(OrderRating).filter_by(order_id=order.order_id, user_id=user.client_id).all()
    assert len(ratings) == 1  # updated in place, not duplicated
    assert ratings[0].rating == 5


def test_rate_order_cannot_rate_another_users_order(client, db_session):
    owner = User(login="owner", email="owner@example.com", password=hash_password("x"))
    db_session.add(owner)
    db_session.flush()
    order = Order(user_id=owner.client_id, total=100, status="done")
    db_session.add(order)
    db_session.commit()

    _login(client, db_session, login="intruder")
    resp = client.post("/forms/rate_order.php", data={"order_id": order.order_id, "rating": 1})
    assert resp.json() == {"ok": False, "msg": "not_found"}


def test_get_order_items_ownership_check(client, db_session):
    owner = User(login="owner2", email="owner2@example.com", password=hash_password("x"))
    db_session.add(owner)
    db_session.flush()
    order = Order(user_id=owner.client_id, total=50, status="done")
    db_session.add(order)
    db_session.commit()

    _login(client, db_session, login="stranger")
    resp = client.get(f"/pages/get_order_items.php?order_id={order.order_id}")
    assert resp.json() == {"items": []}


def test_get_order_items_returns_items_for_owner(client, db_session):
    user = _login(client, db_session)
    coffee = CoffeeItem(name="Капучино", description="", image="", price=65)
    db_session.add(coffee)
    db_session.flush()
    order = Order(user_id=user.client_id, total=65, status="done")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.order_id, product_id=coffee.id, category="coffee_items", quantity=1, price=65))
    db_session.commit()

    resp = client.get(f"/pages/get_order_items.php?order_id={order.order_id}")
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Капучино"


def test_repay_redirects_to_liqpay_for_pending_order(client, db_session):
    user = _login(client, db_session)
    order = Order(user_id=user.client_id, total=200, status="new", payment_status="pending")
    db_session.add(order)
    db_session.commit()

    resp = client.get(f"/profile?repay={order.order_id}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/liqpay-checkout?back=profile"


def test_repay_ignores_already_paid_order(client, db_session):
    user = _login(client, db_session)
    order = Order(user_id=user.client_id, total=200, status="done", payment_status="paid")
    db_session.add(order)
    db_session.commit()

    resp = client.get(f"/profile?repay={order.order_id}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/profile?tab=orders"
