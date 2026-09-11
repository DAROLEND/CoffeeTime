"""Admin reviews management: site reviews and order ratings tabs, with
approve/decline/delete actions."""
from __future__ import annotations

import datetime
import math
import zlib
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.auth import User
from app.models.cms import SiteReview
from app.models.orders import OrderRating
from app.services.permissions import require_perm
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/reviews",
    dependencies=[Depends(get_current_admin), Depends(require_perm("reviews"))],
)

PER_PAGE = 25
AVATAR_COLORS = ["#c0392b", "#e67e22", "#27ae60", "#2980b9", "#8e44ad", "#16a085", "#d35400"]
ALLOWED_STATUSES = {"approved", "declined", "pending"}


def _review_color(name: str) -> str:
    return AVATAR_COLORS[abs(zlib.crc32(name.encode("utf-8"))) % len(AVATAR_COLORS)]


def _pagination_url(query_params, **overrides) -> str:
    merged = dict(query_params)
    merged.update({k: str(v) for k, v in overrides.items()})
    return "?" + urlencode(merged)


@router.get("")
def reviews_page(
    request: Request, db: Session = Depends(get_db),
    tab: str = "", rating: int = 0, status: str = "", p: int = 1,
):
    admin_tab = "order_ratings" if tab == "order_ratings" else "site_reviews"

    if admin_tab == "order_ratings":
        return _order_ratings_tab(request, db, admin_tab, p)
    return _site_reviews_tab(request, db, admin_tab, rating, status, p)


def _site_reviews_tab(request: Request, db: Session, admin_tab: str, filter_rating: int, filter_status: str, page: int):
    clauses = []
    if 1 <= filter_rating <= 5:
        clauses.append(SiteReview.rating == filter_rating)
    if filter_status in ALLOWED_STATUSES:
        clauses.append(SiteReview.status == filter_status)

    total_rows = db.execute(select(func.count()).select_from(SiteReview).where(*clauses)).scalar_one()
    total_pages = max(1, math.ceil(total_rows / PER_PAGE))
    page = min(max(1, page), total_pages)
    offset = (page - 1) * PER_PAGE

    rows = db.execute(
        select(SiteReview).where(*clauses).order_by(SiteReview.created_at.desc()).limit(PER_PAGE).offset(offset)
    ).scalars().all()

    reviews = []
    for r in rows:
        author = r.name or "Анонім"
        status_val = r.status.value if hasattr(r.status, "value") else (r.status or "approved")
        reviews.append({
            "id": r.id, "author": author, "initial": author[:1].upper(), "color": _review_color(author),
            "rating": r.rating or 0, "text": r.text or "", "created_at": r.created_at, "status": status_val,
        })

    rating_dist = {s: 0 for s in range(1, 6)}
    total_count = 0
    for stars, cnt in db.execute(select(SiteReview.rating, func.count()).group_by(SiteReview.rating)).all():
        if stars in rating_dist:
            rating_dist[stars] = cnt
        total_count += cnt
    avg_rating = round(sum(s * c for s, c in rating_dist.items()) / total_count, 1) if total_count else 0.0

    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    this_week = db.execute(select(func.count()).select_from(SiteReview).where(SiteReview.created_at > week_ago)).scalar_one()

    return admin_render(
        request, db, "admin/admin_reviews.html", page_title="Відгуки", active_page="reviews",
        admin_tab=admin_tab, reviews=reviews, total_rows=total_rows, total_pages=total_pages, page=page,
        filter_rating=filter_rating, filter_status=filter_status,
        total_count=total_count, avg_rating=avg_rating, rating_dist=rating_dist, this_week=this_week,
        pagination_url=lambda **kw: _pagination_url(request.query_params, **kw),
        deleted="deleted" in request.query_params,
    )


def _order_ratings_tab(request: Request, db: Session, admin_tab: str, page: int):
    or_total = db.execute(select(func.count()).select_from(OrderRating)).scalar_one()
    or_pages = max(1, math.ceil(or_total / PER_PAGE))
    page = min(max(1, page), or_pages)
    offset = (page - 1) * PER_PAGE

    or_avg = 0.0
    if or_total > 0:
        weighted = 0
        for stars, cnt in db.execute(select(OrderRating.rating, func.count()).group_by(OrderRating.rating)).all():
            weighted += stars * cnt
        or_avg = round(weighted / or_total, 1)

    rows = db.execute(
        select(OrderRating, User)
        .outerjoin(User, User.client_id == OrderRating.user_id)
        .order_by(OrderRating.created_at.desc()).limit(PER_PAGE).offset(offset)
    ).all()

    order_ratings = []
    for rating_row, user in rows:
        uname = f"{user.client_name or ''} {user.client_surname or ''}".strip() if user else ""
        email = user.email if user else ""
        order_ratings.append({
            "order_id": rating_row.order_id, "uname": uname or (email or "Клієнт"),
            "email": email, "rating": rating_row.rating, "created_at": rating_row.created_at,
        })

    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    or_week = db.execute(select(func.count()).select_from(OrderRating).where(OrderRating.created_at > week_ago)).scalar_one()

    return admin_render(
        request, db, "admin/admin_reviews.html", page_title="Відгуки", active_page="reviews",
        admin_tab=admin_tab, order_ratings=order_ratings, or_total=or_total, or_avg=or_avg, or_week=or_week,
        or_page=page, or_pages=or_pages,
    )


@router.post("")
async def reviews_action(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    action = (form.get("action") or "").strip()
    review_id = int(form.get("id") or 0)

    if not review_id or action not in ("approved", "declined", "delete"):
        return JSONResponse({"success": False})

    if action == "delete":
        row = db.get(SiteReview, review_id)
        if row:
            db.delete(row)
            db.commit()
        return JSONResponse({"success": True})

    row = db.get(SiteReview, review_id)
    if row:
        row.status = action
        db.commit()
    return JSONResponse({"success": True})
