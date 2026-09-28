"""Cart API. The cart lives in the server-side session; lines are
addressed by index (see app/services/cart.py for why). Prices are never
accepted from the client."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.errors import ApiError, bad_request
from app.db.session import get_db
from app.schemas.cart import (
    AddToCartRequest, AddToCartResponse, CartItemDetail, CartPreview, CartView,
    RemoveFromCartResponse, UpdateCartItemRequest, UpdateCartItemResponse,
)
from app.schemas.common import OkResponse
from app.services import cart as cart_service
from app.services.item_labels import SUB_CATEGORY_PARENT

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartView)
def get_cart(request: Request, db: Session = Depends(get_db)):
    return cart_service.build_cart_view(request.state.session, db)


@router.delete("", response_model=OkResponse)
def clear_cart(request: Request):
    cart_service.clear_cart(request.state.session)
    return {"ok": True}


@router.get("/preview", response_model=CartPreview)
def cart_preview(request: Request, db: Session = Depends(get_db)):
    """Compact list for the header's mini-cart dropdown."""
    return cart_service.get_cart_preview(request.state.session, db)


@router.post("/items", response_model=AddToCartResponse)
def add_item(body: AddToCartRequest, request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    form = {
        "weight": body.weight,
        "selected_size": body.selected_size,
        "cheese_crust": "1" if body.cheese_crust else "0",
        "takeaway": "1" if body.takeaway else "0",
        "selected_variant": body.selected_variant,
    }
    result = cart_service.add_to_cart(session, db, body.category, body.id, body.quantity, form)
    if not result["ok"]:
        raise bad_request(
            "Обраний варіант недоступний." if result.get("error") == "invalid_variant" else "Товар недоступний.",
            code=result.get("error") or "unavailable",
        )
    if body.category in cart_service.ALL_CATEGORIES and body.category != "sauces":
        session["lastCategory"] = SUB_CATEGORY_PARENT.get(body.category, body.category)
    return result


@router.get("/items/{index}", response_model=CartItemDetail)
def get_item(index: int, request: Request, db: Session = Depends(get_db)):
    result = cart_service.get_cart_item(request.state.session, db, index)
    if not result["ok"]:
        raise ApiError(404, "Товар не знайдено в кошику.", code=result.get("error"))
    return result


@router.patch("/items/{index}", response_model=UpdateCartItemResponse)
def update_item(index: int, body: UpdateCartItemRequest, request: Request, db: Session = Depends(get_db)):
    form = {}
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "cheese_crust":
            value = "1" if value else "0"
        form[key] = value
    result = cart_service.update_cart_item(request.state.session, db, index, form)
    if not result["ok"]:
        if result.get("error") == "invalid_index":
            raise ApiError(404, "Товар не знайдено в кошику.", code="invalid_index")
        raise bad_request("Не вдалося оновити товар.", code=result.get("error") or "update_failed")
    return result


@router.delete("/items/{index}", response_model=RemoveFromCartResponse)
def remove_item(index: int, request: Request, db: Session = Depends(get_db)):
    result = cart_service.remove_from_cart(request.state.session, db, index)
    if not result["ok"]:
        raise ApiError(404, "Товар не знайдено в кошику.", code="invalid_index")
    return result
