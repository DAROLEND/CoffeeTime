from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LiqpayCheckout(BaseModel):
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


class PaymentStatus(BaseModel):
    status: Literal["pending", "paid", "failed", "cash", "unknown"]


class OrderSummary(BaseModel):
    order_id: int
    total: float
    customer_name: str
    ready_time: str
    payment_method: str
    payment_status: str
    order_type: str


class PaymentComplete(BaseModel):
    order: OrderSummary | None
    is_dev_bypass: bool


class PaymentPendingInfo(BaseModel):
    order_id: int
    liqpay_data: str
    liqpay_signature: str


class PaymentFailureInfo(BaseModel):
    order_id: int
