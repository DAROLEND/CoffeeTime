"""CSRF: the token lives in the session, the SPA sends it back in the
X-CSRF-Token header, and every mutating /api request is checked (the
LiqPay endpoints LiqPay itself calls are the only exemptions)."""
from app.middleware.session import SessionData
from app.models.catalog import CoffeeItem
from app.services.csrf import CSRF_SESSION_KEY, csrf_token


def test_csrf_token_is_generated_once_and_cached():
    session = SessionData({})
    token1 = csrf_token(session)
    token2 = csrf_token(session)
    assert token1 == token2
    assert session[CSRF_SESSION_KEY] == token1
    assert len(token1) == 64  # secrets.token_hex(32)


def test_csrf_token_endpoint_is_stable_within_a_session(client):
    t1 = client.get("/api/csrf-token").json()["csrf_token"]
    t2 = client.get("/api/csrf-token").json()["csrf_token"]
    assert t1 == t2 and len(t1) == 64


def test_mutating_request_without_session_token_is_expired(client):
    resp = client.post("/api/cart/items", json={"category": "coffee_items", "id": 1})
    assert resp.status_code == 403
    assert resp.json()["code"] == "csrf_expired"


def test_mutating_request_with_wrong_token_is_rejected(client, db_session):
    db_session.add(CoffeeItem(name="Лате", image="", price=60))
    db_session.commit()
    client.get("/api/csrf-token")  # seeds a token in the session
    resp = client.post("/api/cart/items", json={"category": "coffee_items", "id": 1}, headers={"X-CSRF-Token": "0" * 64})
    assert resp.status_code == 403
    assert resp.json()["code"] == "csrf_invalid"
    assert client.get("/api/cart/preview").json()["count"] == 0


def test_token_in_json_body_is_not_accepted(client, db_session):
    """Only the header counts: a form/JSON field could be set by a
    cross-site form post, a custom header can't."""
    token = client.get("/api/csrf-token").json()["csrf_token"]
    resp = client.post("/api/cart/items", json={"category": "coffee_items", "id": 1, "csrf_token": token})
    assert resp.status_code == 403


def test_safe_methods_need_no_token(client):
    assert client.get("/api/cart").status_code == 200


def test_valid_header_passes(api, db_session):
    db_session.add(CoffeeItem(name="Лате", image="", price=60))
    db_session.commit()
    resp = api.post("/api/cart/items", json={"category": "coffee_items", "id": 1})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_liqpay_callback_is_exempt(client):
    """LiqPay posts server-to-server without our cookie or header; the
    signature is its authentication instead."""
    resp = client.post("/api/liqpay/callback", data={"data": "abc", "signature": "wrong"})
    assert resp.status_code == 403
    assert resp.text == "Invalid signature"
