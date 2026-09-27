from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AddToCartRequest(BaseModel):
    """Line *parameters* only. There is deliberately no price field: the
    server computes every price (app/services/pricing.py)."""
    category: str
    id: int
    quantity: int = Field(1, ge=1, le=99)
    selected_size: Literal["small", "large"] | None = None
    cheese_crust: bool = False
    takeaway: bool = False
    weight: float | None = None
    selected_variant: str | None = None


class AddToCartResponse(BaseModel):
    ok: bool
    count: int = 0
    index: int | None = None
    error: str | None = None


class UpdateCartItemRequest(BaseModel):
    """Only the fields that are sent are changed."""
    quantity: int | None = Field(None, ge=1, le=99)
    selected_size: Literal["small", "large"] | None = None
    cheese_crust: bool | None = None
    weight: float | None = None
    selected_variant: str | None = None


class UpdateCartItemResponse(BaseModel):
    ok: bool
    merged: bool = False
    index: int | None = None
    new_price: float = 0
    new_qty: int = 0
    new_subtotal: float = 0
    selected_size: str | None = None
    cheese_crust: int | None = None
    selected_variant: str | None = None
    error: str | None = None


class RemoveFromCartResponse(BaseModel):
    ok: bool
    cart_total: float = 0
    cart_count: int = 0


class CartPreviewItem(BaseModel):
    session_index: int
    category: str
    id: int
    name: str
    image: str
    price: float
    qty: int


class CartPreview(BaseModel):
    ok: bool = True
    items: list[CartPreviewItem]
    total: float
    count: int


class CartLine(BaseModel):
    session_index: int
    category: str
    id: int
    name: str
    description: str
    image: str
    price: float
    quantity: int
    subtotal: float
    opt_tags: list[str]
    editable: bool
    weight: float | None = None


class CartGroup(BaseModel):
    key: str
    label: str
    items: list[CartLine]


class CartView(BaseModel):
    items: list[CartLine]
    groups: list[CartGroup]
    total: float
    total_qty: int
    item_count: int
    item_word: str
    back_category: str


class CartItemDetail(BaseModel):
    """Everything the cart's "edit options" modal needs for one line."""
    cart_index: int
    category: str
    id: int
    name: str
    desc: str
    image: str
    price: float
    unit_price: float
    quantity: int
    selected_size: str | None = None
    cheese_crust: int = 0
    selected_variant: str | None = None
    weight: float | None = None
    price_large: float | None = None
    has_size_choice: bool | None = None
    variant_options: str | None = None
    price_per_kg: float | None = None
    min_weight: float | None = None
