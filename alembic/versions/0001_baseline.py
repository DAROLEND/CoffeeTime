"""Baseline: reflects the CURRENT production PHP schema exactly (CoffeeTime.sql,
read via SHOW CREATE TABLE — not guessed), including the two known-inconsistent
bits (orders.user_id ON DELETE CASCADE, sushi_sets.pieces + pieces_count both
present, users.email varchar(30)) that get fixed in the next migration.

Purpose: an EXISTING production database should be `alembic stamp 0001_baseline`
(not upgraded — its data already matches this shape) before running `alembic
upgrade head` to apply 0002's fixes. A fresh dev/test database instead runs
`alembic upgrade head` from empty, passing through this exact starting shape.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-05

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_IMAGE = "static/images/menu_items/default.jpg"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("client_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("login", sa.String(60), nullable=False),
        sa.Column("email", sa.String(30), nullable=False),
        sa.Column("password", sa.String(60), nullable=False),
        sa.Column("client_name", sa.String(255)),
        sa.Column("client_surname", sa.String(255)),
        sa.Column("client_PhoneNumber", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("super", "staff", name="admin_role"), nullable=False, server_default="staff"),
        sa.Column("permissions", sa.Text, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False, server_default=""),
    )

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column("attempted_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Index("idx_ip_time", "ip", "attempted_at"),
    )

    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # --- 11 product-category tables + sauces ---
    op.create_table(
        "coffee_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("is_cold", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "cold_drink_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "dessert_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "fast_food_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("variant_options", sa.Text),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "pizza_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("price_large", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sauce_type", sa.Enum("tomato", "cream", "bbq", name="sauce_type_pizza"), nullable=False, server_default="tomato"),
        sa.Column("is_spicy", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("has_size_choice", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("ingredients_tags", sa.String(500)),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "mini_pizza_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False, server_default=DEFAULT_IMAGE),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("sauce_type", sa.Enum("tomato", "cream", "bbq", name="sauce_type_mini_pizza"), nullable=False, server_default="tomato"),
        sa.Column("is_spicy", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("ingredients_tags", sa.String(500)),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "ice_cream_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False, server_default=DEFAULT_IMAGE),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("variant_options", sa.Text),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Index("idx_popularity", "popularity"),
    )
    op.create_table(
        "cake_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False, server_default=DEFAULT_IMAGE),
        sa.Column("price_per_kg", sa.Numeric(10, 2), nullable=False, server_default="1000.00"),
        sa.Column("min_weight", sa.Numeric(4, 1), nullable=False, server_default="1.0"),
        sa.Column("is_custom_order", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="1000.00"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "sushi_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subcategory", sa.String(80), nullable=False, server_default=""),
        sa.Column("description", sa.Text),
        sa.Column("weight", sa.String(20), nullable=False, server_default=""),
        sa.Column("image", sa.String(255), nullable=False, server_default=DEFAULT_IMAGE),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "sushi_sets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("weight", sa.String(20), nullable=False, server_default=""),
        sa.Column("image", sa.String(255), nullable=False, server_default=DEFAULT_IMAGE),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("pieces", sa.SmallInteger, nullable=False, server_default="0"),  # legacy, dropped in 0002
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pieces_count", sa.Integer, nullable=False, server_default="0"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "salad_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("image", sa.String(255), nullable=False, server_default=DEFAULT_IMAGE),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("popularity", sa.Integer, nullable=False, server_default="0"),
        sa.Index("popularity", "popularity"),
    )
    op.create_table(
        "sauces",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("emoji", sa.String(10), server_default="?"),
        sa.Column("active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("image", sa.String(255), nullable=False, server_default=""),
    )

    # --- Commerce ---
    op.create_table(
        "orders",
        sa.Column("order_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.client_id", ondelete="CASCADE", name="fk_orders_user")),  # fixed to SET NULL in 0002
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("delivery_address", sa.String(255), server_default=""),
        sa.Column("phone", sa.String(20)),
        sa.Column("status", sa.Enum("new", "processing", "ready", "done", "cancelled", name="order_status"), nullable=False, server_default="new"),
        sa.Column("customer_name", sa.String(100)),
        sa.Column("customer_surname", sa.String(100)),
        sa.Column("customer_email", sa.String(180)),
        sa.Column("comment", sa.Text),
        sa.Column("ready_time", sa.String(20)),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("payment_status", sa.Enum("pending", "paid", "failed", "cash", name="payment_status"), server_default="pending"),
        sa.Column("paid_at", sa.DateTime),
        sa.Column("liqpay_order_id", sa.String(100)),
        sa.Column("order_type", sa.Enum("dine_in", "takeaway", name="order_type"), nullable=False, server_default="dine_in"),
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.order_id", ondelete="CASCADE", name="fk_order_items_order"), nullable=False),
        sa.Column("product_id", sa.Integer, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("selected_size", sa.String(20), server_default="small"),
        sa.Column("selected_variant", sa.Text),
        sa.Column("cheese_crust", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("takeaway", sa.Boolean, nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "order_ratings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("rating", sa.SmallInteger, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("order_id", "user_id", name="uq_order_user"),
    )
    op.create_table(
        "order_reminders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.order_id", ondelete="CASCADE", name="fk_reminders_order"), nullable=False),
        sa.Column("type", sa.Enum("email_customer", "telegram_admin", name="reminder_type"), nullable=False),
        sa.Column("send_at", sa.DateTime, nullable=False),
        sa.Column("sent_at", sa.DateTime),
        sa.Column("status", sa.Enum("pending", "sent", "failed", name="reminder_status"), nullable=False, server_default="pending"),
        sa.Column("fail_reason", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Index("idx_pending", "status", "send_at"),
    )
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.client_id", ondelete="CASCADE", name="fk_reservations_user"), nullable=False),
        sa.Column("table_number", sa.Integer, nullable=False),
        sa.Column("location", sa.Enum("indoor", "terrace", name="reservation_location"), nullable=False),
        sa.Column("reservation_datetime", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("client_phone", sa.String(20), nullable=False),
        sa.Column("client_name", sa.String(100), nullable=False),
    )

    # --- CMS ---
    op.create_table(
        "hero_slides",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("label", sa.String(100), nullable=False, server_default=""),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("subtitle", sa.String(255), nullable=False, server_default=""),
        sa.Column("sort_order", sa.SmallInteger, server_default="0"),
        sa.Column("active", sa.Boolean, server_default=sa.text("1")),
    )
    op.create_table(
        "gallery",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("alt", sa.String(255), nullable=False, server_default=""),
        sa.Column("category", sa.Enum("food", "interior", name="gallery_category"), nullable=False, server_default="food"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "site_reviews",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("rating", sa.SmallInteger, server_default="0"),
        sa.Column("status", sa.Enum("pending", "approved", "declined", name="review_status"), nullable=False, server_default="approved"),
    )
    op.create_table(
        "site_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
    )


def downgrade() -> None:
    for table in (
        "site_settings", "site_reviews", "gallery", "hero_slides", "reservations",
        "order_reminders", "order_ratings", "order_items", "orders",
        "sauces", "salad_items", "sushi_sets", "sushi_items", "cake_items",
        "ice_cream_items", "mini_pizza_items", "pizza_items", "fast_food_items",
        "dessert_items", "cold_drink_items", "coffee_items",
        "password_resets", "login_attempts", "admin_users", "users",
    ):
        op.drop_table(table)
