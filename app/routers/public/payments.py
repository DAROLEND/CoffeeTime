"""Port of liqpay_checkout.php, liqpay_callback.php, check_payment_status.php,
and pages/payment_success.php / payment_pending.php / payment_failure.php."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.models.orders import Order
from app.services.liqpay import LiqPay, verify_and_decode
from app.services.telegram import notify_order_from_db
from app.templating import render

router = APIRouter()

_LOCALHOST_RE = re.compile(
    r"localhost|127\.0\.0\.1|https?://192\.168\.\d+\.\d+|https?://10\.\d+\.\d+\.\d+"
    r"|https?://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+"
)


def _site_url(request: Request) -> str:
    settings = get_settings()
    return settings.APP_URL.rstrip("/") if settings.APP_URL else str(request.base_url).rstrip("/")


@router.get("/liqpay-checkout")
def liqpay_checkout_page(request: Request, back: str | None = None, db: Session = Depends(get_db)):
    session = request.state.session
    settings = get_settings()

    order_id = int(session.get("pending_order_id") or 0)
    total = float(session.get("pending_order_total") or 0)
    if not order_id or total <= 0:
        return RedirectResponse("/cart", status_code=302)

    order = db.get(Order, order_id)
    if not order:
        return RedirectResponse("/cart", status_code=302)

    site_url = _site_url(request)
    liqpay_ready = bool(settings.LIQPAY_PUBLIC_KEY) and bool(settings.LIQPAY_PRIVATE_KEY) and settings.APP_ENV != "development"

    if not liqpay_ready:
        session["pending_order_id"] = order_id
        session["dev_payment_skip"] = True
        return RedirectResponse("/payment-success", status_code=302)

    liqpay = LiqPay(settings.LIQPAY_PUBLIC_KEY, settings.LIQPAY_PRIVATE_KEY)
    liqpay_oid = f"coffeetime_{order_id}"
    amount = round(float(order.total), 2)
    is_localhost = bool(_LOCALHOST_RE.search(site_url))

    params = {
        "action": "pay", "amount": amount, "currency": "UAH",
        "description": f"Замовлення у Coffee Time #{order_id}",
        "order_id": liqpay_oid, "version": 3, "language": "uk",
    }
    if not is_localhost:
        params["result_url"] = f"{site_url}/payment-success"
        params["server_url"] = f"{site_url}/liqpay-callback"
    if settings.LIQPAY_SANDBOX:
        params["sandbox"] = 1

    data = liqpay.cnb_data(params)
    signature = liqpay.cnb_signature(data)
    session["liqpay_data"] = data
    session["liqpay_signature"] = signature

    from_profile = back == "profile"
    back_href = "/profile?tab=orders" if from_profile else f"/checkout?cancel_order={order_id}"
    back_label = "← Повернутися до замовлень" if from_profile else "← Повернутися до оформлення"

    return render(
        request, "public/liqpay_checkout.html", order_id=order_id, total=order.total,
        data=data, signature=signature, is_localhost=is_localhost,
        back_href=back_href, back_label=back_label,
    )


@router.post("/liqpay-callback")
async def liqpay_callback(request: Request, db: Session = Depends(get_db)):
    """Server-to-server webhook — LiqPay's own request, no session/CSRF."""
    settings = get_settings()
    form = await request.form()
    data = form.get("data", "")
    signature = form.get("signature", "")
    if not data or not signature:
        return PlainTextResponse("Missing data or signature", status_code=400)

    liqpay = LiqPay(settings.LIQPAY_PUBLIC_KEY, settings.LIQPAY_PRIVATE_KEY)
    result = verify_and_decode(liqpay, data, signature)
    if not result:
        return PlainTextResponse("Invalid signature", status_code=403)

    order_id, payment_status, order_status = result["order_id"], result["payment_status"], result["order_status"]

    if order_status:
        from datetime import datetime
        paid_at = datetime.utcnow() if payment_status == "paid" else None
        db.execute(update(Order).where(Order.order_id == order_id).values(payment_status=payment_status, status=order_status, paid_at=paid_at))
    else:
        db.execute(update(Order).where(Order.order_id == order_id).values(payment_status=payment_status))
    db.commit()

    if payment_status == "paid":
        notify_order_from_db(db, order_id)

    return PlainTextResponse("OK", status_code=200)


@router.get("/check-payment-status")
def check_payment_status(request: Request, order_id: int = 0, db: Session = Depends(get_db)):
    session = request.state.session
    if not order_id or int(session.get("pending_order_id") or 0) != order_id:
        return {"status": "unknown"}
    order = db.get(Order, order_id)
    if not order:
        return {"status": "unknown"}
    status = order.payment_status
    return {"status": status.value if hasattr(status, "value") else (status or "pending")}


@router.api_route("/payment-success", methods=["GET", "POST"])
async def payment_success(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    settings = get_settings()

    is_dev_bypass = bool(session.pop("dev_payment_skip", False))
    order_id = 0
    payment_status = "pending"

    if request.method == "POST":
        form = await request.form()
        data, signature = form.get("data", ""), form.get("signature", "")
        if data and signature:
            liqpay = LiqPay(settings.LIQPAY_PUBLIC_KEY, settings.LIQPAY_PRIVATE_KEY)
            result = verify_and_decode(liqpay, data, signature)
            if result:
                order_id = result["order_id"]
                payment_status = result["payment_status"]

    if not order_id:
        order_id = int(session.get("pending_order_id") or 0)

    if payment_status == "failed":
        return RedirectResponse("/payment-failure", status_code=302)

    order = db.get(Order, order_id) if order_id > 0 else None

    if is_dev_bypass and order_id > 0:
        notify_order_from_db(db, order_id)

    session.pop("cart", None)
    session.pop("pending_order_id", None)
    session.pop("pending_order_total", None)

    return render(request, "public/payment_success.html", is_dev_bypass=is_dev_bypass, order=order)


@router.get("/payment-pending")
def payment_pending(request: Request, order_id: int = 0):
    session = request.state.session
    order_id = order_id or int(session.get("pending_order_id") or 0)
    if not order_id:
        return RedirectResponse("/cart", status_code=302)

    return render(
        request, "public/payment_pending.html", page="payment_pending", order_id=order_id,
        check_url=f"/check-payment-status?order_id={order_id}",
        success_url="/payment-success", failure_url="/payment-failure",
        liqpay_data=session.get("liqpay_data", ""), liqpay_signature=session.get("liqpay_signature", ""),
    )


@router.get("/payment-failure")
def payment_failure(request: Request):
    session = request.state.session
    order_id = int(session.get("pending_order_id") or 0)
    return render(request, "public/payment_failure.html", order_id=order_id)
