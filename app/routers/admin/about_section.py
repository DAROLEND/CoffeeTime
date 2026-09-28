"""Admin editor for the homepage About section (site_settings `about_*`).
Missing rows are seeded with the defaults on first access; the public
side merges the same defaults in memory (app/routers/public/pages.py)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.routers.public.pages import ABOUT_DEFAULTS, years_open
from app.schemas.admin import AboutSettings
from app.services.media import item_img, save_cropped_image
from app.services.permissions import require_perm
from app.services.settings import get_settings_by_prefix, set_setting

router = APIRouter(
    prefix="/admin/about-section",
    tags=["admin"],
    dependencies=[Depends(get_current_admin), Depends(require_perm("content"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 4 * 1024 * 1024
EDITABLE_FIELDS = ["about_title", "about_text", "about_founded_year", "about_menu_count", "about_rating"]


def _ensure_defaults(db: Session) -> None:
    existing = get_settings_by_prefix(db, "about_")
    for key, value in ABOUT_DEFAULTS.items():
        if key not in existing:
            set_setting(db, key, value)


def _view(db: Session) -> dict:
    settings = {**ABOUT_DEFAULTS, **get_settings_by_prefix(db, "about_")}
    return {
        **{k: settings[k] for k in EDITABLE_FIELDS},
        "about_photo": item_img(settings["about_photo"]),
        "years_open": years_open(settings["about_founded_year"]),
    }


@router.get("", response_model=AboutSettings)
def about_section(db: Session = Depends(get_db)):
    _ensure_defaults(db)
    return _view(db)


@router.post("", response_model=AboutSettings)
async def save_about_section(
    about_title: str = Form(""), about_text: str = Form(""), about_founded_year: str = Form(""),
    about_menu_count: str = Form(""), about_rating: str = Form(""),
    about_photo_b64: str = Form(""), about_photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    _ensure_defaults(db)
    values = dict(about_title=about_title, about_text=about_text, about_founded_year=about_founded_year,
                  about_menu_count=about_menu_count, about_rating=about_rating)
    for field in EDITABLE_FIELDS:
        set_setting(db, field, values[field].strip())

    upload_dir = PROJECT_ROOT / "static" / "images" / "main"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = ""
    if about_photo_b64:
        ext = save_cropped_image(about_photo_b64, upload_dir / "about-photo.jpg")
        if ext:
            saved_path = f"static/images/main/about-photo.{ext}"
    elif about_photo is not None and about_photo.filename:
        ext = about_photo.filename.rsplit(".", 1)[-1].lower() if "." in about_photo.filename else ""
        data = await about_photo.read()
        if ext in ALLOWED_EXT and len(data) <= MAX_UPLOAD_SIZE:
            (upload_dir / f"about-photo.{ext}").write_bytes(data)
            saved_path = f"static/images/main/about-photo.{ext}"
    if saved_path:
        set_setting(db, "about_photo", saved_path)
    return _view(db)
