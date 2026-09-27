"""The menu catalog: every category's cards in one response (the SPA
switches tabs and searches across categories without refetching), plus
a single-category endpoint. Card flags/prices come from
app/services/menu.build_card_context."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalog import (
    CakeItem, CoffeeItem, ColdDrinkItem, DessertItem, FastFoodItem,
    IceCreamItem, MiniPizzaItem, PizzaItem, SaladItem, Sauce, SushiItem, SushiSet,
)
from app.api.errors import not_found
from app.schemas.menu import MenuCard, MenuResponse
from app.services.item_labels import SUB_CATEGORY_PARENT
from app.services.media import item_img
from app.services.menu import build_card_context, parse_ing_tags

router = APIRouter(prefix="/menu", tags=["menu"])

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


def _load_all(db: Session) -> dict[str, list[dict]]:
    all_items: dict[str, list[dict]] = {}
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
    # Ice cream is shown inside the desserts tab, mini pizza inside pizza.
    all_items["ice_cream_items"] = _rows(db, IceCreamItem.id, IceCreamItem.name, IceCreamItem.description, IceCreamItem.image, IceCreamItem.price, IceCreamItem.variant_options, IceCreamItem.popularity, order_by=IceCreamItem.id)
    all_items["mini_pizza_items"] = _rows(db, MiniPizzaItem.id, MiniPizzaItem.name, MiniPizzaItem.description, MiniPizzaItem.image, MiniPizzaItem.price, MiniPizzaItem.sauce_type, MiniPizzaItem.is_spicy, MiniPizzaItem.ingredients_tags, MiniPizzaItem.popularity, order_by=MiniPizzaItem.id)
    all_items["sauces"] = [{**s, "description": "", "popularity": 0} for s in _active_sauces(db)]
    return all_items


def _active_sauces(db: Session) -> list[dict]:
    return [dict(s) for s in db.execute(
        select(Sauce.id, Sauce.name, Sauce.price, Sauce.image, Sauce.emoji)
        .where(Sauce.active == True)  # noqa: E712
        .order_by(Sauce.sort_order)
    ).mappings().all()]


def _card(item: dict, tbl: str, label: str, idx: int) -> MenuCard:
    c = build_card_context(item, tbl, label, set(), idx)
    return MenuCard(
        id=c["id"], category=tbl, label=label, name=c["name"], description=c["description"], order=idx,
        image=c["img_src"], price=c["price"], popularity=c["popularity"],
        is_pizza=c["is_pizza"], is_mini_pizza=c["is_mini_pizza"], is_pizza_type=c["is_pizza_type"],
        is_fast_food=c["is_fast_food"], is_cold_coffee=c["is_cold_coffee"], is_ice_cream=c["is_ice_cream"],
        is_sushi=c["is_sushi"], is_sushi_set=c["is_sushi_set"], sushi_tags=c["sushi_tags"],
        has_fast_food_size=c["has_fast_food_size"], has_sauce_variant=c["has_sauce_variant"],
        has_ice_cream_scoop=c["has_ice_cream_scoop"], ff_small_price=c["ff_small_price"],
        ff_large_price=c["ff_large_price"], ff_size_str=c["ff_size_str"], has_size=c["has_size"],
        price_large=c["price_large"], sauce_type=str(getattr(c["sauce_type"], "value", c["sauce_type"]) or ""),
        is_spicy=c["is_spicy"], tags=c["tags_arr"], price_per_kg=c["price_per_kg"], min_weight=c["min_weight"],
        variant_options=c["variant_options"],
    )


def _sections(all_items: dict[str, list[dict]]) -> dict[str, list[MenuCard]]:
    """One list of cards per tab, in display order; `order` is a global
    running index the client's "default" sort restores."""
    sections: dict[str, list[MenuCard]] = {}
    idx = 0
    for tbl, label in TABLES.items():
        cards = []
        for item in all_items.get(tbl, []):
            cards.append(_card(item, tbl, label, idx))
            idx += 1
        extra = {"pizza_items": ("mini_pizza_items", "Міні-піца"), "dessert_items": ("ice_cream_items", "Морозиво")}.get(tbl)
        if extra:
            for item in all_items[extra[0]]:
                cards.append(_card(item, extra[0], extra[1], idx))
                idx += 1
        sections[tbl] = cards
    return sections


def resolve_current(category: str | None) -> str:
    category = SUB_CATEGORY_PARENT.get(category or "", category)
    return category if category in TABLES else next(iter(TABLES))


@router.get("", response_model=MenuResponse)
def menu(category: str | None = None, db: Session = Depends(get_db)):
    """The whole menu. `category` only selects the initially active tab
    (mini pizza/ice cream resolve to their parent tab)."""
    current = resolve_current(category)
    all_items = _load_all(db)
    sections = _sections(all_items)

    # Ingredient chips for the pizza filter
    all_ing_tags: list[str] = []
    for pi in all_items["pizza_items"] + all_items["mini_pizza_items"]:
        for t in parse_ing_tags(pi.get("ingredients_tags")):
            if t and t not in all_ing_tags and t.lower() not in _SKIP_ING_TAGS:
                all_ing_tags.append(t)
    all_ing_tags.sort()

    current_group = next((gid for gid, g in GROUPS.items() if current in g["cats"]), "drinks")

    return MenuResponse(
        current=current,
        current_group=current_group,
        groups=[{"id": gid, "label": g["label"], "icon": g["icon"], "categories": g["cats"]} for gid, g in GROUPS.items()],
        tabs=[{"key": tbl, "label": label, "count": len(sections[tbl])} for tbl, label in TABLES.items()],
        sections=sections,
        ingredient_tags=all_ing_tags,
        sauces=[
            {"id": s["id"], "name": s["name"], "price": float(s["price"] or 0), "emoji": s["emoji"] or "",
             "image": item_img(s["image"])}
            for s in all_items["sauces"]
        ],
    )


@router.get("/{category}", response_model=list[MenuCard])
def menu_category(category: str, db: Session = Depends(get_db)):
    """Cards of one menu tab (e.g. `pizza_items` includes mini pizzas)."""
    if SUB_CATEGORY_PARENT.get(category, category) not in TABLES:
        raise not_found("Невідома категорія.")
    return _sections(_load_all(db))[resolve_current(category)]
