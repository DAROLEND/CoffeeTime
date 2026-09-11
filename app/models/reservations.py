"""`reservations` table — present in CoffeeTime.sql with a real FK to
`users`, but Phase 0 grep found no PHP file (page, form, or admin
endpoint) that reads or writes it. Modeled here so the schema round-trips
byte-for-byte and the table isn't silently dropped, but deliberately has
no corresponding router/service — there is no current feature to port.
Revisit if a reservation feature is added later.
"""
from __future__ import annotations

import datetime
import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReservationLocation(str, enum.Enum):
    INDOOR = "indoor"
    TERRACE = "terrace"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Kept as CASCADE (unlike orders.user_id) — no evidence this table is
    # live, so there is no confirmed "financial history" reason to change
    # it; flip to SET NULL too if/when a real reservation feature lands.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.client_id", ondelete="CASCADE"))
    table_number: Mapped[int] = mapped_column(Integer)
    location: Mapped[ReservationLocation] = mapped_column(
        SAEnum(ReservationLocation, name="reservation_location", values_callable=lambda e: [m.value for m in e])
    )
    reservation_datetime: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    client_phone: Mapped[str] = mapped_column(String(20))
    client_name: Mapped[str] = mapped_column(String(100))
