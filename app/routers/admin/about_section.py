"""Admin editor for the homepage About section. Seeds default
site_settings rows on first access (see also app/routers/public/pages.py,
which merges the same defaults in memory without requiring the rows to
exist)."""
from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.services.media import save_cropped_image
from app.services.permissions import require_perm
from app.services.settings import get_settings_by_prefix, set_setting
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/about-section",
    dependencies=[Depends(get_current_admin), Depends(require_perm("content"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 4 * 1024 * 1024

DEFAULTS = {
    "about_title": "Місце, де час зупиняється",
    "about_text": "Coffee Time — це затишне кафе в серці міста, де ми щодня готуємо свіжі десерти та каву з любов'ю. Ніяких заморожених напівфабрикатів — тільки справжнє та смачне.",
    "about_founded_year": "2016",
    "about_menu_count": "50",
    "about_rating": "4.8",
    "about_photo": "static/images/main/about-photo.png",
}
EDITABLE_FIELDS = ["about_title", "about_text", "about_founded_year", "about_menu_count", "about_rating"]


def _ensure_defaults(db: Session) -> None:
    existing = get_settings_by_prefix(db, "about_")
    for key, value in DEFAULTS.items():
        if key not in existing:
            set_setting(db, key, value)


@router.get("")
def about_section_page(request: Request, db: Session = Depends(get_db)):
    _ensure_defaults(db)
    settings = {**DEFAULTS, **get_settings_by_prefix(db, "about_")}
    years_open = datetime.date.today().year - int(settings.get("about_founded_year") or 2016)
    return admin_render(
        request, db, "admin/about_section.html", page_title="Про нас — головна", active_page="about_section",
        settings=settings, years_open=years_open,
    )


@router.post("")
async def about_section_submit(request: Request, db: Session = Depends(get_db)):
    _ensure_defaults(db)
    form = await request.form()

    for field in EDITABLE_FIELDS:
        set_setting(db, field, (form.get(field) or "").strip())

    upload_dir = PROJECT_ROOT / "static" / "images" / "main"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = ""

    b64 = form.get("about_photo_b64") or ""
    if b64:
        ext = save_cropped_image(b64, upload_dir / "about-photo.jpg")
        if ext:
            saved_path = f"static/images/main/about-photo.{ext}"
    else:
        upload = form.get("about_photo")
        filename = getattr(upload, "filename", None)
        if filename:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            data = await upload.read()
            if ext in ALLOWED_EXT and len(data) <= MAX_UPLOAD_SIZE:
                fname = f"about-photo.{ext}"
                (upload_dir / fname).write_bytes(data)
                saved_path = f"static/images/main/{fname}"

    if saved_path:
        set_setting(db, "about_photo", saved_path)

    session = request.state.session
    session["admin_flash"] = "Збережено."
    session["admin_flash_type"] = "success"
    return RedirectResponse("/admin/about-section", status_code=303)
