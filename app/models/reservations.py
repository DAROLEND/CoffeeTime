"""`reservations` table — modeled here for schema completeness, but has no
corresponding router/service since there is no current reservation
feature. Revisit if one is added later.
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
    # Unlike orders.user_id, this stays CASCADE; revisit if a reservation
    # feature becomes live enough that user deletion should preserve it.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.client_id", ondelete="CASCADE"))
    table_number: Mapped[int] = mapped_column(Integer)
    location: Mapped[ReservationLocation] = mapped_column(
        SAEnum(ReservationLocation, name="reservation_location", values_callable=lambda e: [m.value for m in e])
    )
    reservation_datetime: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    client_phone: Mapped[str] = mapped_column(String(20))
    client_name: Mapped[str] = mapped_column(String(100))
