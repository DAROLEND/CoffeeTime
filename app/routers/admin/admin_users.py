"""Admin staff-account management: create/edit/delete accounts, manage
permissions, and the current admin's own account settings."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.auth import AdminUser
from app.services.auth import hash_password, verify_password
from app.services.csrf import CSRFError, verify_csrf
from app.services.enum_utils import enum_value
from app.services.permissions import ALL_PERMS, require_super
from app.templating import admin_render

router = APIRouter(prefix="/admin/users", dependencies=[Depends(get_current_admin), Depends(require_super)])


def _extract_perms(form) -> list[str]:
    perms = [k.split("perms[")[1].rstrip("]") for k in form.keys() if k.startswith("perms[")]
    if "orders_edit" in perms and "orders_view" not in perms:
        perms.append("orders_view")
    return perms


@router.get("")
def admin_users_page(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(select(AdminUser).order_by((AdminUser.role == "super").desc(), AdminUser.id)).scalars().all()
    users = []
    for u in rows:
        try:
            perms_arr = json.loads(u.permissions or "[]")
        except ValueError:
            perms_arr = []
        users.append({"row": u, "perms_arr": perms_arr})

    session = request.state.session
    return admin_render(
        request, db, "admin/admin_users.html", page_title="Персонал", active_page="admin_users",
        users=users, all_perms=ALL_PERMS, current_username=session.get("admin"),
        current_display=session.get("admin_display", ""),
    )


@router.post("")
async def admin_users_submit(request: Request, db: Session = Depends(get_db)):
    session = request.state.session
    try:
        await verify_csrf(request)
    except CSRFError as exc:
        session["admin_flash"] = exc.message
        session["admin_flash_type"] = "error"
        return RedirectResponse("/admin/users", status_code=303)

    form = await request.form()
    action = form.get("action", "")
    current_username = session.get("admin")

    if action == "create":
        username = (form.get("username") or "").strip()
        display_name = (form.get("display_name") or "").strip()
        password = form.get("password") or ""
        perms = _extract_perms(form)

        err = ""
        if len(username) < 3:
            err = "Логін мінімум 3 символи."
        if len(password) < 6:
            err = err or "Пароль мінімум 6 символів."
        if not perms:
            err = err or "Оберіть принаймні одне право доступу."
        if not err and db.execute(select(AdminUser.id).where(AdminUser.username == username)).first():
            err = "Такий логін вже існує."

        if err:
            session["admin_flash"], session["admin_flash_type"] = err, "error"
        else:
            db.add(AdminUser(username=username, password=hash_password(password), role="staff", permissions=json.dumps(perms), display_name=display_name))
            db.commit()
            session["admin_flash"] = f"Акаунт «{username}» створено."

    elif action == "my_account":
        display_name = (form.get("display_name") or "").strip()
        new_pass = form.get("new_password") or ""
        cur_pass = form.get("current_password") or ""

        me = db.execute(select(AdminUser).where(AdminUser.username == current_username)).scalar_one_or_none()
        if not me or not verify_password(cur_pass, me.password):
            session["admin_flash"], session["admin_flash_type"] = "Невірний поточний пароль.", "error"
        elif new_pass and len(new_pass) < 6:
            session["admin_flash"], session["admin_flash_type"] = "Новий пароль мінімум 6 символів.", "error"
        else:
            me.display_name = display_name
            if new_pass:
                me.password = hash_password(new_pass)
            db.commit()
            if display_name:
                session["admin_display"] = display_name
            session["admin_flash"] = "Акаунт оновлено."
        return RedirectResponse("/admin/users", status_code=303)

    elif action == "edit":
        user_id = int(form.get("id") or 0)
        display_name = (form.get("display_name") or "").strip()
        perms = _extract_perms(form)
        new_pass = form.get("new_password") or ""

        target = db.get(AdminUser, user_id)
        if not target:
            session["admin_flash"], session["admin_flash_type"] = "Акаунт не знайдено.", "error"
        elif enum_value(target.role) == "super" and target.username != current_username:
            session["admin_flash"], session["admin_flash_type"] = "Не можна редагувати інших super-адмінів.", "error"
        else:
            target.display_name = display_name
            target.permissions = json.dumps(perms)
            if new_pass and len(new_pass) >= 6:
                target.password = hash_password(new_pass)
            db.commit()
            session["admin_flash"] = "Збережено."

    elif action == "delete":
        user_id = int(form.get("id") or 0)
        target = db.get(AdminUser, user_id)
        if not target:
            session["admin_flash"], session["admin_flash_type"] = "Акаунт не знайдено.", "error"
        elif target.username == current_username:
            session["admin_flash"], session["admin_flash_type"] = "Не можна видалити власний акаунт.", "error"
        elif enum_value(target.role) == "super":
            session["admin_flash"], session["admin_flash_type"] = "Не можна видалити super-адміна.", "error"
        else:
            username = target.username
            db.delete(target)
            db.commit()
            session["admin_flash"] = f"Акаунт «{username}» видалено."

    return RedirectResponse("/admin/users", status_code=303)
