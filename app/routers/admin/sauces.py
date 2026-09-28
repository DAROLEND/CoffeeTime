"""Admin sauce management: list/add/update/toggle/delete.

Sauce photos are saved to local disk only (not mirrored to Supabase like
product photos). A rejected or oversized upload is ignored and the
existing image kept, rather than failing the whole save."""
from __future__ import annotations

import random
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import bad_request, not_found
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.catalog import Sauce
from app.schemas.admin import AdminSauce, SauceActiveRequest, SauceSaved
from app.schemas.common import SuccessResponse
from app.services.media import item_img, save_cropped_image
from app.services.permissions import require_perm

router = APIRouter(
    prefix="/admin/sauces",
    tags=["admin"],
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
    return f"sauce_{int(time.time())}_{random.randint(1000, 9999)}"


def _has_photo(image: str | None) -> bool:
    if not image or "default.jpg" in image:
        return False
    return image.startswith("http") or (PROJECT_ROOT / image).exists()


def _sauce_out(s: Sauce) -> dict:
    has_photo = _has_photo(s.image)
    return {
        "id": s.id, "name": s.name, "price": float(s.price or 0), "image": item_img(s.image) if has_photo else "",
        "has_photo": has_photo, "active": bool(s.active), "sort_order": s.sort_order or 0,
    }


async def _store_image(image_b64: str, upload: UploadFile | None) -> str:
    upload_dir = PROJECT_ROOT / "static" / "images" / "menu_items" / "sauces"
    upload_dir.mkdir(parents=True, exist_ok=True)

    if image_b64:
        fname = _unique_name()
        ext = save_cropped_image(image_b64, upload_dir / f"{fname}.jpg")
        return f"static/images/menu_items/sauces/{fname}.{ext}" if ext else ""

    if upload is not None and upload.filename:
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        data = await upload.read()
        if ext in ALLOWED_EXT and len(data) <= MAX_UPLOAD_SIZE:
            fname = f"{_unique_name()}.{ext}"
            (upload_dir / fname).write_bytes(data)
            return f"static/images/menu_items/sauces/{fname}"
    return ""


@router.get("", response_model=list[AdminSauce])
def list_sauces(db: Session = Depends(get_db)):
    return [_sauce_out(s) for s in db.execute(select(Sauce).order_by(Sauce.sort_order, Sauce.id)).scalars().all()]


@router.post("", response_model=SauceSaved, status_code=201)
async def add_sauce(
    name: str = Form(""), price: str = Form(""), sort_order: str = Form(""), active: bool = Form(False),
    image_b64: str = Form(""), image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    name = name.strip()
    if not name:
        raise bad_request("Назва обовʼязкова")
    sauce = Sauce(
        name=name, price=_numval(price), image=await _store_image(image_b64, image), emoji="",
        active=active, sort_order=int(_numval(sort_order)),
    )
    db.add(sauce)
    db.commit()
    return {"success": True, "sauce": _sauce_out(sauce)}


@router.post("/{sauce_id}", response_model=SauceSaved)
async def update_sauce(
    sauce_id: int,
    name: str = Form(""), price: str = Form(""), sort_order: str = Form(""), active: bool = Form(False),
    image_b64: str = Form(""), image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    sauce = db.get(Sauce, sauce_id)
    if sauce is None:
        raise not_found("Соус не знайдено.")
    name = name.strip()
    if not name:
        raise bad_request("Назва обовʼязкова")
    new_image = await _store_image(image_b64, image)
    if new_image:
        sauce.image = new_image
    sauce.name = name
    sauce.price = _numval(price)
    sauce.active = active
    sauce.sort_order = int(_numval(sort_order))
    db.commit()
    return {"success": True, "sauce": _sauce_out(sauce)}


@router.patch("/{sauce_id}/active", response_model=SuccessResponse)
def toggle_sauce(sauce_id: int, body: SauceActiveRequest, db: Session = Depends(get_db)):
    sauce = db.get(Sauce, sauce_id)
    if sauce is None:
        raise not_found("Соус не знайдено.")
    sauce.active = body.active
    db.commit()
    return {"success": True}


@router.delete("/{sauce_id}", response_model=SuccessResponse)
def delete_sauce(sauce_id: int, db: Session = Depends(get_db)):
    sauce = db.get(Sauce, sauce_id)
    if sauce is not None:
        db.delete(sauce)
        db.commit()
    return {"success": True}
