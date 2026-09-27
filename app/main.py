"""
FastAPI application entrypoint: a JSON API under /api (consumed by the
React SPA in frontend/), static assets under /static, the DB-backed
session middleware, and the exception handlers that give every error
the same `{detail, code, errors}` body.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import ApiError, error_body
from app.api.router import api_router, webhook_router
from app.config import get_settings
from app.dependencies import AuthRequired
from app.middleware.session import DBSessionMiddleware
from app.services.csrf import CSRFError
from app.services.permissions import AdminAccessDenied

app = FastAPI(
    title="Coffee Time API",
    version="2.0.0",
    description="JSON API behind the Coffee Time café site. Session-cookie auth; "
    "mutating requests need the `X-CSRF-Token` header (see `GET /api/csrf-token`).",
)

app.add_middleware(DBSessionMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router)
app.include_router(webhook_router)


@app.get("/api/health", include_in_schema=False)
def health():
    return {"ok": True}


@app.get("/", include_in_schema=False)
def root():
    """The backend has no pages of its own any more. When FRONTEND_URL is
    set (production), old links to the API host land on the SPA."""
    frontend = get_settings().FRONTEND_URL
    if frontend:
        return RedirectResponse(frontend, status_code=302)
    return {"name": "Coffee Time API", "docs": "/docs", "openapi": "/openapi.json"}


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(error_body(exc.detail, exc.code, exc.errors), status_code=exc.status_code)


@app.exception_handler(CSRFError)
async def csrf_error_handler(request: Request, exc: CSRFError):
    code = "csrf_expired" if exc.session_expired else "csrf_invalid"
    return JSONResponse(error_body(exc.message, code), status_code=403)


@app.exception_handler(AdminAccessDenied)
async def admin_access_denied_handler(request: Request, exc: AdminAccessDenied):
    return JSONResponse(error_body(exc.message, "forbidden"), status_code=403)


@app.exception_handler(AuthRequired)
async def auth_required_handler(request: Request, exc: AuthRequired):
    return JSONResponse(error_body("Потрібно увійти в акаунт.", "auth_required"), status_code=401)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(error_body("Некоректні дані запиту.", "invalid_request", errors), status_code=422)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(error_body(str(exc.detail), None), status_code=exc.status_code)
