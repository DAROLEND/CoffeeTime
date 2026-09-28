from __future__ import annotations

from typing import Literal

from app.schemas.base import Schema


class PublicReview(Schema):
    name: str
    initial: str
    avatar_color: str
    text: str
    rating: int
    created_at: str


class RatingBucket(Schema):
    stars: int
    count: int
    pct: int


class ReviewsPage(Schema):
    sort: Literal["newest", "oldest", "best", "worst"]
    filter: int
    page: int
    total_pages: int
    total_count: int
    filtered_count: int
    avg_rating: float
    distribution: list[RatingBucket]
    reviews: list[PublicReview]
    reviewed_already: bool


class ReviewCreate(Schema):
    name: str = ""
    text: str = ""
    rating: int = 0
