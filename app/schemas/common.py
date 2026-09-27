from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    errors: list[str] = Field(default_factory=list)


class OkResponse(BaseModel):
    ok: bool = True


class SuccessResponse(BaseModel):
    success: bool
    error: str | None = None


class Pagination(BaseModel):
    page: int
    total_pages: int
    total: int
