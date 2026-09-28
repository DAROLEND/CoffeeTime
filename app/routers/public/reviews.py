"""Paginated/sorted/filtered site reviews, plus review submission for
logged-in customers. Reviews an admin declined are not shown."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import bad_request
from app.db.session import get_db
from app.dependencies import require_user
from app.models.cms import ReviewStatus, SiteReview
from app.schemas.common import OkResponse
from app.schemas.reviews import ReviewCreate, ReviewsPage
from app.services.home import review_avatar_color

router = APIRouter(prefix="/reviews", tags=["reviews"])

SORT_OPTIONS = {"newest", "oldest", "best", "worst"}
ORDER_MAP = {
    "newest": (SiteReview.created_at.desc(),),
    "oldest": (SiteReview.created_at.asc(),),
    "best": (SiteReview.rating.desc(), SiteReview.created_at.desc()),
    "worst": (SiteReview.rating.asc(), SiteReview.created_at.desc()),
}
PER_PAGE = 6
VISIBLE = SiteReview.status != ReviewStatus.DECLINED


@router.get("", response_model=ReviewsPage)
def reviews_page(request: Request, sort: str = "newest", filter: int = 0, page: int = 1, db: Session = Depends(get_db)):
    sort = sort if sort in SORT_OPTIONS else "newest"
    filter = max(0, min(5, filter))

    stats = db.execute(select(func.avg(SiteReview.rating), func.count()).select_from(SiteReview).where(VISIBLE)).first()
    avg_rating = round(float(stats[0] or 0), 1)
    total_count = int(stats[1] or 0)

    counts = dict(db.execute(select(SiteReview.rating, func.count()).where(VISIBLE).group_by(SiteReview.rating)).all())
    distribution = [
        {"stars": i, "count": int(counts.get(i, 0)), "pct": round(counts.get(i, 0) / total_count * 100) if total_count else 0}
        for i in range(5, 0, -1)
    ]

    clauses = [VISIBLE] + ([SiteReview.rating == filter] if filter > 0 else [])
    filtered_total = db.execute(select(func.count()).select_from(SiteReview).where(*clauses)).scalar_one()
    total_pages = max(1, -(-filtered_total // PER_PAGE))
    page = min(max(1, page), total_pages)

    rows = db.execute(
        select(SiteReview.name, SiteReview.text, SiteReview.rating, SiteReview.created_at)
        .where(*clauses).order_by(*ORDER_MAP[sort]).limit(PER_PAGE).offset((page - 1) * PER_PAGE)
    ).all()

    return {
        "sort": sort, "filter": filter, "page": page, "total_pages": total_pages,
        "total_count": total_count, "filtered_count": filtered_total, "avg_rating": avg_rating,
        "distribution": distribution,
        "reviews": [
            {"name": r.name, "initial": (r.name[:1] or "?").upper(), "avatar_color": review_avatar_color(r.name),
             "text": r.text, "rating": int(r.rating or 0),
             "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else ""}
            for r in rows
        ],
        "reviewed_already": bool(request.state.session.get("reviewed")),
    }


@router.post("", response_model=OkResponse, status_code=201)
def submit_review(body: ReviewCreate, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    name, text = body.name.strip(), body.text.strip()
    errors = []
    if not 1 <= body.rating <= 5:
        errors.append("Оберіть оцінку")
    if len(name) < 2:
        errors.append("Ім'я занадто коротке")
    if len(text) < 10:
        errors.append("Відгук занадто короткий")
    if errors:
        raise bad_request(errors[0], code="validation", errors=errors)
    db.add(SiteReview(name=name, text=text, rating=body.rating))
    db.commit()
    request.state.session["reviewed"] = True
    return {"ok": True}
