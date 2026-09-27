from __future__ import annotations

from pydantic import BaseModel


class HeroSlideOut(BaseModel):
    image: str
    label: str
    text: str
    sub: str


class HomeProduct(BaseModel):
    id: int
    table: str
    name: str
    description: str
    image: str
    price: float


class AboutBlock(BaseModel):
    title: str
    text: str
    founded_year: str
    menu_count: str
    rating: str
    photo: str
    years_open: int


class DessertBanner(BaseModel):
    label: str
    title: str
    desc: str
    btn: str
    image: str | None


class HomeReview(BaseModel):
    name: str
    text: str
    rating: int
    avatar_color: str


class HomePage(BaseModel):
    hero_slides: list[HeroSlideOut]
    food_items: list[HomeProduct]
    drink_items: list[HomeProduct]
    dessert_items: list[HomeProduct]
    about: AboutBlock
    dessert_banner: DessertBanner
    reviews: list[HomeReview]
    total_reviews: int


class GalleryPhoto(BaseModel):
    id: int
    url: str
    alt: str
    category: str


class GalleryPage(BaseModel):
    photos: list[GalleryPhoto]
    food_count: int
    interior_count: int
