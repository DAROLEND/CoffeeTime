"""Read-only content pages: the homepage and the gallery. menu.py and
reviews.py carry their own routers."""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.categories import ProductCategory
from app.db.session import get_db
from app.models.catalog import DessertItem
from app.models.cms import Gallery, GalleryCategory, HeroSlide, ReviewStatus, SiteReview
from app.schemas.pages import AboutBlock, GalleryPage, HomePage
from app.services.enum_utils import enum_value
from app.services.home import fetch_popular_items, fetch_top_ordered_items, review_avatar_color
from app.services.media import item_img
from app.services.settings import get_settings_by_prefix

router = APIRouter(tags=["pages"])

_FALLBACK_HERO_SLIDES = [
    {"image": "static/images/categories/coffee_category.webp", "label": "", "text": "Кожен ковток — тепла історія", "sub": "Свіжозварена кава щоранку з любов'ю"},
    {"image": "static/images/categories/dessert.webp", "label": "", "text": "Неможливо встояти…", "sub": "Десерти власного приготування щодня"},
    {"image": "static/images/categories/fast_food.webp", "label": "", "text": "Ідеальне комбо", "sub": "Смачно, ситно і завжди свіже"},
]

ABOUT_DEFAULTS = {
    "about_title": "Місце, де час зупиняється",
    "about_text": "Coffee Time — це затишне кафе в серці міста, де ми щодня готуємо свіжі десерти та каву з любов'ю. Ніяких заморожених напівфабрикатів — тільки справжнє та смачне.",
    "about_founded_year": "2016",
    "about_menu_count": "50",
    "about_rating": "4.8",
    "about_photo": "static/images/main/about-photo.png",
}

_DESSERT_BANNER_DEFAULTS = {
    "label": "Щодня нове",
    "title": "Десерт дня",
    "desc": "Мусові торти, еклери та макарони —\nготуємо кожного ранку зі свіжих інгредієнтів",
    "btn": "Дивитись десерти →",
    "image": "",
}


def years_open(founded_year: str | None) -> int:
    try:
        founded = int(founded_year or 2016)
    except ValueError:
        founded = 2016
    return max(0, datetime.date.today().year - founded)


def about_block(db: Session) -> dict:
    about = {**ABOUT_DEFAULTS, **get_settings_by_prefix(db, "about_")}
    return {
        "title": about["about_title"], "text": about["about_text"],
        "founded_year": about["about_founded_year"], "menu_count": about["about_menu_count"],
        "rating": about["about_rating"], "photo": item_img(about.get("about_photo") or ABOUT_DEFAULTS["about_photo"]),
        "years_open": years_open(about["about_founded_year"]),
    }


def random_dessert_image(db: Session) -> str | None:
    # ORDER BY RANDOM() LIMIT 1 — func.random() maps to Postgres's RANDOM().
    row = db.execute(select(DessertItem.image).order_by(func.random()).limit(1)).first()
    return item_img(row[0]) or None if row else None


def _products(items: list[dict]) -> list[dict]:
    return [
        {"id": it["id"], "table": it["table"], "name": it["name"], "description": it.get("description") or "",
         "image": it.get("image") or "", "price": it["price"]}
        for it in items
    ]


@router.get("/home", response_model=HomePage)
def home(db: Session = Depends(get_db)):
    slides = db.execute(
        select(HeroSlide).where(HeroSlide.active == True).order_by(HeroSlide.sort_order, HeroSlide.id)  # noqa: E712
    ).scalars().all()
    hero_slides = [{"image": s.image, "label": s.label, "text": s.title, "sub": s.subtitle} for s in slides] or _FALLBACK_HERO_SLIDES

    banner_raw = get_settings_by_prefix(db, "dessert_banner_")
    banner = {**_DESSERT_BANNER_DEFAULTS, **{k.replace("dessert_banner_", ""): v for k, v in banner_raw.items()}}
    banner["image"] = item_img(banner["image"]) if banner["image"] else random_dessert_image(db)

    visible = SiteReview.status != ReviewStatus.DECLINED
    total_reviews = db.execute(select(func.count()).select_from(SiteReview).where(visible)).scalar_one()
    reviews = db.execute(
        select(SiteReview.name, SiteReview.text, SiteReview.rating)
        .where(visible, func.length(SiteReview.text) > 20)
        .order_by(SiteReview.rating.desc(), SiteReview.created_at.desc())
        .limit(3)
    ).all()
    if not reviews:
        reviews = db.execute(
            select(SiteReview.name, SiteReview.text, SiteReview.rating)
            .where(visible).order_by(SiteReview.created_at.desc()).limit(3)
        ).all()

    return {
        "hero_slides": [{**s, "image": item_img(s["image"]), "label": s["label"] or "", "sub": s["sub"] or ""} for s in hero_slides],
        "food_items": _products(fetch_top_ordered_items(db, [ProductCategory.FAST_FOOD, ProductCategory.PIZZA], limit=3)),
        "drink_items": _products(fetch_top_ordered_items(db, [ProductCategory.COLD_DRINK, ProductCategory.COFFEE], limit=5, days=7)),
        "dessert_items": _products(fetch_popular_items(db, [ProductCategory.DESSERT], limit=3)),
        "about": about_block(db),
        "dessert_banner": banner,
        "reviews": [
            {"name": r.name, "text": r.text, "rating": int(r.rating or 5), "avatar_color": review_avatar_color(r.name)}
            for r in reviews
        ],
        "total_reviews": total_reviews,
    }


def gallery_url(filename: str) -> str:
    """`gallery.filename` is a bare filename for local photos, a full URL
    for Supabase-hosted ones."""
    return filename if filename.startswith("http") else f"/static/images/gallery/{filename}"


@router.get("/gallery", response_model=GalleryPage)
def gallery(db: Session = Depends(get_db)):
    photos = db.execute(select(Gallery).order_by(Gallery.created_at.desc(), Gallery.id.desc())).scalars().all()
    return {
        "photos": [{"id": p.id, "url": gallery_url(p.filename), "alt": p.alt or "", "category": enum_value(p.category)} for p in photos],
        "food_count": sum(1 for p in photos if enum_value(p.category) == GalleryCategory.FOOD.value),
        "interior_count": sum(1 for p in photos if enum_value(p.category) == GalleryCategory.INTERIOR.value),
    }


@router.get("/about", response_model=AboutBlock)
def about(db: Session = Depends(get_db)):
    """The "About us" block (edited in the admin panel), for /about."""
    return about_block(db)
