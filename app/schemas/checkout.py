from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CheckoutItem(BaseModel):
    id: int
    category: str
    name: str
    image: str
    price: float
    quantity: int
    subtotal: float


class DaySchedule(BaseModel):
    open: str
    close: str


class NextAvailable(BaseModel):
    time: str
    label: str
    is_today: bool


class CheckoutPrefill(BaseModel):
    first_name: str
    last_name: str
    phone: str
    customer_email: str
    ready_time: str
    comment: str
    payment: str
    order_type: Literal["dine_in", "takeaway"]


class CheckoutView(BaseModel):
    items: list[CheckoutItem]
    total: float
    has_cakes: bool
    prep_minutes: int
    # ISO weekday "1".."7" -> hours. Keys are strings because JSON objects are.
    schedule: dict[str, DaySchedule]
    next_available: NextAvailable | None
    # Café-local (Europe/Kyiv) wall-clock time, so the time picker works
    # in the café's timezone even if the customer's device isn't.
    server_now: str
    max_days_ahead: int
    prefill: CheckoutPrefill
    user_email: str
    has_pending_order: bool


class CheckoutRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    customer_email: str = ""
    ready_time: str = ""
    comment: str = ""
    payment: str = ""
    order_type: str = "dine_in"
    travel_minutes: int = 15


class CheckoutResult(BaseModel):
    order_id: int
    # "success": order placed (cash) -> /payment-success
    # "liqpay": go to /liqpay-checkout to pay online
    next: Literal["success", "liqpay"]
