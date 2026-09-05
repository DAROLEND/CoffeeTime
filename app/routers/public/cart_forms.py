"""AJAX cart endpoints. Routes keep their literal PHP filenames
(/forms/xxx.php) because static/js/menu.js and static/js/cart-edit.js are
reused byte-for-byte and hardcode these exact URLs (confirmed via grep —
see the migration plan). None of these endpoints carried CSRF checks in
the original PHP either (unlike login/register/reviews), so none are
added here — preserving behavior exactly, not just the URLs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import cart as cart_service

router = APIRouter(prefix="/forms")


@router.post("/add_to_cart.php")
async def add_to_cart(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    category = form.get("category", "")
    item_id = int(form.get("id") or 0)
    qty = max(1, min(99, int(form.get("quantity") or 1)))
    result = cart_service.add_to_cart(request.state.session, db, category, item_id, qty, form)
    return result


@router.post("/update_cart.php")
async def update_cart(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    category = form.get("category", "")
    item_id = int(form.get("item_id") or 0)
    action = form.get("action", "")
    qty_field = form.get("qty")
    result = cart_service.update_qty_stepper(
        request.state.session, db, category, item_id, action,
        int(qty_field) if qty_field not in (None, "") else None,
    )
    return result


@router.post("/update_cart_item.php")
async def update_cart_item_route(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    index = int(form.get("index") or -1)
    result = cart_service.update_cart_item(request.state.session, db, index, form)
    return result


@router.post("/update_cart_variant.php")
async def update_cart_variant_route(request: Request):
    form = await request.form()
    category = form.get("category", "")
    item_id = int(form.get("id") or 0)
    variant = form.get("selected_variant", "")
    result = cart_service.update_cart_variant(request.state.session, category, item_id, variant)
    return result


@router.post("/remove_from_cart.php")
async def remove_from_cart_route(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    si = form.get("session_index")
    result = cart_service.remove_from_cart(
        request.state.session, db,
        int(si) if si not in (None, "") else None,
        form.get("category", ""),
        int(form.get("item_id") or 0),
    )
    return result


@router.post("/clear_cart.php")
async def clear_cart_route(request: Request):
    cart_service.clear_cart(request.state.session)
    return {"ok": True}


@router.get("/get_cart_preview.php")
async def get_cart_preview_route(request: Request, db: Session = Depends(get_db)):
    return cart_service.get_cart_preview(request.state.session, db)


@router.get("/get_cart_item.php")
async def get_cart_item_route(
    request: Request,
    db: Session = Depends(get_db),
    index: int | None = Query(None),
    category: str = "",
    id: int = 0,
    variant: str = "",
    selected_size: str = "",
    cheese_crust: int = 0,
):
    return cart_service.get_cart_item(request.state.session, db, index, category, id, variant, selected_size, cheese_crust)
