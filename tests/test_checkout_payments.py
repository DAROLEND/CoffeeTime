"""Phase 5 verification: checkout order creation (cash vs card_online),
LiqPay signature round-trip, the webhook callback, payment-status polling,
and reminder scheduling."""
from __future__ import annotations

import datetime
import re
from zoneinfo import ZoneInfo

from app.models.catalog import CoffeeItem
from app.models.orders import Order, OrderItem, OrderReminder
from app.services.liqpay import LiqPay, map_liqpay_status, verify_and_decode
from app.services.reminders import schedule_reminders
from app.services.schedule import get_next_available_time, is_cafe_open_at

_KYIV_TZ = ZoneInfo("Europe/Kyiv")


def _csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', html)
    assert m
    return m.group(1)


def _future_ready_time_str() -> str:
    """A same-day ready_time comfortably past checkout's own
    prep_minutes+travel_minutes buffer (up to ~150 min for the heaviest
    cart) — not just get_next_available_time()'s ~15-minute UI-picker
    suggestion, which checkout's stricter server-side validation can
    reject as "already passed" depending on the cart's estimated prep
    time. Falls back to the next available day (a full day of buffer)
    if +2h would land outside today's cafe hours."""
    candidate = (datetime.datetime.now(_KYIV_TZ) + datetime.timedelta(hours=2)).replace(second=0, microsecond=0)
    if is_cafe_open_at(candidate):
        return candidate.strftime("%Y-%m-%d %H:%M")
    slot = get_next_available_time()
    assert slot is not None
    return slot["datetime"].strftime("%Y-%m-%d %H:%M")


def _add_coffee_to_cart(client, db_session, price=60):
    coffee = CoffeeItem(name="Латте", description="", image="", price=price)
    db_session.add(coffee)
    db_session.commit()
    client.post("/forms/add_to_cart.php", data={"category": "coffee_items", "id": coffee.id, "quantity": 2})
    return coffee


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

def test_checkout_cash_order_creates_order_and_clears_cart(client, db_session, monkeypatch):
    import app.routers.public.checkout as checkout_module
    monkeypatch.setattr(checkout_module, "notify_new_order", lambda *a, **k: None)

    _add_coffee_to_cart(client, db_session)
    resp = client.get("/checkout")
    assert resp.status_code == 200
    token = _csrf_token(resp.text)
    ready_time = _future_ready_time_str()

    resp = client.post("/checkout", data={
        "csrf_token": token, "first_name": "Іван", "last_name": "Петренко",
        "phone": "+380991234567", "ready_time": ready_time, "payment": "cash_on_pickup",
        "order_type": "dine_in", "travel_minutes": "15",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/payment-success"

    order = db_session.query(Order).one()
    assert order.customer_name == "Іван"
    assert order.total == 120
    assert order.status.value == "new"
    items = db_session.query(OrderItem).filter_by(order_id=order.order_id).all()
    assert len(items) == 1
    assert items[0].quantity == 2

    coffee = db_session.query(CoffeeItem).one()
    assert coffee.popularity == 2  # incremented by the ordered quantity


def test_checkout_requires_cart(client, db_session):
    resp = client.get("/checkout", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/cart"


def test_checkout_rejects_missing_fields(client, db_session):
    """checkout.php has a real quirk worth preserving: the generic
    "fill all required fields" message is deliberately excluded from the
    visible error banner (client-side JS shows per-field messages
    instead) — `error_message and error_message != "..."` in the
    template. So the observable behavior here is: no order gets created
    and the form re-renders (200, not a redirect)."""
    _add_coffee_to_cart(client, db_session)
    resp = client.get("/checkout")
    token = _csrf_token(resp.text)
    resp = client.post("/checkout", data={"csrf_token": token, "first_name": "", "payment": "cash_on_pickup"})
    assert resp.status_code == 200
    assert db_session.query(Order).count() == 0


def test_checkout_future_day_requires_online_payment(client, db_session):
    _add_coffee_to_cart(client, db_session)
    resp = client.get("/checkout")
    token = _csrf_token(resp.text)

    import datetime
    future = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d") + " 12:00"
    resp = client.post("/checkout", data={
        "csrf_token": token, "first_name": "Іван", "last_name": "Петренко",
        "phone": "+380991234567", "ready_time": future, "payment": "cash_on_pickup", "order_type": "dine_in",
    })
    assert resp.status_code == 200
    assert "лише з передоплатою" in resp.text


# ── Checkout: card_online order ──

def test_checkout_card_online_redirects_to_liqpay(client, db_session, monkeypatch):
    _add_coffee_to_cart(client, db_session)
    resp = client.get("/checkout")
    token = _csrf_token(resp.text)
    ready_time = _future_ready_time_str()

    resp = client.post("/checkout", data={
        "csrf_token": token, "first_name": "Ольга", "last_name": "Іванова",
        "phone": "+380991234567", "ready_time": ready_time, "payment": "card_online", "order_type": "takeaway",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/liqpay-checkout"

    order = db_session.query(Order).one()
    assert order.payment_status.value == "pending"
    assert order.liqpay_order_id == f"coffeetime_{order.order_id}"
    # Cart is NOT cleared yet for online payment — only payment_success clears it.
    preview = client.get("/forms/get_cart_preview.php").json()
    assert preview["count"] == 2


def test_liqpay_checkout_dev_bypass_when_keys_missing(client, db_session):
    """No LIQPAY_PUBLIC_KEY/PRIVATE_KEY configured in tests -> dev bypass
    skips the real gateway and goes straight to payment-success."""
    _add_coffee_to_cart(client, db_session)
    resp = client.get("/checkout")
    token = _csrf_token(resp.text)
    ready_time = _future_ready_time_str()
    client.post("/checkout", data={
        "csrf_token": token, "first_name": "Марія", "last_name": "Коваль",
        "phone": "+380991234567", "ready_time": ready_time, "payment": "card_online", "order_type": "dine_in",
    }, follow_redirects=False)

    resp = client.get("/liqpay-checkout", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/payment-success"


# ── Webhook + status polling ──

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

    resp = client.post("/liqpay-callback", data={"data": data, "signature": sig})
    assert resp.status_code == 200
    assert resp.text == "OK"

    db_session.expire_all()
    updated = db_session.get(Order, order.order_id)
    assert updated.payment_status.value == "paid"
    assert updated.status.value == "new"
    assert updated.paid_at is not None
    assert notified["order_id"] == order.order_id


def test_liqpay_callback_rejects_bad_signature(client, db_session):
    resp = client.post("/liqpay-callback", data={"data": "abc", "signature": "wrong"})
    assert resp.status_code == 403


def test_check_payment_status_requires_matching_session(client, db_session):
    order = Order(total=50, status="new", payment_status="pending")
    db_session.add(order)
    db_session.commit()

    # No pending_order_id in session yet -> unknown (anti-enumeration)
    resp = client.get(f"/check-payment-status?order_id={order.order_id}")
    assert resp.json() == {"status": "unknown"}


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
