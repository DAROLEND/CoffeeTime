"""Paginated/sorted/filtered site reviews, plus the authenticated
review-submission form."""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.cms import SiteReview
from app.services.csrf import CSRFError, verify_csrf
from app.services.home import review_avatar_color
from app.templating import render, templates

router = APIRouter()

SORT_OPTIONS = {"newest", "oldest", "best", "worst"}
ORDER_MAP = {
    "newest": (SiteReview.created_at.desc(),),
    "oldest": (SiteReview.created_at.asc(),),
    "best": (SiteReview.rating.desc(), SiteReview.created_at.desc()),
    "worst": (SiteReview.rating.asc(), SiteReview.created_at.desc()),
}
PER_PAGE = 6


def _build_url(sort: str, filter_: int, page: int, overrides: dict) -> str:
    params = {"sort": sort, "filter": filter_, "p": page}
    params.update(overrides)
    if int(params["filter"]) == 0:
        params.pop("filter", None)
    if params["sort"] == "newest":
        params.pop("sort", None)
    if int(params.get("p", 1)) <= 1:
        params.pop("p", None)
    return "/reviews" + (f"?{urlencode(params)}" if params else "")


@router.get("/reviews")
def reviews_page(
    request: Request,
    sort: str = "newest",
    filter: int = 0,
    p: int = 1,
    ajax: int | None = None,
    success: int | None = None,
    db: Session = Depends(get_db),
):
    sort = sort if sort in SORT_OPTIONS else "newest"
    filter = max(0, min(5, filter))
    page_num = max(1, p)

    stats = db.execute(
        select(func.round(func.avg(SiteReview.rating), 1), func.count()).select_from(SiteReview)
    ).first()
    avg_rating = float(stats[0] or 0)
    total_count = int(stats[1] or 0)

    distribution = {}
    for i in range(5, 0, -1):
        distribution[i] = db.execute(
            select(func.count()).select_from(SiteReview).where(SiteReview.rating == i)
        ).scalar_one()

    if filter > 0:
        filtered_total = db.execute(
            select(func.count()).select_from(SiteReview).where(SiteReview.rating == filter)
        ).scalar_one()
    else:
        filtered_total = total_count

    total_pages = max(1, -(-filtered_total // PER_PAGE))  # ceil division
    page_num = min(page_num, total_pages)
    offset = (page_num - 1) * PER_PAGE

    query = select(SiteReview.name, SiteReview.text, SiteReview.rating, SiteReview.created_at)
    if filter > 0:
        query = query.where(SiteReview.rating == filter)
    query = query.order_by(*ORDER_MAP[sort]).limit(PER_PAGE).offset(offset)
    review_rows = db.execute(query).all()

    grid_context = {
        "request": request,
        "reviews": review_rows,
        "page_num": page_num,
        "total_pages": total_pages,
        "build_url": lambda overrides: _build_url(sort, filter, page_num, overrides),
        "review_avatar_color": review_avatar_color,
    }

    if ajax:
        html = templates.get_template("public/_reviews_grid.html").render(grid_context)
        return JSONResponse({"ok": True, "html": html, "count": filtered_total})

    reviewed_already = bool(request.state.session.get("reviewed"))

    return render(
        request,
        "public/reviews.html",
        page="reviews",
        page_title="Відгуки — Coffee Time",
        sort=sort,
        filter=filter,
        total_count=total_count,
        avg_rating=avg_rating,
        distribution=distribution,
        show_success=success is not None,
        reviewed_already=reviewed_already,
        **{k: v for k, v in grid_context.items() if k != "request"},
    )


@router.post("/reviews")
async def submit_review(
    request: Request,
    name: str = Form(""),
    text: str = Form(""),
    rating: int = Form(0),
    sort: str = "newest",
    db: Session = Depends(get_db),
):
    try:
        await verify_csrf(request)
    except CSRFError as exc:
        request.state.session["flash_error"] = exc.message
        return RedirectResponse("/reviews", status_code=303)

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/reviews", status_code=303)

    name, text = name.strip(), text.strip()
    if len(name) >= 2 and len(text) >= 10 and 1 <= rating <= 5:
        db.add(SiteReview(name=name, text=text, rating=rating))
        db.commit()
        request.state.session["reviewed"] = True
        return RedirectResponse(f"/reviews?success=1&sort={sort}", status_code=303)

    return RedirectResponse("/reviews", status_code=303)
