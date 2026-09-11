"""Hero slider, gallery, site reviews, and the generic key/value settings
store used for the About section and dessert-of-the-day banner."""
from __future__ import annotations

import datetime
import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GalleryCategory(str, enum.Enum):
    FOOD = "food"
    INTERIOR = "interior"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class HeroSlide(Base):
    __tablename__ = "hero_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image: Mapped[str] = mapped_column(String(255))
    label: Mapped[str] = mapped_column(String(100), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    subtitle: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    active: Mapped[bool | None] = mapped_column(Boolean, default=True)


class Gallery(Base):
    __tablename__ = "gallery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    alt: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[GalleryCategory] = mapped_column(
        SAEnum(GalleryCategory, name="gallery_category", values_callable=lambda e: [m.value for m in e]), default=GalleryCategory.FOOD
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class SiteReview(Base):
    """User-submitted site reviews (pages/reviews.php + admin/admin_reviews.php).

    Distinct from db/fetch_google_reviews.php's Google-Places JSON cache,
    which was confirmed unused/dead during Phase 0 and is not ported.
    """

    __tablename__ = "site_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    rating: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, name="review_status", values_callable=lambda e: [m.value for m in e]), default=ReviewStatus.APPROVED
    )


class SiteSetting(Base):
    """Generic EAV-style settings store — `about_*` and `dessert_banner_*` keys."""

    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
