"""
Port of admin/includes/perm.php.

Exact 5 permission keys confirmed via all_perms(): orders_view,
orders_edit, products, content, reviews. `super` short-circuits every
check; `staff` permissions are the explicit JSON array on admin_users.

Per the confirmed migration decisions, this port also FIXES two bug
classes found in the PHP admin panel rather than reproducing them:
  1. admin/view_order.php called `require_perm('orders')` — not a real
     key from all_perms() — making it effectively super-only. The FastAPI
     route uses `require_perm('orders_view')` instead.
  2. Product-mutation routes (add/edit/delete item) and the DB backup
     route checked only "logged in as some admin" in PHP, with no
     `require_perm('products')`/`require_super()` — meaning any staff
     account could hit them directly by URL regardless of assigned
     permissions. The FastAPI routes apply the same permission dependency
     their listing pages already implied.
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from starlette.requests import Request

ALL_PERMS: dict[str, str] = {
    "orders_view": "Переглядати замовлення",
    "orders_edit": "Змінювати статус замовлень",
    "products": "Управляти товарами",
    "content": "Редагувати контент (слайдер, про нас, галерея)",
    "reviews": "Управляти відгуками",
}


class AdminAccessDenied(Exception):
    """Raised on a failed require_perm()/require_super() check. PHP set a
    session flash and redirected to dashboard.php; the FastAPI exception
    handler (app/main.py) reproduces that — and, unlike PHP's
    admin/includes/layout_top.php, the flash is guaranteed to render
    because admin_base.html reads it unconditionally (see Phase 7 notes:
    today's dashboard.php never displayed it)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def admin_role(request: Request) -> str:
    return request.state.session.get("admin_role", "")


def admin_perms(request: Request) -> list[str]:
    raw = request.state.session.get("admin_perms", [])
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return []
    return list(raw)


def is_super(request: Request) -> bool:
    return admin_role(request) == "super"


def has_perm(request: Request, perm: str) -> bool:
    if is_super(request):
        return True
    return perm in admin_perms(request)


def require_perm(perm: str):
    """FastAPI dependency factory: `Depends(require_perm("products"))`."""

    def _dep(request: Request) -> None:
        if not has_perm(request, perm):
            raise AdminAccessDenied("У вас немає доступу до цього розділу.")

    return _dep


def require_super(request: Request) -> None:
    if not is_super(request):
        raise AdminAccessDenied("Цей розділ доступний тільки головному адміну.")
