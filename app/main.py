"""
FastAPI application entrypoint.

Phase 1 (foundations) scope only: session/CSRF/permission wiring, static
asset mounting, and a couple of debug routes used to verify the session
middleware round-trips correctly (see the migration plan's Phase 1
verification step). Public/admin page routers are added in later phases.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.dependencies import AuthRequired
from app.middleware.session import DBSessionMiddleware
from app.routers.admin import auth as admin_auth
from app.routers.admin import dashboard as admin_dashboard
from app.routers.admin import admin_users as admin_admin_users
from app.routers.admin import orders as admin_orders
from app.routers.admin import products as admin_products
from app.routers.admin import gallery as admin_gallery
from app.routers.admin import sauces as admin_sauces
from app.routers.public import auth as public_auth
from app.routers.public import cart_forms as public_cart_forms
from app.routers.public import cart_page as public_cart_page
from app.routers.public import checkout as public_checkout
from app.routers.public import menu as public_menu
from app.routers.public import pages as public_pages
from app.routers.public import payments as public_payments
from app.routers.public import profile as public_profile
from app.routers.public import reviews as public_reviews
from app.services.csrf import CSRFError
from app.services.csrf import is_ajax as _is_ajax
from app.services.permissions import AdminAccessDenied

settings = get_settings()

app = FastAPI(title="Coffee Time")

app.add_middleware(DBSessionMiddleware)

# The existing static/ directory (CSS/JS/images) is reused unchanged —
# no asset was touched or renamed for this port.
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(public_pages.router)
app.include_router(public_menu.router)
app.include_router(public_reviews.router)
app.include_router(public_cart_forms.router)
app.include_router(public_cart_page.router)
app.include_router(public_auth.router)
app.include_router(public_checkout.router)
app.include_router(public_payments.router)
app.include_router(public_profile.router)
app.include_router(admin_auth.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_orders.router)
app.include_router(admin_admin_users.router)
app.include_router(admin_products.router)
app.include_router(admin_sauces.router)
app.include_router(admin_gallery.router)


@app.exception_handler(CSRFError)
async def csrf_error_handler(request: Request, exc: CSRFError):
    # Mirrors includes/helpers.php::verify_csrf() exactly: AJAX requests
    # get a JSON 403, full-page requests get a flash + redirect back.
    if _is_ajax(request):
        return JSONResponse({"error": exc.message}, status_code=403)
    request.state.session["flash_error"] = exc.message
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=303)


@app.exception_handler(AdminAccessDenied)
async def admin_access_denied_handler(request: Request, exc: AdminAccessDenied):
    # Mirrors admin/includes/perm.php's require_perm()/require_super():
    # flash + redirect to the admin dashboard. Unlike the PHP version
    # (where dashboard.php never actually rendered admin_flash), the
    # Jinja2 admin_base.html template added in Phase 7 renders this
    # unconditionally, so the message is no longer silently lost.
    request.state.session["admin_flash"] = exc.message
    request.state.session["admin_flash_type"] = "error"
    return RedirectResponse("/admin/dashboard", status_code=303)


@app.exception_handler(AuthRequired)
async def auth_required_handler(request: Request, exc: AuthRequired):
    if _is_ajax(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


# --- Phase 1 verification routes (debug only, remove before Phase 10) ---


@app.get("/debug/session-test")
async def session_test(request: Request):
    count = request.state.session.get("hits", 0) + 1
    request.state.session["hits"] = count
    return {"hits": count}


@app.get("/debug/health")
async def health():
    return {"status": "ok", "env": settings.APP_ENV}
