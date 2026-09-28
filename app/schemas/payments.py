from __future__ import annotations

from typing import Literal

from app.schemas.base import Schema


class LiqpayCheckout(Schema):
    """Either a signed LiqPay form to auto-submit, or `dev_bypass` when
    LiqPay isn't configured (the SPA then goes straight to success)."""
    dev_bypass: bool = False
    order_id: int
    total: float = 0
    action_url: str = ""
    data: str = ""
    signature: str = ""
    is_localhost: bool = False
    back_href: str = "/cart"
    back_label: str = ""


class PaymentStatus(Schema):
    status: Literal["pending", "paid", "failed", "cash", "unknown"]


class OrderSummary(Schema):
    order_id: int
    total: float
    customer_name: str
    ready_time: str
    payment_method: str
    payment_status: str
    order_type: str


class PaymentComplete(Schema):
    order: OrderSummary | None
    is_dev_bypass: bool


class PaymentPendingInfo(Schema):
    order_id: int
    liqpay_data: str
    liqpay_signature: str


class PaymentFailureInfo(Schema):
    order_id: int
