from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PublicReview(BaseModel):
    name: str
    initial: str
    avatar_color: str
    text: str
    rating: int
    created_at: str


class RatingBucket(BaseModel):
    stars: int
    count: int
    pct: int


class ReviewsPage(BaseModel):
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


class ReviewCreate(BaseModel):
    name: str = ""
    text: str = ""
    rating: int = 0
