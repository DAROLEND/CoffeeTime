"""Orders, order line items, ratings, and reminder scheduling."""
from __future__ import annotations

import datetime
import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    NEW = "new"
    PROCESSING = "processing"
    READY = "ready"
    DONE = "done"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CASH = "cash"


class OrderType(str, enum.Enum):
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"


class ReminderType(str, enum.Enum):
    EMAIL_CUSTOMER = "email_customer"
    TELEGRAM_ADMIN = "telegram_admin"


class ReminderStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


def _enum(python_enum: type[enum.Enum], name: str):
    """`name` must match the type name the Alembic migration created.

    Postgres enums are real named types, so the name is part of the
    schema — bind a column to a type name that doesn't exist and
    psycopg2 fails with `type "..." does not exist`. Left implicit,
    SQLAlchemy derives it from the Python class name (ReminderType ->
    "remindertype"), which won't match what the migration created."""
    return SAEnum(python_enum, name=name, values_callable=lambda e: [m.value for m in e])


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # SET NULL rather than CASCADE: deleting a user should not delete their
    # order history. No current admin feature deletes users, so this only
    # guards against a future one becoming a silent data-loss trap.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.client_id", ondelete="SET NULL"), nullable=True
    )
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    delivery_address: Mapped[str | None] = mapped_column(String(255), default="")
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"), default=OrderStatus.NEW)
    customer_name: Mapped[str | None] = mapped_column(String(100), default=None)
    customer_surname: Mapped[str | None] = mapped_column(String(100), default=None)
    customer_email: Mapped[str | None] = mapped_column(String(180), default=None)
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    # Free-form string, sometimes bare "HH:MM", sometimes full
    # "YYYY-MM-DD HH:MM" — not a real DATETIME column, since
    # services/schedule.py parses this exact free-form shape and admin
    # pages format it for display without a strict type.
    ready_time: Mapped[str | None] = mapped_column(String(20), default=None)
    payment_method: Mapped[str | None] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    payment_status: Mapped[PaymentStatus | None] = mapped_column(_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING)
    paid_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, default=None)
    liqpay_order_id: Mapped[str | None] = mapped_column(String(100), default=None)
    order_type: Mapped[OrderType] = mapped_column(_enum(OrderType, "order_type"), default=OrderType.DINE_IN)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    # No FK — deliberately polymorphic, resolved via `category` against one
    # of the 11 product tables (see app/constants/categories.py).
    product_id: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)  # price snapshot at order time
    category: Mapped[str] = mapped_column(String(50))
    selected_size: Mapped[str | None] = mapped_column(String(20), default="small")
    selected_variant: Mapped[str | None] = mapped_column(Text, default=None)  # JSON text, decoded ad hoc
    cheese_crust: Mapped[bool] = mapped_column(Boolean, default=False)
    takeaway: Mapped[bool] = mapped_column(Boolean, default=False)


class OrderRating(Base):
    __tablename__ = "order_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = ()  # UNIQUE(order_id, user_id) added via Alembic (`uq_order_user`)


class OrderReminder(Base):
    __tablename__ = "order_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    type: Mapped[ReminderType] = mapped_column(_enum(ReminderType, "reminder_type"))
    send_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, default=None)
    status: Mapped[ReminderStatus] = mapped_column(_enum(ReminderStatus, "reminder_status"), default=ReminderStatus.PENDING)
    fail_reason: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
