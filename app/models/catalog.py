"""
The 11 menu-category tables + `sauces`.

Each PHP category table was hand-rolled independently (`id, name,
description, image, price, popularity` plus category-specific extras) —
NOT a shared `products` table with a `category` discriminator. We keep
that exact physical layout here (rather than "normalizing" it) because
`order_items.product_id` has no FK and is resolved purely by matching
`order_items.category` to one of these table names at read time
(see app/constants/categories.py) — collapsing them into one table would
be a real schema/behavior change, not a port.

Column types/defaults are transliterated 1:1 from CoffeeTime.sql's
`SHOW CREATE TABLE` output (read directly, not guessed).
"""
from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DEFAULT_IMAGE = "static/images/menu_items/default.jpg"


class SauceType(str, enum.Enum):
    TOMATO = "tomato"
    CREAM = "cream"
    BBQ = "bbq"


class CoffeeItem(Base):
    __tablename__ = "coffee_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_cold: Mapped[bool] = mapped_column(Boolean, default=False)
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class ColdDrinkItem(Base):
    __tablename__ = "cold_drink_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class DessertItem(Base):
    __tablename__ = "dessert_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class FastFoodItem(Base):
    __tablename__ = "fast_food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    # JSON text blob: size/filling option tree (e.g. hot-dog filling choices,
    # ice-cream-cone-in-fast-food scoop options seen in real order_items data)
    variant_options: Mapped[str | None] = mapped_column(Text, default=None)


class PizzaItem(Base):
    __tablename__ = "pizza_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    price_large: Mapped[float | None] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    # One Python enum, but two distinct Postgres types — pizza_items and
    # mini_pizza_items each got their own in 0001_baseline (MySQL had no
    # shared type to reuse), so the names must be spelled out per column.
    sauce_type: Mapped[SauceType] = mapped_column(SAEnum(SauceType, name="sauce_type_pizza", values_callable=lambda e: [m.value for m in e]), default=SauceType.TOMATO)
    is_spicy: Mapped[bool] = mapped_column(Boolean, default=False)
    has_size_choice: Mapped[bool] = mapped_column(Boolean, default=True)
    ingredients_tags: Mapped[str | None] = mapped_column(String(500), default=None)


class MiniPizzaItem(Base):
    __tablename__ = "mini_pizza_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255), default=DEFAULT_IMAGE)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    sauce_type: Mapped[SauceType] = mapped_column(SAEnum(SauceType, name="sauce_type_mini_pizza", values_callable=lambda e: [m.value for m in e]), default=SauceType.TOMATO)
    is_spicy: Mapped[bool] = mapped_column(Boolean, default=False)
    ingredients_tags: Mapped[str | None] = mapped_column(String(500), default=None)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    # NOTE: no price_large — mini pizzas have one size only (confirmed: no
    # $sizedCats branch in add_to_cart.php reads a `price_large` column for
    # this table, only plain `price`).


class IceCreamItem(Base):
    __tablename__ = "ice_cream_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255), default=DEFAULT_IMAGE)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    variant_options: Mapped[str | None] = mapped_column(Text, default=None)  # scoop-count JSON
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class CakeItem(Base):
    __tablename__ = "cake_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255), default=DEFAULT_IMAGE)
    price_per_kg: Mapped[float] = mapped_column(Numeric(10, 2), default=1000)
    min_weight: Mapped[float] = mapped_column(Numeric(4, 1), default=1.0)
    is_custom_order: Mapped[bool] = mapped_column(Boolean, default=True)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=1000)


class SushiItem(Base):
    __tablename__ = "sushi_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    subcategory: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str | None] = mapped_column(Text, default=None)
    weight: Mapped[str] = mapped_column(String(20), default="")
    image: Mapped[str] = mapped_column(String(255), default=DEFAULT_IMAGE)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class SushiSet(Base):
    __tablename__ = "sushi_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    weight: Mapped[str] = mapped_column(String(20), default="")
    image: Mapped[str] = mapped_column(String(255), default=DEFAULT_IMAGE)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    # Consolidated from the two overlapping PHP columns `pieces`
    # (tinyint, populated only by the one-off db/migrate_menu.php seed
    # script and read by pages/menu.php) vs `pieces_count` (smallint,
    # the one admin/edit_item.php actually writes and pages/checkout.php
    # reads for prep-time estimation) — confirmed via grep that these had
    # silently drifted apart (an admin edit to piece count never showed up
    # on the public menu). Kept the actively-maintained one; see
    # alembic/versions for the one-time data backfill
    # (`pieces_count = pieces` wherever `pieces_count` was still 0).
    pieces_count: Mapped[int] = mapped_column(Integer, default=0)


class SaladItem(Base):
    __tablename__ = "salad_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image: Mapped[str] = mapped_column(String(255), default=DEFAULT_IMAGE)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class Sauce(Base):
    __tablename__ = "sauces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), default=0)
    emoji: Mapped[str | None] = mapped_column(String(10), default="?")
    active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(String(255), default="")
