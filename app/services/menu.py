"""Port of pages/menu.php's local helpers: parseIngTags(), fmtPrice(), and
the big renderCard() function — split here into a pure data-prep function
(build_card_context) so the Jinja template only handles markup, while all
the "is this a pizza / does it have a fast-food size choice / what's the
cheese-crust badge" branching logic lives in one testable place, exactly
mirroring the PHP branch-for-branch.
"""
from __future__ import annotations

import json

DEFAULT_IMAGE = "static/images/menu_items/default.jpg"


def parse_ing_tags(raw: str | None) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw[0] == "[":
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                return [t.strip() for t in decoded if isinstance(t, str) and t.strip()]
        except ValueError:
            pass
    return [t.strip() for t in raw.split(",") if t.strip()]


def fmt_price(p: float) -> str:
    if p == int(p):
        s = f"{int(p):,}".replace(",", " ").replace(" ", " ")
    else:
        s = f"{p:,.2f}".replace(",", " ").replace(".", ",").replace(" ", " ")
    return f"{s} ₴"


def build_card_context(item: dict, tbl: str, label: str, cart_keys: set[str], card_idx: int = 0) -> dict:
    item_id = item["id"]
    in_cart = f"{tbl}_{item_id}" in cart_keys
    is_pizza = tbl == "pizza_items"
    is_mini_pizza = tbl == "mini_pizza_items"
    is_pizza_type = is_pizza or is_mini_pizza
    is_fast_food = tbl == "fast_food_items"
    is_cold_coffee = tbl == "coffee_items" and bool(item.get("is_cold"))
    is_ice_cream = tbl == "ice_cream_items"
    is_sushi = tbl == "sushi_items"
    is_sushi_set = tbl == "sushi_sets"

    sushi_tags: list[str] = []
    if (is_sushi or is_sushi_set) and item.get("weight"):
        sushi_tags.append(item["weight"])
    if is_sushi_set and item.get("pieces_count"):
        sushi_tags.append(f"{int(item['pieces_count'])} шт")

    variant_options_raw = item.get("variant_options") or ""
    has_fast_food_size = is_fast_food and bool(variant_options_raw) and (
        '"type":"size"' in variant_options_raw or '"type":"filling"' in variant_options_raw
    )
    has_sauce_variant = is_fast_food and bool(variant_options_raw) and not has_fast_food_size
    has_ice_cream_scoop = is_ice_cream and bool(variant_options_raw)

    price = float(item.get("price", 0) or 0)
    ff_small_price = ff_large_price = price
    ff_size_str = ""
    if has_fast_food_size:
        try:
            ff_vo = json.loads(variant_options_raw)
        except ValueError:
            ff_vo = {}
        options = ff_vo.get("options") if isinstance(ff_vo, dict) else None
        if isinstance(options, list):
            labels = []
            max_diff = 0.0
            for opt in options:
                labels.append(opt.get("label", ""))
                d = float(opt.get("price_diff", 0) or 0)
                sizes = opt.get("sizes")
                if isinstance(sizes, list):
                    for sz in sizes:
                        td = d + float(sz.get("price_diff", 0) or 0)
                        max_diff = max(max_diff, td)
                else:
                    max_diff = max(max_diff, d)
            if max_diff > 0:
                ff_large_price = ff_small_price + max_diff
            if ff_vo.get("type") == "size" and len(labels) == 2:
                ff_size_str = " / ".join(labels)

    has_size = is_pizza and bool(item.get("has_size_choice"))
    price_large = float(item.get("price_large") or 0) if is_pizza else 0.0
    sauce_type = (item.get("sauce_type") or "tomato") if is_pizza_type else ""
    is_spicy = bool(item.get("is_spicy")) if is_pizza_type else False
    ing_tags_raw = (item.get("ingredients_tags") or "") if is_pizza_type else ""
    tags_arr = parse_ing_tags(ing_tags_raw) if is_pizza_type else []
    popularity = int(item.get("popularity", 0) or 0)

    image = item.get("image") or ""
    is_default = image == DEFAULT_IMAGE or not image
    img_src = "" if is_default else "/" + image

    return {
        "id": item_id,
        "tbl": tbl,
        "label": label,
        "name": item["name"],
        "description": item.get("description") or "",
        "card_idx": card_idx,
        "in_cart": in_cart,
        "is_pizza": is_pizza,
        "is_mini_pizza": is_mini_pizza,
        "is_pizza_type": is_pizza_type,
        "is_fast_food": is_fast_food,
        "is_cold_coffee": is_cold_coffee,
        "is_ice_cream": is_ice_cream,
        "is_sushi": is_sushi,
        "is_sushi_set": is_sushi_set,
        "sushi_tags": sushi_tags,
        "has_fast_food_size": has_fast_food_size,
        "has_sauce_variant": has_sauce_variant,
        "has_ice_cream_scoop": has_ice_cream_scoop,
        "ff_small_price": ff_small_price,
        "ff_large_price": ff_large_price,
        "ff_size_str": ff_size_str,
        "has_size": has_size,
        "price_large": price_large,
        "sauce_type": sauce_type,
        "is_spicy": is_spicy,
        "tags_arr": tags_arr,
        "tags_json": json.dumps(tags_arr, ensure_ascii=False),
        "popularity": popularity,
        "is_default": is_default,
        "img_src": img_src,
        "price": price,
        "price_per_kg": price if tbl == "cake_items" else None,
        "min_weight": float(item.get("min_weight") or 1) if tbl == "cake_items" else None,
        "variant_options_raw": variant_options_raw,
        "is_cold": bool(item.get("is_cold")) if tbl == "coffee_items" else None,
    }
