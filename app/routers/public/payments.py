"""LiqPay checkout, webhook callback, the browser return URL, payment
status polling, and the data behind the success/pending/failure pages.

Two endpoints here are called by LiqPay rather than by the SPA, so they
are mounted on `webhook_router` (no CSRF dependency, see
app/api/router.py):
- `POST /api/liqpay/callback` — server-to-server status notification.
- `GET|POST /api/liqpay/result` — LiqPay's `result_url`, where the
  customer's browser lands after paying. It verifies the payload and
  redirects to the SPA's result page.
"""
from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.config import get_settings
from app.db.session import get_db
from app.models.orders import Order
from app.schemas.payments import (
    LiqpayCheckout, PaymentComplete, PaymentFailureInfo, PaymentPendingInfo, PaymentStatus,
)
from app.services.enum_utils import enum_value
from app.services.liqpay import LiqPay, verify_and_decode
from app.services.telegram import notify_order_from_db

router = APIRouter(tags=["payments"])
webhook_router = APIRouter(tags=["payments"])

LIQPAY_ACTION_URL = "https://www.liqpay.ua/api/3/checkout"
_LOCALHOST_RE = re.compile(
    r"localhost|127\.0\.0\.1|https?://192\.168\.\d+\.\d+|https?://10\.\d+\.\d+\.\d+"
    r"|https?://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+"
)


def _site_url(request: Request) -> str:
    """Public origin of the site (the SPA's origin, which proxies /api)."""
    settings = get_settings()
    return settings.APP_URL.rstrip("/") if settings.APP_URL else str(request.base_url).rstrip("/")


def _liqpay() -> LiqPay:
    settings = get_settings()
    return LiqPay(settings.LIQPAY_PUBLIC_KEY, settings.LIQPAY_PRIVATE_KEY)


def _own_order_id(session, order_id: int) -> bool:
    """Only the session that placed an order may poll or view it."""
    return bool(order_id) and order_id in (
        int(session.get("pending_order_id") or 0), int(session.get("last_order_id") or 0),
    )


@router.get("/liqpay/checkout", response_model=LiqpayCheckout)
def liqpay_checkout(request: Request, back: str | None = None, db: Session = Depends(get_db)):
    """Signed `data`/`signature` for the LiqPay form. The SPA renders a
    hidden form with them and submits it to LiqPay's own domain."""
    session = request.state.session
    settings = get_settings()

    order_id = int(session.get("pending_order_id") or 0)
    total = float(session.get("pending_order_total") or 0)
    order = db.get(Order, order_id) if order_id and total > 0 else None
    if order is None:
        raise ApiError(409, "Немає замовлення для оплати.", code="no_pending_order")

    liqpay_ready = bool(settings.LIQPAY_PUBLIC_KEY) and bool(settings.LIQPAY_PRIVATE_KEY) and settings.APP_ENV != "development"
    if not liqpay_ready:
        session["dev_payment_skip"] = True
        return {"dev_bypass": True, "order_id": order_id, "total": float(order.total)}

    site_url = _site_url(request)
    is_localhost = bool(_LOCALHOST_RE.search(site_url))
    params = {
        "action": "pay", "amount": round(float(order.total), 2), "currency": "UAH",
        "description": f"Замовлення у Coffee Time #{order_id}",
        "order_id": f"coffeetime_{order_id}", "version": 3, "language": "uk",
    }
    if not is_localhost:
        params["result_url"] = f"{site_url}/api/liqpay/result"
        params["server_url"] = f"{site_url}/api/liqpay/callback"
    if settings.LIQPAY_SANDBOX:
        params["sandbox"] = 1

    liqpay = _liqpay()
    data = liqpay.cnb_data(params)
    signature = liqpay.cnb_signature(data)
    session["liqpay_data"] = data
    session["liqpay_signature"] = signature

    from_profile = back == "profile"
    return {
        "order_id": order_id, "total": float(order.total), "action_url": LIQPAY_ACTION_URL,
        "data": data, "signature": signature, "is_localhost": is_localhost,
        "back_href": "/profile?tab=orders" if from_profile else "/checkout?cancel=1",
        "back_label": "← Повернутися до замовлень" if from_profile else "← Повернутися до оформлення",
    }


@webhook_router.post("/liqpay/callback", response_class=PlainTextResponse)
async def liqpay_callback(request: Request, db: Session = Depends(get_db)):
    """Server-to-server webhook — LiqPay's own request, no session/CSRF."""
    form = await request.form()
    data = form.get("data", "")
    signature = form.get("signature", "")
    if not data or not signature:
        return PlainTextResponse("Missing data or signature", status_code=400)

    result = verify_and_decode(_liqpay(), data, signature)
    if not result:
        return PlainTextResponse("Invalid signature", status_code=403)

    order_id, payment_status, order_status = result["order_id"], result["payment_status"], result["order_status"]
    if order_status:
        paid_at = datetime.utcnow() if payment_status == "paid" else None
        db.execute(update(Order).where(Order.order_id == order_id).values(payment_status=payment_status, status=order_status, paid_at=paid_at))
    else:
        db.execute(update(Order).where(Order.order_id == order_id).values(payment_status=payment_status))
    db.commit()

    if payment_status == "paid":
        notify_order_from_db(db, order_id)
    return PlainTextResponse("OK", status_code=200)


@webhook_router.api_route("/liqpay/result", methods=["GET", "POST"], include_in_schema=False)
async def liqpay_result(request: Request):
    """LiqPay's `result_url`. The browser arrives here cross-site (so the
    SameSite=Lax session cookie may be missing on a POST); only the signed
    payload decides where to send it."""
    target = "/payment-success"
    if request.method == "POST":
        form = await request.form()
        data, signature = form.get("data", ""), form.get("signature", "")
        if data and signature:
            result = verify_and_decode(_liqpay(), data, signature)
            if result and result["payment_status"] == "failed":
                target = "/payment-failure"
    return RedirectResponse(target, status_code=303)


@router.get("/payments/status", response_model=PaymentStatus)
def payment_status(request: Request, order_id: int = 0, db: Session = Depends(get_db)):
    if not _own_order_id(request.state.session, order_id):
        return {"status": "unknown"}
    order = db.get(Order, order_id)
    if not order:
        return {"status": "unknown"}
    return {"status": enum_value(order.payment_status) or "pending"}


@router.post("/payments/complete", response_model=PaymentComplete)
def payment_complete(request: Request, db: Session = Depends(get_db)):
    """Called once by the success page: clears the cart and returns the
    order summary. Idempotent — a repeat call (page refresh, React's
    StrictMode double effect) returns the same order."""
    session = request.state.session
    pending_id = int(session.get("pending_order_id") or 0)
    if pending_id:
        # First completion of this order.
        order_id = pending_id
        is_dev_bypass = bool(session.pop("dev_payment_skip", False))
        session.pop("cart", None)
        session.pop("checkout_draft", None)
        session.pop("pending_order_id", None)
        session.pop("pending_order_total", None)
        session["last_order_id"] = order_id
        session["last_order_dev_bypass"] = is_dev_bypass
        if is_dev_bypass and db.get(Order, order_id) is not None:
            notify_order_from_db(db, order_id)
    else:
        order_id = int(session.get("last_order_id") or 0)
        is_dev_bypass = bool(session.get("last_order_dev_bypass"))

    order = db.get(Order, order_id) if order_id > 0 else None
    summary = None
    if order is not None:
        summary = {
            "order_id": order.order_id, "total": float(order.total),
            "customer_name": order.customer_name or "", "ready_time": order.ready_time or "",
            "payment_method": order.payment_method or "", "payment_status": enum_value(order.payment_status) or "pending",
            "order_type": enum_value(order.order_type) or "dine_in",
        }
    return {"order": summary, "is_dev_bypass": is_dev_bypass}


@router.get("/payments/pending", response_model=PaymentPendingInfo)
def payment_pending(request: Request, order_id: int = 0):
    session = request.state.session
    order_id = order_id or int(session.get("pending_order_id") or 0)
    if not _own_order_id(session, order_id):
        raise ApiError(404, "Замовлення не знайдено.", code="not_found")
    return {
        "order_id": order_id,
        "liqpay_data": session.get("liqpay_data", ""),
        "liqpay_signature": session.get("liqpay_signature", ""),
    }


@router.get("/payments/failure", response_model=PaymentFailureInfo)
def payment_failure(request: Request):
    return {"order_id": int(request.state.session.get("pending_order_id") or 0)}
