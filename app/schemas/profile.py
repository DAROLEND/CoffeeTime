from __future__ import annotations

from pydantic import BaseModel


class ProfileUser(BaseModel):
    login: str
    email: str
    client_name: str
    client_surname: str
    client_PhoneNumber: str  # noqa: N815


class PayBadge(BaseModel):
    cls: str
    label: str


class ProfileOrder(BaseModel):
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


class ProfileOrderGroup(BaseModel):
    key: str
    label: str
    orders: list[ProfileOrder]


class ProfileView(BaseModel):
    user: ProfileUser
    initials: str
    display_name: str
    order_count: int
    total_spent: float
    joined_at: str
    groups: list[ProfileOrderGroup]
    has_orders: bool


class ProfileUpdateRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""


class OrderLine(BaseModel):
    name: str
    image: str
    category: str
    quantity: int
    price: float
    opts: list[str] = []


class OrderLines(BaseModel):
    items: list[OrderLine]


class RateOrderRequest(BaseModel):
    rating: int


class RepayResult(BaseModel):
    redirect: str
