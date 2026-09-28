from __future__ import annotations

from app.schemas.base import Schema


class HeroSlideOut(Schema):
    image: str
    label: str
    text: str
    sub: str


class HomeProduct(Schema):
    id: int
    table: str
    name: str
    description: str
    image: str
    price: float


class AboutBlock(Schema):
    title: str
    text: str
    founded_year: str
    menu_count: str
    rating: str
    photo: str
    years_open: int


class DessertBanner(Schema):
    label: str
    title: str
    desc: str
    btn: str
    image: str | None


class HomeReview(Schema):
    name: str
    text: str
    rating: int
    avatar_color: str


class HomePage(Schema):
    hero_slides: list[HeroSlideOut]
    food_items: list[HomeProduct]
    drink_items: list[HomeProduct]
    dessert_items: list[HomeProduct]
    about: AboutBlock
    dessert_banner: DessertBanner
    reviews: list[HomeReview]
    total_reviews: int


class GalleryPhoto(Schema):
    id: int
    url: str
    alt: str
    category: str


class GalleryPage(Schema):
    photos: list[GalleryPhoto]
    food_count: int
    interior_count: int
