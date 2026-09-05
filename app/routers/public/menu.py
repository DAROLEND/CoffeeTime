"""Port of pages/menu.php: the full catalog page with category tabs,
client-side filter bar, and per-item detail modal (the modal/filter
JS itself is static/js/menu.js, reused unchanged — this route's job is to
emit the exact same data-* attributes that script depends on)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalog import (
    CakeItem, CoffeeItem, ColdDrinkItem, DessertItem, FastFoodItem,
    IceCreamItem, MiniPizzaItem, PizzaItem, SaladItem, Sauce, SushiItem, SushiSet,
)
from app.services.menu import build_card_context, parse_ing_tags
from app.templating import render

router = APIRouter()

TABLES = {
    "coffee_items": "Кава",
    "cold_drink_items": "Холодні напої",
    "pizza_items": "Піца",
    "salad_items": "Салати",
    "dessert_items": "Десерти",
    "cake_items": "Торти на замовлення",
    "fast_food_items": "Фаст-фуд",
    "sushi_items": "Суші",
    "sushi_sets": "Сети суші",
    "sauces": "Соуси",
}

GROUPS = {
    "drinks": {
        "label": "Напої",
        "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4z"/><path d="M7 3c.5.8 1 1 1 2M11 3c.5.8 1 1 1 2"/></svg>',
        "cats": ["coffee_items", "cold_drink_items"],
    },
    "food": {
        "label": "Їжа",
        "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 .6.4 1 1 1h4v7"/></svg>',
        "cats": ["pizza_items", "salad_items", "dessert_items", "cake_items"],
    },
    "fastfood": {
        "label": "Фаст-фуд",
        "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11c0-4 3.6-7 8-7s8 3 8 7"/><path d="M3 11h18"/><path d="M3 15h18"/><path d="M5 19h14a2 2 0 0 0 2-2v-2H3v2a2 2 0 0 0 2 2z"/></svg>',
        "cats": ["fast_food_items", "sauces"],
    },
    "sushi": {
        "label": "Суші",
        "icon": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M3.5 8.5h4M16.5 8.5h4M3.5 15.5h4M16.5 15.5h4"/></svg>',
        "cats": ["sushi_items", "sushi_sets"],
    },
}

_SKIP_ING_TAGS = {"моцарела", "оливкова олія", "4 сири"}


def _rows(db: Session, *cols, order_by) -> list[dict]:
    return [dict(r) for r in db.execute(select(*cols).order_by(order_by)).mappings().all()]


@router.get("/menu")
def menu_page(request: Request, category: str | None = None, scroll_to: int = 0, db: Session = Depends(get_db)):
    if category == "mini_pizza_items":
        return RedirectResponse("/menu?category=pizza_items", status_code=302)
    if category == "ice_cream_items":
        return RedirectResponse("/menu?category=dessert_items", status_code=302)

    current = category if category in TABLES else next(iter(TABLES))

    all_items: dict[str, list[dict]] = {}
    counts: dict[str, int] = {}

    all_items["coffee_items"] = _rows(db, CoffeeItem.id, CoffeeItem.name, CoffeeItem.description, CoffeeItem.image, CoffeeItem.price, CoffeeItem.is_cold, CoffeeItem.popularity, order_by=CoffeeItem.id)
    all_items["cold_drink_items"] = _rows(db, ColdDrinkItem.id, ColdDrinkItem.name, ColdDrinkItem.description, ColdDrinkItem.image, ColdDrinkItem.price, ColdDrinkItem.popularity, order_by=ColdDrinkItem.id)
    all_items["pizza_items"] = _rows(db, PizzaItem.id, PizzaItem.name, PizzaItem.description, PizzaItem.image, PizzaItem.price, PizzaItem.price_large, PizzaItem.sauce_type, PizzaItem.is_spicy, PizzaItem.has_size_choice, PizzaItem.ingredients_tags, PizzaItem.popularity, order_by=PizzaItem.id)
    all_items["salad_items"] = _rows(db, SaladItem.id, SaladItem.name, SaladItem.description, SaladItem.image, SaladItem.price, SaladItem.popularity, order_by=SaladItem.id)
    all_items["dessert_items"] = _rows(db, DessertItem.id, DessertItem.name, DessertItem.description, DessertItem.image, DessertItem.price, DessertItem.popularity, order_by=DessertItem.id)
    all_items["cake_items"] = [
        {**row, "price": row.pop("price_per_kg")}
        for row in _rows(db, CakeItem.id, CakeItem.name, CakeItem.description, CakeItem.image, CakeItem.price_per_kg, CakeItem.min_weight, CakeItem.popularity, order_by=CakeItem.id)
    ]
    all_items["fast_food_items"] = _rows(db, FastFoodItem.id, FastFoodItem.name, FastFoodItem.description, FastFoodItem.image, FastFoodItem.price, FastFoodItem.variant_options, FastFoodItem.popularity, order_by=FastFoodItem.id)
    all_items["sushi_items"] = _rows(db, SushiItem.id, SushiItem.name, SushiItem.description, SushiItem.image, SushiItem.price, SushiItem.weight, SushiItem.popularity, order_by=SushiItem.id)
    all_items["sushi_sets"] = _rows(db, SushiSet.id, SushiSet.name, SushiSet.description, SushiSet.image, SushiSet.price, SushiSet.weight, SushiSet.pieces_count, SushiSet.popularity, order_by=SushiSet.id)

    for tbl in TABLES:
        if tbl == "sauces":
            continue
        counts[tbl] = len(all_items.get(tbl, []))

    # Ice cream (merged into desserts section)
    all_items["ice_cream_items"] = _rows(db, IceCreamItem.id, IceCreamItem.name, IceCreamItem.description, IceCreamItem.image, IceCreamItem.price, IceCreamItem.variant_options, IceCreamItem.popularity, order_by=IceCreamItem.id)
    counts["ice_cream_items"] = len(all_items["ice_cream_items"])

    # Mini pizza (merged into pizza section)
    all_items["mini_pizza_items"] = _rows(db, MiniPizzaItem.id, MiniPizzaItem.name, MiniPizzaItem.description, MiniPizzaItem.image, MiniPizzaItem.price, MiniPizzaItem.sauce_type, MiniPizzaItem.is_spicy, MiniPizzaItem.ingredients_tags, MiniPizzaItem.popularity, order_by=MiniPizzaItem.id)
    counts["mini_pizza_items"] = len(all_items["mini_pizza_items"])

    # Ingredient chips for pizza filter
    all_ing_tags: list[str] = []
    for pi in all_items["pizza_items"] + all_items["mini_pizza_items"]:
        for t in parse_ing_tags(pi.get("ingredients_tags")):
            if t and t not in all_ing_tags and t.lower() not in _SKIP_ING_TAGS:
                all_ing_tags.append(t)
    all_ing_tags.sort()

    # Sauces (add-on modal + standalone menu section)
    sauces = [dict(s) for s in db.execute(
        select(Sauce.id, Sauce.name, Sauce.price, Sauce.image, Sauce.emoji)
        .where(Sauce.active == True)  # noqa: E712
        .order_by(Sauce.sort_order)
    ).mappings().all()]
    all_items["sauces"] = [{**s, "description": "", "popularity": 0} for s in sauces]
    counts["sauces"] = len(all_items["sauces"])

    cart = request.state.session.get("cart", [])
    cart_keys = {f"{ci['category']}_{ci['id']}" for ci in cart if "category" in ci and "id" in ci}

    current_group = "drinks"
    for gid, g in GROUPS.items():
        if current in g["cats"]:
            current_group = gid
            break

    # Build render-ready card contexts per section (mirrors renderCard() loop)
    cards_by_tbl: dict[str, list[dict]] = {}
    card_idx = 0
    for tbl, label in TABLES.items():
        cards = []
        for item in all_items.get(tbl, []):
            cards.append(build_card_context(item, tbl, label, cart_keys, card_idx))
            card_idx += 1
        cards_by_tbl[tbl] = cards
        if tbl == "pizza_items":
            mini_cards = []
            for item in all_items["mini_pizza_items"]:
                mini_cards.append(build_card_context(item, "mini_pizza_items", "Міні-піца", cart_keys, card_idx))
                card_idx += 1
            cards_by_tbl["pizza_items"] += mini_cards
        if tbl == "dessert_items":
            ic_cards = []
            for item in all_items["ice_cream_items"]:
                ic_cards.append(build_card_context(item, "ice_cream_items", "Морозиво", cart_keys, card_idx))
                card_idx += 1
            cards_by_tbl["dessert_items"] += ic_cards

    sub_tab_counts = {
        "pizza_items": counts["pizza_items"] + counts["mini_pizza_items"],
        "dessert_items": counts["dessert_items"] + counts["ice_cream_items"],
    }

    return render(
        request,
        "public/menu.html",
        page="menu",
        page_title="Меню — Coffee Time",
        tables=TABLES,
        groups=GROUPS,
        current=current,
        current_group=current_group,
        counts=counts,
        sub_tab_counts=sub_tab_counts,
        all_ing_tags=all_ing_tags,
        sauces=sauces,
        cards_by_tbl=cards_by_tbl,
        cart_keys_json=json.dumps(sorted(cart_keys), ensure_ascii=False),
        current_json=json.dumps(current, ensure_ascii=False),
        scroll_to=scroll_to,
    )
