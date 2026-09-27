"""Admin reviews: site reviews (filter, approve/decline/delete) and the
per-order ratings customers leave in their profile."""
from __future__ import annotations

import datetime
import math
import zlib

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.auth import User
from app.models.cms import SiteReview
from app.models.orders import OrderRating
from app.schemas.admin import AdminOrderRatingsPage, AdminReviewsPage, ReviewStatusRequest
from app.schemas.common import SuccessResponse
from app.services.enum_utils import enum_value
from app.services.permissions import require_perm

router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin"],
    dependencies=[Depends(get_current_admin), Depends(require_perm("reviews"))],
)

PER_PAGE = 25
AVATAR_COLORS = ["#c0392b", "#e67e22", "#27ae60", "#2980b9", "#8e44ad", "#16a085", "#d35400"]
ALLOWED_STATUSES = {"approved", "declined", "pending"}


def _review_color(name: str) -> str:
    return AVATAR_COLORS[abs(zlib.crc32(name.encode("utf-8"))) % len(AVATAR_COLORS)]


@router.get("", response_model=AdminReviewsPage)
def site_reviews(rating: int = 0, status: str = "", page: int = 1, db: Session = Depends(get_db)):
    clauses = []
    if 1 <= rating <= 5:
        clauses.append(SiteReview.rating == rating)
    if status in ALLOWED_STATUSES:
        clauses.append(SiteReview.status == status)

    total_rows = db.execute(select(func.count()).select_from(SiteReview).where(*clauses)).scalar_one()
    total_pages = max(1, math.ceil(total_rows / PER_PAGE))
    page = min(max(1, page), total_pages)
    rows = db.execute(
        select(SiteReview).where(*clauses).order_by(SiteReview.created_at.desc(), SiteReview.id.desc())
        .limit(PER_PAGE).offset((page - 1) * PER_PAGE)
    ).scalars().all()

    rating_dist = {s: 0 for s in range(1, 6)}
    total_count = 0
    for stars, cnt in db.execute(select(SiteReview.rating, func.count()).group_by(SiteReview.rating)).all():
        if stars in rating_dist:
            rating_dist[stars] = cnt
        total_count += cnt
    avg_rating = round(sum(s * c for s, c in rating_dist.items()) / total_count, 1) if total_count else 0.0
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)

    return {
        "reviews": [
            {
                "id": r.id, "author": r.name or "Анонім", "initial": (r.name or "А")[:1].upper(),
                "color": _review_color(r.name or "Анонім"), "rating": r.rating or 0, "text": r.text or "",
                "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else "",
                "status": enum_value(r.status) or "approved",
            }
            for r in rows
        ],
        "total_rows": total_rows, "page": page, "total_pages": total_pages,
        "filter_rating": rating if 1 <= rating <= 5 else 0,
        "filter_status": status if status in ALLOWED_STATUSES else "",
        "total_count": total_count, "avg_rating": avg_rating,
        "rating_dist": [{"stars": s, "count": rating_dist[s]} for s in range(5, 0, -1)],
        "this_week": db.execute(select(func.count()).select_from(SiteReview).where(SiteReview.created_at > week_ago)).scalar_one(),
    }


@router.get("/order-ratings", response_model=AdminOrderRatingsPage)
def order_ratings(page: int = 1, db: Session = Depends(get_db)):
    total = db.execute(select(func.count()).select_from(OrderRating)).scalar_one()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(1, page), total_pages)
    avg = 0.0
    if total:
        weighted = sum(stars * cnt for stars, cnt in db.execute(select(OrderRating.rating, func.count()).group_by(OrderRating.rating)).all())
        avg = round(weighted / total, 1)

    rows = db.execute(
        select(OrderRating, User).outerjoin(User, User.client_id == OrderRating.user_id)
        .order_by(OrderRating.created_at.desc(), OrderRating.id.desc()).limit(PER_PAGE).offset((page - 1) * PER_PAGE)
    ).all()
    out = []
    for rating_row, user in rows:
        uname = f"{user.client_name or ''} {user.client_surname or ''}".strip() if user else ""
        email = user.email if user else ""
        out.append({
            "order_id": rating_row.order_id, "uname": uname or email or "Клієнт", "email": email or "",
            "rating": rating_row.rating,
            "created_at": rating_row.created_at.isoformat(timespec="seconds") if rating_row.created_at else "",
        })
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    return {
        "order_ratings": out, "total": total, "avg": avg, "page": page, "total_pages": total_pages,
        "week": db.execute(select(func.count()).select_from(OrderRating).where(OrderRating.created_at > week_ago)).scalar_one(),
    }


@router.patch("/{review_id}", response_model=SuccessResponse)
def set_review_status(review_id: int, body: ReviewStatusRequest, db: Session = Depends(get_db)):
    row = db.get(SiteReview, review_id)
    if row is None:
        raise not_found("Відгук не знайдено.")
    row.status = body.status
    db.commit()
    return {"success": True}


@router.delete("/{review_id}", response_model=SuccessResponse)
def delete_review(review_id: int, db: Session = Depends(get_db)):
    row = db.get(SiteReview, review_id)
    if row is not None:
        db.delete(row)
        db.commit()
    return {"success": True}
