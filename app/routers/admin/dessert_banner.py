"""Admin editor for the homepage "dessert of the day" banner
(site_settings `dessert_banner_*`). Without a custom photo the site shows
a random dessert from the menu."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.routers.public.pages import random_dessert_image
from app.schemas.admin import DessertBannerSettings
from app.services.media import item_img, save_cropped_image
from app.services.permissions import require_perm
from app.services.settings import get_settings_by_prefix, set_setting

router = APIRouter(
    prefix="/admin/dessert-banner",
    tags=["admin"],
    dependencies=[Depends(get_current_admin), Depends(require_perm("content"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 4 * 1024 * 1024

DEFAULTS = {
    "dessert_banner_label": "Щодня нове",
    "dessert_banner_title": "Десерт дня",
    "dessert_banner_desc": "Мусові торти, еклери та макарони —\nготуємо кожного ранку зі свіжих інгредієнтів",
    "dessert_banner_btn": "Дивитись десерти →",
    "dessert_banner_image": "",
}
EDITABLE_FIELDS = ["dessert_banner_label", "dessert_banner_title", "dessert_banner_desc", "dessert_banner_btn"]


def _ensure_defaults(db: Session) -> None:
    existing = get_settings_by_prefix(db, "dessert_banner_")
    for key, value in DEFAULTS.items():
        if key not in existing:
            set_setting(db, key, value)


def _view(db: Session) -> dict:
    settings = {**DEFAULTS, **get_settings_by_prefix(db, "dessert_banner_")}
    image = settings.get("dessert_banner_image") or ""
    url = None
    if image:
        # Cache-bust: the file name ("dessert-banner.<ext>") never changes,
        # so without ?v= the browser keeps showing the previous photo.
        try:
            version = int((PROJECT_ROOT / image).stat().st_mtime)
        except OSError:
            version = int(time.time())
        url = f"{item_img(image)}?v={version}"
    return {
        **{k: settings[k] for k in EDITABLE_FIELDS}, "image": url, "has_custom_image": bool(image),
        "random_image": None if image else random_dessert_image(db),
    }


@router.get("", response_model=DessertBannerSettings)
def dessert_banner(db: Session = Depends(get_db)):
    _ensure_defaults(db)
    return _view(db)


@router.post("", response_model=DessertBannerSettings)
async def save_dessert_banner(
    dessert_banner_label: str = Form(""), dessert_banner_title: str = Form(""),
    dessert_banner_desc: str = Form(""), dessert_banner_btn: str = Form(""),
    dessert_banner_image_b64: str = Form(""), dessert_banner_image: UploadFile | None = File(None),
    clear_image: bool = Form(False),
    db: Session = Depends(get_db),
):
    _ensure_defaults(db)
    values = dict(dessert_banner_label=dessert_banner_label, dessert_banner_title=dessert_banner_title,
                  dessert_banner_desc=dessert_banner_desc, dessert_banner_btn=dessert_banner_btn)
    for field in EDITABLE_FIELDS:
        set_setting(db, field, values[field].strip())

    upload_dir = PROJECT_ROOT / "static" / "images" / "main"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = ""
    if dessert_banner_image_b64:
        ext = save_cropped_image(dessert_banner_image_b64, upload_dir / "dessert-banner.jpg")
        if ext:
            saved_path = f"static/images/main/dessert-banner.{ext}"
    elif dessert_banner_image is not None and dessert_banner_image.filename:
        filename = dessert_banner_image.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        data = await dessert_banner_image.read()
        if ext in ALLOWED_EXT and len(data) <= MAX_UPLOAD_SIZE:
            (upload_dir / f"dessert-banner.{ext}").write_bytes(data)
            saved_path = f"static/images/main/dessert-banner.{ext}"

    if saved_path:
        set_setting(db, "dessert_banner_image", saved_path)
    elif clear_image:
        # Back to a random dessert on the site.
        set_setting(db, "dessert_banner_image", "")
    return _view(db)
