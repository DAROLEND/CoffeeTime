"""Port of pages/cart.php: the full cart page (quick-add via GET, item
list grouped by category, summary panel). Cart *mutation* AJAX endpoints
live in cart_forms.py; this module only renders."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.cart import ALL_CATEGORIES, resolve_cart_items_full
from app.services.media import item_img
from app.templating import render

router = APIRouter()

CAT_LABELS = {
    "coffee_items": "Кава", "cold_drink_items": "Холодні напої", "fast_food_items": "Фаст-фуд",
    "pizza_items": "Піца", "mini_pizza_items": "Міні-піца", "sushi_items": "Суші",
    "sushi_sets": "Суші-сети", "salad_items": "Салати", "dessert_items": "Десерти",
    "ice_cream_items": "Морозиво", "cake_items": "Торти", "sauces": "Соуси",
}


def _item_word(n: int) -> str:
    n = abs(n) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return "товарів"
    if n1 == 1:
        return "товар"
    if 2 <= n1 <= 4:
        return "товари"
    return "товарів"


def _opt_tags(it: dict) -> list[str]:
    tags = []
    if it.get("selected_size"):
        tags.append("20 см" if it["category"] == "mini_pizza_items" else ("40 см" if it["selected_size"] == "large" else "30 см"))
    if it.get("cheese_crust"):
        tags.append("Сирний бортик")
    if it.get("takeaway"):
        tags.append("З собою")
    if it.get("weight"):
        tags.append(f"{it['weight']} кг")
    if it.get("is_spicy"):
        tags.append("Гостра")
    if it.get("is_cold"):
        tags.append("Холодна")
    if it.get("selected_variant"):
        try:
            sv = json.loads(it["selected_variant"])
        except ValueError:
            sv = None
        if isinstance(sv, dict):
            if sv.get("type") == "filling":
                fl = sv.get("filling_label", "")
                if sv.get("size_label"):
                    fl += " · " + sv["size_label"]
                if fl:
                    tags.append(fl)
            elif "scoop_label" in sv:
                tags.append(sv["scoop_label"])
            elif sv.get("sauces"):
                tags.append(", ".join(s.get("name", "") for s in sv["sauces"]))
    return tags


@router.get("/cart")
def cart_page(request: Request, action: str | None = None, category: str | None = None, id: int | None = None, db: Session = Depends(get_db)):
    session = request.state.session
    cart = session.get("cart")
    if not isinstance(cart, list):
        cart = []
        session["cart"] = cart

    if action == "add" and category and id:
        if category in ALL_CATEGORIES and id > 0:
            session["lastCategory"] = category
            found = None
            for i, it in enumerate(cart):
                if it.get("category") == category and int(it.get("id", -1)) == id:
                    found = i
                    break
            if found is not None:
                cart[found]["quantity"] += 1
            else:
                cart.append({"category": category, "id": id, "quantity": 1})
            session["cart"] = cart
        return RedirectResponse("/cart", status_code=302)

    items = resolve_cart_items_full(db, cart)
    for it in items:
        it["opt_tags"] = _opt_tags(it)
        it["image_url"] = item_img(it.get("image", ""))

    total = sum(it["subtotal"] for it in items)
    total_qty = sum(it["quantity"] for it in items)
    back_cat = session.get("lastCategory", "coffee_items")

    grouped: dict[str, list[dict]] = {}
    for it in items:
        group_key = "pizza_items" if it["category"] == "mini_pizza_items" else it["category"]
        grouped.setdefault(group_key, []).append(it)

    return render(
        request,
        "public/cart.html",
        page="cart",
        page_title="Кошик — Coffee Time",
        items=items,
        grouped_items=grouped,
        cat_labels=CAT_LABELS,
        total=total,
        total_qty=total_qty,
        item_count=len(items),
        item_word=_item_word(len(items)),
        back_cat=back_cat,
    )
