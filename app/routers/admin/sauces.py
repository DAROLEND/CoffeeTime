"""Port of admin/admin_sauces.php. Already had require_perm('products') in
PHP — unlike manage_items.php's add/edit/delete siblings, no permission-
check fix was needed here.

Note: unlike the product-item upload pipeline (app/services/storage.py),
this file never called includes/storage.php's supabase_upload() — sauce
photos are saved to local disk only, even though storage.php was
require_once'd (only its save_cropped_image()-adjacent helper is used).
Reproduced as-is; not a confirmed fix target."""
from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.catalog import Sauce
from app.services.media import save_cropped_image
from app.services.permissions import require_perm
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/sauces",
    dependencies=[Depends(get_current_admin), Depends(require_perm("products"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 2 * 1024 * 1024

_NUM_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)")


def _numval(raw) -> float:
    s = (raw or "").strip() if isinstance(raw, str) else raw
    if not s:
        return 0.0
    m = _NUM_RE.match(str(s))
    return float(m.group(0)) if m else 0.0


def _unique_name() -> str:
    # PHP: 'sauce_' . time() . '_' . mt_rand(1000,9999) — exact format is
    # never parsed back, only kept opaque/collision-safe.
    return f"sauce_{int(time.time())}_{random.randint(1000, 9999)}"


def _has_photo(image: str | None) -> bool:
    if not image or "default.jpg" in image:
        return False
    return (PROJECT_ROOT / image).exists()


async def _handle_sauce_image(form) -> str:
    """Shared add/update image branch. Returns the new image path, or ''
    if nothing valid was supplied — callers then leave the existing image
    untouched, same as PHP (a rejected/missing upload here is silently
    ignored, not surfaced as a form error)."""
    upload_dir = PROJECT_ROOT / "static" / "images" / "menu_items" / "sauces"
    upload_dir.mkdir(parents=True, exist_ok=True)

    b64 = form.get("sauce_image_b64") or ""
    if b64:
        fname = _unique_name()
        ext = save_cropped_image(b64, upload_dir / f"{fname}.jpg")
        return f"static/images/menu_items/sauces/{fname}.{ext}" if ext else ""

    upload = form.get("sauce_image")
    filename = getattr(upload, "filename", None)
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        data = await upload.read()
        if ext in ALLOWED_EXT and len(data) <= MAX_UPLOAD_SIZE:
            fname = f"{_unique_name()}.{ext}"
            (upload_dir / fname).write_bytes(data)
            return f"static/images/menu_items/sauces/{fname}"
    return ""


def _sauce_json(s: Sauce) -> str:
    # Mirrors json_encode($s) in PHP: the *raw* row, not filtered by
    # has_photo — the edit form's JS preview trusts `image` unconditionally
    # (see module docstring's has_photo note for the analogous listing-page
    # behavior, which IS filtered).
    return json.dumps({
        "id": s.id, "name": s.name, "price": float(s.price) if s.price is not None else 0,
        "image": s.image or "", "active": 1 if s.active else 0, "sort_order": s.sort_order or 0,
    }, ensure_ascii=False)


@router.get("")
def sauces_page(request: Request, db: Session = Depends(get_db)):
    rows = db.execute(select(Sauce).order_by(Sauce.sort_order, Sauce.id)).scalars().all()
    sauces = [{"row": s, "has_photo": _has_photo(s.image), "json": _sauce_json(s)} for s in rows]
    return admin_render(request, db, "admin/admin_sauces.html", page_title="Соуси", active_page="sauces", sauces=sauces)


@router.post("")
async def sauces_action(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    action = (form.get("action") or "").strip()

    if action == "add":
        name = (form.get("name") or "").strip()
        price = _numval(form.get("price"))
        sort_order = int(_numval(form.get("sort_order")))
        active = form.get("active") is not None
        if not name:
            return JSONResponse({"success": False, "error": "Назва обовʼязкова"})

        image_path = await _handle_sauce_image(form)
        sauce = Sauce(name=name, price=price, image=image_path, emoji="", active=active, sort_order=sort_order)
        db.add(sauce)
        db.commit()
        return JSONResponse({"success": True, "id": sauce.id, "image": image_path})

    if action == "update":
        sauce_id = int(_numval(form.get("id")))
        name = (form.get("name") or "").strip()
        if not sauce_id or not name:
            return JSONResponse({"success": False, "error": "Невірні дані"})
        sauce = db.get(Sauce, sauce_id)
        if not sauce:
            return JSONResponse({"success": False, "error": "Невірні дані"})

        new_image = await _handle_sauce_image(form)
        if new_image:
            sauce.image = new_image
        sauce.name = name
        sauce.price = _numval(form.get("price"))
        sauce.active = form.get("active") is not None
        sauce.sort_order = int(_numval(form.get("sort_order")))
        db.commit()
        return JSONResponse({"success": True})

    if action == "toggle":
        sauce_id = int(_numval(form.get("id")))
        if not sauce_id:
            return JSONResponse({"success": False})
        sauce = db.get(Sauce, sauce_id)
        if sauce:
            sauce.active = bool(int(_numval(form.get("active"))))
            db.commit()
        return JSONResponse({"success": True})

    if action == "delete":
        sauce_id = int(_numval(form.get("id")))
        if not sauce_id:
            return JSONResponse({"success": False})
        sauce = db.get(Sauce, sauce_id)
        if sauce:
            db.delete(sauce)
            db.commit()
        return JSONResponse({"success": True})

    return JSONResponse({"success": False, "error": "Unknown action"})
