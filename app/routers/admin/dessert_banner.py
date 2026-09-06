"""Port of admin/dessert_banner.php. Already had require_perm('content')
in PHP — no permission-check fix needed.

The CREATE TABLE IF NOT EXISTS site_settings DDL is not reproduced (part
of the Alembic baseline); the "INSERT IGNORE the defaults" seeding is
reproduced for parity, same as about_section.py."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.catalog import DessertItem
from app.services.media import save_cropped_image
from app.services.permissions import require_perm
from app.services.settings import get_settings_by_prefix, set_setting
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/dessert-banner",
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


@router.get("")
def dessert_banner_page(request: Request, db: Session = Depends(get_db)):
    _ensure_defaults(db)
    settings = {**DEFAULTS, **get_settings_by_prefix(db, "dessert_banner_")}

    random_img = None
    if not (settings.get("dessert_banner_image") or ""):
        # ORDER BY RAND() LIMIT 1 — func.rand() maps to MySQL's RAND(),
        # same as app/routers/public/pages.py's identical query. SQLite
        # (used in tests) doesn't understand RAND(); tests seed a custom
        # dessert_banner_image to skip this branch instead of exercising
        # it — a documented MySQL-vs-SQLite test-environment limitation,
        # not a code bug (see FASTAPI_MIGRATION.md).
        random_row = db.execute(select(DessertItem.image).order_by(func.rand()).limit(1)).first()
        random_img = "/" + random_row[0].lstrip("/") if random_row else None

    has_custom_image = bool(settings.get("dessert_banner_image"))
    photo_version = ""
    if has_custom_image:
        # ?v=filemtime(...) cache-bust, same as PHP — without it the
        # browser can keep showing the old photo after a re-upload, since
        # the filename ("dessert-banner.<ext>") doesn't change.
        image_path = PROJECT_ROOT / settings["dessert_banner_image"]
        try:
            photo_version = int(image_path.stat().st_mtime)
        except OSError:
            photo_version = int(time.time())

    return admin_render(
        request, db, "admin/dessert_banner.html", page_title="Банер «Десерт дня»", active_page="dessert_banner",
        settings=settings, has_custom_image=has_custom_image, random_img=random_img, photo_version=photo_version,
    )


@router.post("")
async def dessert_banner_submit(request: Request, db: Session = Depends(get_db)):
    _ensure_defaults(db)
    form = await request.form()

    for field in EDITABLE_FIELDS:
        set_setting(db, field, (form.get(field) or "").strip())

    upload_dir = PROJECT_ROOT / "static" / "images" / "main"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = ""

    b64 = form.get("dessert_banner_image_b64") or ""
    if b64:
        ext = save_cropped_image(b64, upload_dir / "dessert-banner.jpg")
        if ext:
            saved_path = f"static/images/main/dessert-banner.{ext}"
    else:
        upload = form.get("dessert_banner_image")
        filename = getattr(upload, "filename", None)
        if filename:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            data = await upload.read()
            if ext in ALLOWED_EXT and len(data) <= MAX_UPLOAD_SIZE:
                fname = f"dessert-banner.{ext}"
                (upload_dir / fname).write_bytes(data)
                saved_path = f"static/images/main/{fname}"

    if saved_path:
        set_setting(db, "dessert_banner_image", saved_path)

    # Remove custom image (falls back to a random dessert on the site)
    if form.get("clear_image") is not None:
        set_setting(db, "dessert_banner_image", "")

    session = request.state.session
    session["admin_flash"] = "Збережено."
    session["admin_flash_type"] = "success"
    return RedirectResponse("/admin/dessert-banner", status_code=303)
