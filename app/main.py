"""
FastAPI application entrypoint: session/CSRF/permission middleware and
exception handlers, static asset mounting, and every public storefront
+ admin panel router.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.dependencies import AuthRequired
from app.middleware.session import DBSessionMiddleware
from app.routers.admin import auth as admin_auth
from app.routers.admin import dashboard as admin_dashboard
from app.routers.admin import admin_users as admin_admin_users
from app.routers.admin import orders as admin_orders
from app.routers.admin import products as admin_products
from app.routers.admin import about_section as admin_about_section
from app.routers.admin import backup as admin_backup
from app.routers.admin import dessert_banner as admin_dessert_banner
from app.routers.admin import gallery as admin_gallery
from app.routers.admin import hero_slides as admin_hero_slides
from app.routers.admin import reviews as admin_reviews
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

app = FastAPI(title="Coffee Time")

app.add_middleware(DBSessionMiddleware)

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
app.include_router(admin_reviews.router)
app.include_router(admin_hero_slides.router)
app.include_router(admin_about_section.router)
app.include_router(admin_dessert_banner.router)
app.include_router(admin_backup.router)


@app.exception_handler(CSRFError)
async def csrf_error_handler(request: Request, exc: CSRFError):
    # AJAX requests get a JSON 403; full-page requests get a flash + redirect back.
    if _is_ajax(request):
        return JSONResponse({"error": exc.message}, status_code=403)
    request.state.session["flash_error"] = exc.message
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=303)


@app.exception_handler(AdminAccessDenied)
async def admin_access_denied_handler(request: Request, exc: AdminAccessDenied):
    # Flash + redirect to the admin dashboard, which always renders admin_flash.
    request.state.session["admin_flash"] = exc.message
    request.state.session["admin_flash_type"] = "error"
    return RedirectResponse("/admin/dashboard", status_code=303)


@app.exception_handler(AuthRequired)
async def auth_required_handler(request: Request, exc: AuthRequired):
    if _is_ajax(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return RedirectResponse("/login", status_code=303)
