"""
Jinja2 setup + a `render()` helper that injects the same "ambient" context
every PHP page got for free via includes/header.php: the cart badge count,
the logged-in user (or None), and the csrf_field()/icon() helpers as
template globals (mirrors PHP calling icon(...)/csrf_field() directly in
markup).
"""
from __future__ import annotations

import datetime

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.config import get_settings
from app.services.csrf import csrf_field as _csrf_field
from app.services.icons import icon
from app.services.menu import fmt_price

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["icon"] = icon
templates.env.filters["fmt_price"] = fmt_price
# SQLAlchemy's Enum columns come back as Python enum members when read
# fresh from the DB, but a plain string when a route already normalized
# it (or when an in-memory object was constructed without a DB round
# trip — see app/services/profile.py's _enum_value for the same issue).
# This filter lets templates handle both shapes uniformly.
templates.env.filters["enum_value"] = lambda x: x.value if hasattr(x, "value") else (x or "")


def _cart_badge_count(session) -> int:
    cart = session.get("cart", [])
    return sum(int(ci.get("quantity", 0)) for ci in cart) if isinstance(cart, list) else 0


def render(request: Request, template_name: str, status_code: int = 200, **context) -> HTMLResponse:
    session = request.state.session
    base_context = {
        "request": request,
        "user": session.get("user"),
        "cart_badge_count": _cart_badge_count(session),
        "csrf_field": lambda: _csrf_field(session),
        "flash_error": session.pop("flash_error", None),
        "current_year": datetime.datetime.now().year,
        "ga_id": get_settings().GA_ID,
    }
    base_context.update(context)
    return templates.TemplateResponse(request, template_name, base_context, status_code=status_code)


def admin_render(request: Request, db, template_name: str, status_code: int = 200, **context) -> HTMLResponse:
    from app.services.admin_common import admin_layout_context

    base_context = {"request": request, **admin_layout_context(request, db)}
    base_context.update(context)
    return templates.TemplateResponse(request, template_name, base_context, status_code=status_code)
