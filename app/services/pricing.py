"""
Server-side price computation for cart lines and order items.

The client never supplies a price. It sends *parameters* (pizza size,
cheese crust, cake weight, the id of a chosen variant option) and every
price is derived here from the current DB row:

- cake_items: weight (clamped up to the cake's min_weight) x price_per_kg
- pizza_items: price or price_large (+ fixed cheese-crust surcharge)
- mini_pizza_items: price (one size, never a crust surcharge)
- ice_cream_items / fast_food_items: price + the surcharge of the chosen
  option, looked up by id in the product's own `variant_options`
- everything else: price

`variant_options` is stored as free-form JSON text. `parse_variant_options`
normalizes the four shapes found in real data into one structure, and is
used both here (to validate a selection) and by the menu API (so the
client renders exactly the options the server will accept).
"""
from __future__ import annotations

import json
from typing import Any

from app.constants.categories import CHEESE_CRUST_SURCHARGE

VARIANT_CATEGORIES = {"fast_food_items", "ice_cream_items"}
VARIANT_TYPES = {"size", "filling", "sauce", "scoops"}


class InvalidVariant(ValueError):
    """The submitted selection doesn't match any option the product offers."""


def _num(raw: Any) -> float:
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def parse_variant_options(raw: str | None) -> dict | None:
    """Normalize a `variant_options` JSON blob to
    `{type, label, options: [{id, label, price_diff, sizes: [{label, price_diff}]}]}`,
    or None when the blob is empty or not one of the known shapes.

    `sauce` options are stored as bare strings (a free choice, no
    surcharge); they are given the string itself as both id and label.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("type") not in VARIANT_TYPES:
        return None
    options_raw = data.get("options")
    if not isinstance(options_raw, list) or not options_raw:
        return None

    options = []
    for i, opt in enumerate(options_raw):
        if isinstance(opt, str):
            options.append({"id": opt, "label": opt, "price_diff": 0.0, "sizes": []})
            continue
        if not isinstance(opt, dict):
            continue
        sizes = []
        for sz in opt.get("sizes") or []:
            if isinstance(sz, dict) and sz.get("label"):
                sizes.append({"label": str(sz["label"]), "price_diff": _num(sz.get("price_diff"))})
        label = str(opt.get("label") or "")
        options.append({
            "id": str(opt.get("id") if opt.get("id") is not None else i + 1),
            "label": label,
            "price_diff": _num(opt.get("price_diff")),
            "sizes": sizes,
        })
    if not options:
        return None
    return {"type": data["type"], "label": str(data.get("label") or ""), "options": options}


def _find_option(options: list[dict], option_id: Any) -> dict | None:
    if option_id is None:
        return None
    for opt in options:
        if opt["id"] == str(option_id):
            return opt
    return None


def resolve_variant(variant_options_raw: str | None, submitted: str | None) -> tuple[str | None, float]:
    """Validate a submitted `selected_variant` against the product's own
    options. Returns `(canonical_variant_json, price_diff)`.

    Only the option *identity* is taken from the client (`scoop_id`,
    `filling_id`, `size_label`, or the sauce label); labels and surcharges
    are copied from the DB. A missing selection on a product that has a
    priced choice defaults to the first option, like the menu UI. Raises
    InvalidVariant for a selection the product doesn't offer.
    """
    vo = parse_variant_options(variant_options_raw)
    submitted = (submitted or "").strip()
    if vo is None:
        # Nothing selectable on this product: whatever the client sent is ignored.
        return None, 0.0

    chosen: Any = None
    if submitted:
        try:
            chosen = json.loads(submitted)
        except ValueError:
            chosen = submitted  # a bare sauce label
    options = vo["options"]

    if vo["type"] == "sauce":
        if not submitted:
            return None, 0.0
        label = chosen.get("label") if isinstance(chosen, dict) else chosen
        opt = _find_option(options, label)
        if opt is None:
            raise InvalidVariant(submitted)
        return json.dumps({"type": "sauce", "label": opt["label"]}, ensure_ascii=False), 0.0

    if vo["type"] == "scoops" or vo["type"] == "size":
        option_id = chosen.get("scoop_id") if isinstance(chosen, dict) else None
        if submitted and option_id is None:
            raise InvalidVariant(submitted)
        opt = _find_option(options, option_id) if option_id is not None else options[0]
        if opt is None:
            raise InvalidVariant(submitted)
        canonical = {"type": vo["type"], "scoop_id": opt["id"], "scoop_label": opt["label"], "price_diff": opt["price_diff"]}
        return json.dumps(canonical, ensure_ascii=False), opt["price_diff"]

    # filling, optionally with a nested size
    option_id = chosen.get("filling_id") if isinstance(chosen, dict) else None
    if submitted and option_id is None:
        raise InvalidVariant(submitted)
    opt = _find_option(options, option_id) if option_id is not None else options[0]
    if opt is None:
        raise InvalidVariant(submitted)
    canonical = {"type": "filling", "filling_id": opt["id"], "filling_label": opt["label"]}
    diff = opt["price_diff"]
    if opt["sizes"]:
        size_label = chosen.get("size_label") if isinstance(chosen, dict) else None
        size = next((s for s in opt["sizes"] if s["label"] == size_label), None) if size_label else opt["sizes"][0]
        if size is None:
            raise InvalidVariant(submitted)
        canonical["size_label"] = size["label"]
        canonical["size_diff"] = size["price_diff"]
        diff += size["price_diff"]
    canonical["price_diff"] = diff
    return json.dumps(canonical, ensure_ascii=False), diff


def clamp_cake_weight(row, weight: Any) -> float:
    w = _num(weight) or 1.0
    return max(float(row.min_weight or 1), w, 0.5)


def pizza_size(row, requested: str | None) -> str:
    """Large only exists for a pizza with a size choice and a large price."""
    if requested == "large" and getattr(row, "has_size_choice", False) and float(getattr(row, "price_large", 0) or 0) > 0:
        return "large"
    return "small"


def unit_price(category: str, row, line: dict) -> float:
    """The current price of one unit of this cart line, from the DB row
    plus the line's own parameters."""
    if category == "cake_items":
        return round(clamp_cake_weight(row, line.get("weight")) * float(row.price_per_kg or 0), 2)

    if category == "pizza_items":
        size = pizza_size(row, line.get("selected_size"))
        price = float(row.price_large) if size == "large" else float(row.price)
        if int(line.get("cheese_crust") or 0):
            price += CHEESE_CRUST_SURCHARGE[size]
        return round(price, 2)

    base = float(row.price or 0)
    if category in VARIANT_CATEGORIES and line.get("selected_variant"):
        try:
            _, diff = resolve_variant(row.variant_options, line["selected_variant"])
        except InvalidVariant:
            diff = 0.0
        base += diff
    return round(base, 2)
