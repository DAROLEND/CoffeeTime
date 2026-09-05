"""Public read-only pages: index, gallery, about, contact.
menu.py and reviews.py carry their own routers (substantial page-specific
logic) and are included alongside this one in app/main.py."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.categories import ProductCategory
from app.db.session import get_db
from app.models.catalog import DessertItem
from app.models.cms import Gallery, GalleryCategory, HeroSlide, SiteReview
from app.services.home import fetch_popular_items, fetch_top_ordered_items, review_avatar_color
from app.services.media import item_img
from app.services.settings import get_settings_by_prefix
from app.templating import render

router = APIRouter()

_FALLBACK_HERO_SLIDES = [
    {"image": "static/images/categories/coffee_category.webp", "label": "", "text": "Кожен ковток — тепла історія", "sub": "Свіжозварена кава щоранку з любов'ю"},
    {"image": "static/images/categories/dessert.webp", "label": "", "text": "Неможливо встояти…", "sub": "Десерти власного приготування щодня"},
    {"image": "static/images/categories/fast_food.webp", "label": "", "text": "Ідеальне комбо", "sub": "Смачно, ситно і завжди свіже"},
]

_ABOUT_DEFAULTS = {
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


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    slides = db.execute(
        select(HeroSlide).where(HeroSlide.active == True).order_by(HeroSlide.sort_order, HeroSlide.id)  # noqa: E712
    ).scalars().all()
    hero_slides = (
        [{"image": s.image, "label": s.label, "text": s.title, "sub": s.subtitle} for s in slides]
        or _FALLBACK_HERO_SLIDES
    )

    food_items = fetch_top_ordered_items(db, [ProductCategory.FAST_FOOD, ProductCategory.PIZZA], limit=3)
    drink_items = fetch_top_ordered_items(db, [ProductCategory.COLD_DRINK, ProductCategory.COFFEE], limit=5, days=7)
    dessert_items = fetch_popular_items(db, [ProductCategory.DESSERT], limit=3)

    about = {**_ABOUT_DEFAULTS, **get_settings_by_prefix(db, "about_")}
    banner_raw = get_settings_by_prefix(db, "dessert_banner_")
    dessert_banner = {**_DESSERT_BANNER_DEFAULTS, **{k.replace("dessert_banner_", ""): v for k, v in banner_raw.items()}}

    if dessert_banner["image"]:
        dessert_banner_img = "/" + dessert_banner["image"].lstrip("/")
    else:
        # ORDER BY RAND() LIMIT 1 — func.rand() maps to MySQL's RAND().
        random_row = db.execute(select(DessertItem.image).order_by(func.rand()).limit(1)).first()
        dessert_banner_img = "/" + random_row[0].lstrip("/") if random_row else None

    total_reviews = db.execute(select(func.count()).select_from(SiteReview)).scalar_one()
    reviews = db.execute(
        select(SiteReview.name, SiteReview.text, SiteReview.rating)
        .where(func.length(SiteReview.text) > 20)
        .order_by(SiteReview.rating.desc(), SiteReview.created_at.desc())
        .limit(3)
    ).all()
    if not reviews:
        reviews = db.execute(
            select(SiteReview.name, SiteReview.text, SiteReview.rating)
            .order_by(SiteReview.created_at.desc())
            .limit(3)
        ).all()

    years_open = 2026 - int(about.get("about_founded_year") or 2016)

    return render(
        request,
        "public/index.html",
        page="home",
        page_title="Головна | Coffee Time",
        preload_hero_image=hero_slides[0]["image"] if hero_slides else "",
        hero_slides=hero_slides,
        food_items=food_items,
        drink_items=drink_items,
        dessert_items=dessert_items,
        about=about,
        years_open=years_open,
        about_photo="/" + (about.get("about_photo") or "static/images/main/about-photo.png").lstrip("/"),
        dessert_banner=dessert_banner,
        dessert_banner_img=dessert_banner_img,
        reviews=[{"name": r.name, "text": r.text, "rating": r.rating} for r in reviews],
        total_reviews=total_reviews,
        review_avatar_color=review_avatar_color,
    )


@router.get("/gallery")
def gallery(request: Request, db: Session = Depends(get_db)):
    photos = db.execute(select(Gallery).order_by(Gallery.created_at.desc())).scalars().all()
    food_count = sum(1 for p in photos if p.category == GalleryCategory.FOOD)
    interior_count = sum(1 for p in photos if p.category == GalleryCategory.INTERIOR)
    return render(
        request,
        "public/gallery.html",
        page="gallery",
        page_title="Галерея — Coffee Time",
        photos=photos,
        food_count=food_count,
        interior_count=interior_count,
    )


@router.get("/about")
def about(request: Request):
    return render(request, "public/empty_page.html", page="about", page_title="Coffee Time")


@router.get("/contact")
def contact(request: Request):
    return render(request, "public/empty_page.html", page="contact", page_title="Coffee Time")
