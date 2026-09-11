"""
Admin permission model: 5 permission keys (orders_view, orders_edit,
products, content, reviews). `super` short-circuits every check; `staff`
permissions are the explicit JSON array on admin_users.
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
    """Raised on a failed require_perm()/require_super() check. The
    exception handler in app/main.py sets a session flash and redirects
    to the dashboard, which renders it unconditionally."""

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
