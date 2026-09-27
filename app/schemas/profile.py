from __future__ import annotations

from app.schemas.base import Schema


class ProfileUser(Schema):
    login: str
    email: str
    client_name: str
    client_surname: str
    client_PhoneNumber: str  # noqa: N815


class PayBadge(Schema):
    cls: str
    label: str


class ProfileOrder(Schema):
    order_id: int
    items_count: int
    preview_names: list[str]
    preview_remaining: int
    rating: int | None
    is_pending: bool
    is_done: bool
    status: str
    status_label: str | None
    payment_status: str
    pay_badge: PayBadge
    total: float
    created_at: str
    ready_time: str
    comment: str


class ProfileOrderGroup(Schema):
    key: str
    label: str
    orders: list[ProfileOrder]


class ProfileView(Schema):
    user: ProfileUser
    initials: str
    display_name: str
    order_count: int
    total_spent: float
    joined_at: str
    groups: list[ProfileOrderGroup]
    has_orders: bool


class ProfileUpdateRequest(Schema):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""


class OrderLine(Schema):
    name: str
    image: str
    category: str
    quantity: int
    price: float
    opts: list[str] = []


class OrderLines(Schema):
    items: list[OrderLine]


class RateOrderRequest(Schema):
    rating: int


class RepayResult(Schema):
    redirect: str
