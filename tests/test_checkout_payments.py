"""Tests for checkout order creation (cash vs card_online), LiqPay
signature round-trip, the webhook callback, payment-status polling, and
reminder scheduling."""
from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem, OrderReminder
from app.services.liqpay import LiqPay, map_liqpay_status, verify_and_decode
from app.services.reminders import schedule_reminders

_KYIV_TZ = ZoneInfo("Europe/Kyiv")

# A same-day ready_time comfortably clears checkout's own
# prep_minutes+travel_minutes buffer (up to ~150 min for the heaviest
# cart) only when "now" is well inside cafe hours with room to spare —
# real wall-clock time can be anywhere (including within ~2h of closing,
# where no same-day slot can possibly satisfy that buffer, a fundamental
# fact about the business rule being tested, not a test bug). Freezing
# "now" to a fixed, safe weekday mid-morning makes every test in this
# file deterministic regardless of when the suite actually runs.
_FROZEN_NOW = "2026-09-08T10:00:00+03:00"  # a Tuesday, well inside 08:00-20:00


@pytest.fixture(autouse=True)
def _frozen_clock():
    with freeze_time(_FROZEN_NOW):
        yield


def _future_ready_time_str() -> str:
    """A same-day ready_time, safely inside frozen "now" + cafe hours —
    not just get_next_available_time()'s ~15-minute UI-picker suggestion,
    which checkout's stricter server-side validation (prep_minutes +
    travel_minutes, up to ~150 min for the heaviest cart) can reject as
    "already passed"."""
    candidate = (datetime.datetime.now(_KYIV_TZ) + datetime.timedelta(hours=2)).replace(second=0, microsecond=0)
    return candidate.strftime("%Y-%m-%d %H:%M")


def _add_coffee_to_cart(api, db_session, price=60):
    coffee = CoffeeItem(name="Латте", description="", image="", price=price)
    db_session.add(coffee)
    db_session.commit()
    api.post("/api/cart/items", json={"category": "coffee_items", "id": coffee.id, "quantity": 2})
    return coffee


def _order(api, **overrides):
    body = {
        "first_name": "Іван", "last_name": "Петренко", "phone": "+380991234567",
        "ready_time": _future_ready_time_str(), "payment": "cash_on_pickup",
        "order_type": "dine_in", "travel_minutes": 15,
    }
    body.update(overrides)
    return api.post("/api/checkout", json=body)


# ── LiqPay SDK ──

def test_liqpay_signature_round_trip():
    lp = LiqPay("pub_key", "priv_key")
    data = lp.cnb_data({"action": "pay", "amount": 100, "order_id": "coffeetime_5"})
    sig = lp.cnb_signature(data)
    assert lp.verify_signature(data, sig) is True
    assert lp.verify_signature(data, "tampered") is False


def test_liqpay_status_mapping():
    assert map_liqpay_status("success") == ("paid", "new")
    assert map_liqpay_status("sandbox") == ("paid", "new")
    assert map_liqpay_status("failure") == ("failed", "cancelled")
    assert map_liqpay_status("error") == ("failed", "cancelled")
    assert map_liqpay_status("reversed") == ("failed", None)
    assert map_liqpay_status("wait_accept") == ("pending", None)


def test_verify_and_decode_extracts_order_id():
    lp = LiqPay("pub", "priv")
    data = lp.cnb_data({"action": "pay", "amount": 50, "order_id": "coffeetime_42", "status": "success"})
    sig = lp.cnb_signature(data)
    result = verify_and_decode(lp, data, sig)
    assert result == {"order_id": 42, "payment_status": "paid", "order_status": "new"}


def test_verify_and_decode_rejects_bad_signature():
    lp = LiqPay("pub", "priv")
    data = lp.cnb_data({"order_id": "coffeetime_1"})
    assert verify_and_decode(lp, data, "wrong-signature") is None


# ── Checkout: cash order ──

def test_checkout_view_has_cart_schedule_and_prefill(api, db_session):
    _add_coffee_to_cart(api, db_session)
    view = api.get("/api/checkout").json()
    assert view["total"] == 120
    assert view["items"][0]["quantity"] == 2
    assert view["prep_minutes"] == 15  # 2 coffees x 3 min, rounded up to a 15-min slot
    assert set(view["schedule"]) == {"1", "2", "3", "4", "5", "6", "7"}
    assert view["server_now"].startswith("2026-09-08T10:00")
    assert view["prefill"]["order_type"] == "dine_in"


def test_checkout_cash_order_creates_order_and_clears_cart(api, db_session, monkeypatch):
    import app.routers.public.checkout as checkout_module
    monkeypatch.setattr(checkout_module, "notify_new_order", lambda *a, **k: None)

    _add_coffee_to_cart(api, db_session)
    resp = _order(api, first_name="Іван")
    assert resp.status_code == 200, resp.text
    assert resp.json()["next"] == "success"

    order = db_session.query(Order).one()
    assert order.customer_name == "Іван"
    assert order.total == 120
    assert order.status.value == "new"
    items = db_session.query(OrderItem).filter_by(order_id=order.order_id).all()
    assert len(items) == 1
    assert items[0].quantity == 2

    coffee = db_session.query(CoffeeItem).one()
    assert coffee.popularity == 2  # incremented by the ordered quantity
    assert api.get("/api/cart/preview").json()["count"] == 0

    done = api.post("/api/payments/complete").json()
    assert done["order"]["order_id"] == order.order_id
    assert done["order"]["payment_method"] == "cash_on_pickup"
    # Idempotent: a second call (refresh / StrictMode) returns the same order.
    assert api.post("/api/payments/complete").json()["order"]["order_id"] == order.order_id


def test_order_includes_ice_cream_and_sauces(api, db_session, monkeypatch):
    """They used to be shown in the cart but dropped from the order."""
    import app.routers.public.checkout as checkout_module
    from app.models.catalog import IceCreamItem, Sauce
    monkeypatch.setattr(checkout_module, "notify_new_order", lambda *a, **k: None)

    db_session.add_all([IceCreamItem(name="Пломбір", image="", price=40), Sauce(name="Кетчуп", price=15, active=True, image="")])
    db_session.commit()
    api.post("/api/cart/items", json={"category": "ice_cream_items", "id": 1})
    api.post("/api/cart/items", json={"category": "sauces", "id": 1, "quantity": 2})

    assert _order(api).status_code == 200
    order = db_session.query(Order).one()
    assert float(order.total) == 70
    assert sorted(i.category for i in db_session.query(OrderItem).all()) == ["ice_cream_items", "sauces"]


def test_checkout_uses_current_db_price(api, db_session, monkeypatch):
    import app.routers.public.checkout as checkout_module
    monkeypatch.setattr(checkout_module, "notify_new_order", lambda *a, **k: None)
    coffee = _add_coffee_to_cart(api, db_session, price=60)
    coffee.price = 75  # price changed after it was put in the cart
    db_session.commit()
    _order(api)
    assert float(db_session.query(Order).one().total) == 150


def test_checkout_requires_cart(api, db_session):
    resp = api.get("/api/checkout")
    assert resp.status_code == 409
    assert resp.json()["code"] == "cart_empty"


def test_checkout_rejects_missing_fields(api, db_session):
    _add_coffee_to_cart(api, db_session)
    resp = _order(api, first_name="", last_name="")
    assert resp.status_code == 400
    assert resp.json()["code"] == "missing_fields"
    assert db_session.query(Order).count() == 0


def test_checkout_rejects_time_in_the_past(api, db_session):
    _add_coffee_to_cart(api, db_session)
    resp = _order(api, ready_time="2026-09-08 09:00")
    assert resp.status_code == 400
    assert "вже минув" in resp.json()["detail"]


def test_checkout_rejects_more_than_14_days_ahead(api, db_session):
    _add_coffee_to_cart(api, db_session)
    resp = _order(api, ready_time="2026-09-30 12:00", payment="card_online")
    assert resp.status_code == 400
    assert "14 днів" in resp.json()["detail"]


def test_checkout_rejects_closed_hours(api, db_session):
    _add_coffee_to_cart(api, db_session)
    resp = _order(api, ready_time="2026-09-08 21:30")
    assert resp.status_code == 400
    assert "Кафе не працює" in resp.json()["detail"]


def test_checkout_future_day_requires_online_payment(api, db_session):
    _add_coffee_to_cart(api, db_session)
    future = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d") + " 12:00"
    resp = _order(api, ready_time=future, payment="cash_on_pickup")
    assert resp.status_code == 400
    assert "лише з передоплатою" in resp.json()["detail"]


# ── Checkout: card_online order ──

def test_checkout_card_online_goes_to_liqpay(api, db_session):
    _add_coffee_to_cart(api, db_session)
    resp = _order(api, first_name="Ольга", payment="card_online", order_type="takeaway")
    assert resp.json()["next"] == "liqpay"

    order = db_session.query(Order).one()
    assert order.payment_status.value == "pending"
    assert order.liqpay_order_id == f"coffeetime_{order.order_id}"
    # Cart is NOT cleared yet for online payment — only payment completion clears it.
    assert api.get("/api/cart/preview").json()["count"] == 2


def test_liqpay_checkout_dev_bypass_when_keys_missing(api, db_session):
    """No LIQPAY_PUBLIC_KEY/PRIVATE_KEY configured in tests -> dev bypass
    skips the real gateway and the SPA goes straight to success."""
    _add_coffee_to_cart(api, db_session)
    _order(api, payment="card_online")

    data = api.get("/api/liqpay/checkout").json()
    assert data["dev_bypass"] is True

    done = api.post("/api/payments/complete").json()
    assert done["is_dev_bypass"] is True
    assert api.get("/api/cart/preview").json()["count"] == 0


def test_liqpay_checkout_signs_form(api, db_session, monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "LIQPAY_PUBLIC_KEY", "pub")
    monkeypatch.setattr(settings, "LIQPAY_PRIVATE_KEY", "priv")
    # not "development" (that forces the dev bypass), and not "production"
    # (a Secure cookie would not survive the plain-http TestClient)
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    monkeypatch.setattr(settings, "APP_URL", "https://coffee.example")

    _add_coffee_to_cart(api, db_session)
    _order(api, payment="card_online")
    data = api.get("/api/liqpay/checkout").json()
    assert data["dev_bypass"] is False
    assert data["action_url"] == "https://www.liqpay.ua/api/3/checkout"
    lp = LiqPay("pub", "priv")
    assert lp.verify_signature(data["data"], data["signature"])
    params = lp.decode_data_str(data["data"])
    assert params["result_url"] == "https://coffee.example/api/liqpay/result"
    assert params["server_url"] == "https://coffee.example/api/liqpay/callback"


def test_liqpay_checkout_without_pending_order(api):
    assert api.get("/api/liqpay/checkout").status_code == 409


def test_cancel_pending_cancels_unpaid_order(api, db_session):
    _add_coffee_to_cart(api, db_session)
    _order(api, payment="card_online")
    assert api.post("/api/checkout/cancel-pending").json() == {"ok": True}
    order = db_session.query(Order).one()
    db_session.refresh(order)
    assert order.status.value == "cancelled"
    # The form draft survives, so the customer can resubmit.
    assert api.get("/api/checkout").json()["prefill"]["payment"] == "card_online"


# ── Webhook + result URL + status polling ──

def test_liqpay_callback_updates_order_and_notifies(client, db_session, monkeypatch):
    import app.routers.public.payments as payments_module
    notified = {}
    monkeypatch.setattr(payments_module, "notify_order_from_db", lambda db, oid: notified.setdefault("order_id", oid))

    order = Order(total=100, phone="+380991234567", status="new", payment_status="pending", customer_name="Test")
    db_session.add(order)
    db_session.commit()

    lp = LiqPay("", "")  # empty keys match the default test settings
    data = lp.cnb_data({"order_id": f"coffeetime_{order.order_id}", "status": "success", "amount": 100})
    sig = lp.cnb_signature(data)

    resp = client.post("/api/liqpay/callback", data={"data": data, "signature": sig})
    assert resp.status_code == 200
    assert resp.text == "OK"

    db_session.expire_all()
    updated = db_session.get(Order, order.order_id)
    assert updated.payment_status.value == "paid"
    assert updated.status.value == "new"
    assert updated.paid_at is not None
    assert notified["order_id"] == order.order_id


def test_liqpay_callback_rejects_bad_signature(client, db_session):
    resp = client.post("/api/liqpay/callback", data={"data": "abc", "signature": "wrong"})
    assert resp.status_code == 403


def test_liqpay_result_redirects_to_spa_page(client):
    lp = LiqPay("", "")
    failed = lp.cnb_data({"order_id": "coffeetime_5", "status": "failure"})
    resp = client.post("/api/liqpay/result", data={"data": failed, "signature": lp.cnb_signature(failed)}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/payment-failure"

    ok = lp.cnb_data({"order_id": "coffeetime_5", "status": "success"})
    resp = client.post("/api/liqpay/result", data={"data": ok, "signature": lp.cnb_signature(ok)}, follow_redirects=False)
    assert resp.headers["location"] == "/payment-success"


def test_check_payment_status_requires_matching_session(api, db_session):
    order = Order(total=50, status="new", payment_status="pending")
    db_session.add(order)
    db_session.commit()

    # No pending_order_id in session -> unknown (anti-enumeration)
    resp = api.get(f"/api/payments/status?order_id={order.order_id}")
    assert resp.json() == {"status": "unknown"}


def test_check_payment_status_for_own_order(api, db_session):
    _add_coffee_to_cart(api, db_session)
    order_id = _order(api, payment="card_online").json()["order_id"]
    assert api.get(f"/api/payments/status?order_id={order_id}").json() == {"status": "pending"}
    assert api.get("/api/payments/pending").json()["order_id"] == order_id


# ── Reminders ──

def test_schedule_reminders_creates_rows_for_far_future_order(db_session):
    import datetime
    pickup = datetime.datetime.now() + datetime.timedelta(days=3)
    ready_time = pickup.strftime("%Y-%m-%d") + " 14:00"

    order = Order(total=100, status="new")
    db_session.add(order)
    db_session.commit()

    schedule_reminders(db_session, order.order_id, ready_time, "customer@example.com")

    reminders = db_session.query(OrderReminder).filter_by(order_id=order.order_id).all()
    types = sorted(r.type.value for r in reminders)
    # 3+ days out -> telegram+email reminders at 2h-before, 1-day-before 19:00,
    # and 2-days-before 19:00 (6 rows total: 3 telegram + 3 email)
    assert types.count("telegram_admin") == 3
    assert types.count("email_customer") == 3


def test_schedule_reminders_skips_past_ready_time(db_session):
    order = Order(total=100, status="new")
    db_session.add(order)
    db_session.commit()
    schedule_reminders(db_session, order.order_id, "2020-01-01 12:00", "x@example.com")
    assert db_session.query(OrderReminder).filter_by(order_id=order.order_id).count() == 0


def test_schedule_reminders_no_email_reminder_without_customer_email(db_session):
    import datetime
    pickup = datetime.datetime.now() + datetime.timedelta(hours=5)
    if pickup.hour < 9:
        pickup = pickup.replace(hour=12)
    ready_time = pickup.strftime("%Y-%m-%d %H:%M")

    order = Order(total=100, status="new")
    db_session.add(order)
    db_session.commit()
    schedule_reminders(db_session, order.order_id, ready_time, None)

    reminders = db_session.query(OrderReminder).filter_by(order_id=order.order_id).all()
    assert all(r.type.value == "telegram_admin" for r in reminders)
