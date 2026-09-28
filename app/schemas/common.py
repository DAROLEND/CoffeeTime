from __future__ import annotations

from pydantic import Field

from app.schemas.base import Schema


class ErrorResponse(Schema):
    detail: str
    code: str | None = None
    errors: list[str] = Field(default_factory=list)


class OkResponse(Schema):
    ok: bool = True


class SuccessResponse(Schema):
    success: bool
    error: str | None = None


class Pagination(Schema):
    page: int
    total_pages: int
    total: int
