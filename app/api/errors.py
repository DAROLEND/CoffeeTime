"""One error envelope for the whole API.

Every non-2xx response body is `{"detail": str, "code": str | None,
"errors": list[str]}` so the SPA can show `detail` (or each of
`errors`) without special-casing endpoints. Routes raise ApiError;
app/main.py maps it (and the session/CSRF/permission exceptions raised
from dependencies) onto that shape.
"""
from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str, *, code: str | None = None, errors: list[str] | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.errors = errors or []
        super().__init__(detail)


def bad_request(detail: str, *, code: str | None = None, errors: list[str] | None = None) -> ApiError:
    return ApiError(400, detail, code=code, errors=errors)


def not_found(detail: str = "Не знайдено.") -> ApiError:
    return ApiError(404, detail, code="not_found")


def error_body(detail: str, code: str | None = None, errors: list[str] | None = None) -> dict:
    return {"detail": detail, "code": code, "errors": errors or []}
