"""Applies 3 schema fixes, plus adds the new app_sessions table needed by
the session middleware (pure new infrastructure, additive only).

1. orders.user_id: ON DELETE CASCADE -> SET NULL. No admin feature
   deletes user accounts today, so this changes no currently-reachable
   behavior; it only stops a future user-deletion feature from silently
   wiping the deleted user's entire order/financial history.

2. sushi_sets: consolidate the two overlapping "piece count" columns.
   `pieces` and `pieces_count` had silently drifted apart (an admin edit
   to piece count never showed up on the public menu). Backfill
   `pieces_count` from `pieces` wherever `pieces_count` is still 0 (i.e.
   never edited since seeding), then drop the unused `pieces` column.

3. users.email: varchar(30) -> varchar(255), too short for real-world
   addresses; widening is backward-compatible with every existing row.

Revision ID: 0002_port_fixes
Revises: 0001_baseline
Create Date: 2026-09-05

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_port_fixes"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. orders.user_id FK: CASCADE -> SET NULL ---
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_user", type_="foreignkey")
        batch.alter_column("user_id", existing_type=sa.Integer, nullable=True)
        batch.create_foreign_key(
            "fk_orders_user", "users", ["user_id"], ["client_id"], ondelete="SET NULL"
        )

    # --- 2. sushi_sets: backfill then drop the legacy `pieces` column ---
    op.execute(
        "UPDATE sushi_sets SET pieces_count = pieces "
        "WHERE pieces_count = 0 AND pieces > 0"
    )
    with op.batch_alter_table("sushi_sets") as batch:
        batch.drop_column("pieces")

    # --- 3. users.email: widen ---
    with op.batch_alter_table("users") as batch:
        batch.alter_column("email", existing_type=sa.String(30), type_=sa.String(255), existing_nullable=False)

    # --- New: server-side session store for the session middleware ---
    # `data` has no server_default: app/middleware/session.py always sets
    # `.data` explicitly before the first commit of a new row, matching
    # the ORM model's Python-level `default="{}"` in
    # app/models/session_store.py.
    op.create_table(
        "app_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("data", sa.Text, nullable=False),
        sa.Column("last_activity", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_sessions")

    with op.batch_alter_table("users") as batch:
        batch.alter_column("email", existing_type=sa.String(255), type_=sa.String(30), existing_nullable=False)

    with op.batch_alter_table("sushi_sets") as batch:
        batch.add_column(sa.Column("pieces", sa.SmallInteger, nullable=False, server_default="0"))
    op.execute("UPDATE sushi_sets SET pieces = pieces_count")

    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_user", type_="foreignkey")
        batch.create_foreign_key(
            "fk_orders_user", "users", ["user_id"], ["client_id"], ondelete="CASCADE"
        )
