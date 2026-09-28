"""Staff accounts (super-admin only): create/edit/delete accounts and
their permissions, plus the current admin's own account settings."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError, bad_request, not_found
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.auth import AdminUser
from app.schemas.admin import AdminUserCreate, AdminUsersPage, AdminUserUpdate, MessageResult, MyAccountUpdate
from app.services.auth import hash_password, verify_password
from app.services.enum_utils import enum_value
from app.services.permissions import ALL_PERMS, require_super

router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(get_current_admin), Depends(require_super)],
)


def _clean_perms(perms: list[str]) -> list[str]:
    """Known keys only; editing orders implies viewing them."""
    perms = [p for p in dict.fromkeys(perms) if p in ALL_PERMS]
    if "orders_edit" in perms and "orders_view" not in perms:
        perms.append("orders_view")
    return perms


def _perms_of(u: AdminUser) -> list[str]:
    try:
        return json.loads(u.permissions or "[]")
    except ValueError:
        return []


@router.get("", response_model=AdminUsersPage)
def list_admins(request: Request, db: Session = Depends(get_db)):
    me = request.state.session.get("admin")
    rows = db.execute(select(AdminUser).order_by((AdminUser.role == "super").desc(), AdminUser.id)).scalars().all()
    return {
        "users": [
            {"id": u.id, "username": u.username, "display_name": u.display_name or "", "role": enum_value(u.role) or "staff",
             "perms": _perms_of(u), "is_me": u.username == me}
            for u in rows
        ],
        "all_perms": [{"key": k, "label": v} for k, v in ALL_PERMS.items()],
    }


@router.post("", response_model=MessageResult, status_code=201)
def create_admin(body: AdminUserCreate, db: Session = Depends(get_db)):
    username = body.username.strip()
    perms = _clean_perms(body.perms)
    if len(username) < 3:
        raise bad_request("Логін мінімум 3 символи.")
    if len(body.password) < 6:
        raise bad_request("Пароль мінімум 6 символів.")
    if not perms:
        raise bad_request("Оберіть принаймні одне право доступу.")
    if db.execute(select(AdminUser.id).where(AdminUser.username == username)).first():
        raise bad_request("Такий логін вже існує.", code="duplicate")
    db.add(AdminUser(
        username=username, password=hash_password(body.password), role="staff",
        permissions=json.dumps(perms), display_name=body.display_name.strip(),
    ))
    db.commit()
    return {"ok": True, "message": f"Акаунт «{username}» створено."}


@router.post("/me", response_model=MessageResult)
def update_my_account(body: MyAccountUpdate, request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    me = db.execute(select(AdminUser).where(AdminUser.username == session.get("admin"))).scalar_one_or_none()
    if me is None or not verify_password(body.current_password, me.password):
        raise bad_request("Невірний поточний пароль.", code="invalid_credentials")
    if body.new_password and len(body.new_password) < 6:
        raise bad_request("Новий пароль мінімум 6 символів.")
    me.display_name = body.display_name.strip()
    if body.new_password:
        me.password = hash_password(body.new_password)
    db.commit()
    if me.display_name:
        session["admin_display"] = me.display_name
    return {"ok": True, "message": "Акаунт оновлено."}


@router.patch("/{user_id}", response_model=MessageResult)
def update_admin(user_id: int, body: AdminUserUpdate, request: Request, db: Session = Depends(get_db)):
    target = db.get(AdminUser, user_id)
    if target is None:
        raise not_found("Акаунт не знайдено.")
    if enum_value(target.role) == "super" and target.username != request.state.session.get("admin"):
        raise ApiError(403, "Не можна редагувати інших super-адмінів.", code="forbidden")
    target.display_name = body.display_name.strip()
    if enum_value(target.role) != "super":
        target.permissions = json.dumps(_clean_perms(body.perms))
    if body.new_password:
        if len(body.new_password) < 6:
            raise bad_request("Новий пароль мінімум 6 символів.")
        target.password = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "Збережено."}


@router.delete("/{user_id}", response_model=MessageResult)
def delete_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    target = db.get(AdminUser, user_id)
    if target is None:
        raise not_found("Акаунт не знайдено.")
    if target.username == request.state.session.get("admin"):
        raise bad_request("Не можна видалити власний акаунт.")
    if enum_value(target.role) == "super":
        raise ApiError(403, "Не можна видалити super-адміна.", code="forbidden")
    username = target.username
    db.delete(target)
    db.commit()
    return {"ok": True, "message": f"Акаунт «{username}» видалено."}
