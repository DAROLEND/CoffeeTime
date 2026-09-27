from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class VariantSize(BaseModel):
    label: str
    price_diff: float


class VariantOption(BaseModel):
    id: str
    label: str
    price_diff: float
    sizes: list[VariantSize] = []


class VariantOptions(BaseModel):
    """Normalized `variant_options` (see app/services/pricing.py)."""
    type: Literal["size", "filling", "sauce", "scoops"]
    label: str
    options: list[VariantOption]


class MenuCard(BaseModel):
    id: int
    category: str
    label: str
    name: str
    description: str
    order: int
    image: str
    price: float
    popularity: int
    is_pizza: bool
    is_mini_pizza: bool
    is_pizza_type: bool
    is_fast_food: bool
    is_cold_coffee: bool
    is_ice_cream: bool
    is_sushi: bool
    is_sushi_set: bool
    sushi_tags: list[str]
    has_fast_food_size: bool
    has_sauce_variant: bool
    has_ice_cream_scoop: bool
    ff_small_price: float
    ff_large_price: float
    ff_size_str: str
    has_size: bool
    price_large: float
    sauce_type: str
    is_spicy: bool
    tags: list[str]
    price_per_kg: float | None = None
    min_weight: float | None = None
    variant_options: VariantOptions | None = None


class MenuGroup(BaseModel):
    id: str
    label: str
    icon: str
    categories: list[str]


class MenuTab(BaseModel):
    key: str
    label: str
    count: int


class MenuSauce(BaseModel):
    id: int
    name: str
    price: float
    image: str
    emoji: str


class MenuResponse(BaseModel):
    current: str
    current_group: str
    groups: list[MenuGroup]
    tabs: list[MenuTab]
    sections: dict[str, list[MenuCard]]
    ingredient_tags: list[str]
    sauces: list[MenuSauce]
