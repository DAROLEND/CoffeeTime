"""Admin hero-slider management: add/edit/delete/reorder/toggle slides.
Seeds 3 default slides on a genuinely empty table (see _ensure_seed_data),
so a fresh install always has something to show."""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.cms import HeroSlide
from app.services.media import save_cropped_image
from app.services.permissions import require_perm
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/hero-slides",
    dependencies=[Depends(get_current_admin), Depends(require_perm("content"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 4 * 1024 * 1024

SEED_SLIDES = [
    ("static/images/categories/coffee_category.jpg", "Кожен ковток — тепла історія", "Свіжозварена кава щоранку з любов'ю", 0),
    ("static/images/categories/dessert.jpg", "Неможливо встояти…", "Десерти власного приготування щодня", 1),
    ("static/images/categories/fast_food.jpg", "Ідеальне комбо", "Смачно, ситно і завжди свіже", 2),
]


def _ensure_seed_data(db: Session) -> None:
    count = db.execute(select(func.count()).select_from(HeroSlide)).scalar_one()
    if count == 0:
        for image, title, subtitle, order in SEED_SLIDES:
            db.add(HeroSlide(image=image, title=title, subtitle=subtitle, sort_order=order))
        db.commit()


def _unique_name() -> str:
    return f"slide_{secrets.token_hex(4)}"


async def _handle_slide_image(form) -> tuple[str, str]:
    """Returns (image_path, error). Mirrors the add-form's image branch —
    callers that allow a missing image (edit) just check `image_path`."""
    upload_dir = PROJECT_ROOT / "static" / "images" / "slides"
    upload_dir.mkdir(parents=True, exist_ok=True)

    b64 = form.get("image_b64") or ""
    if b64:
        fname = _unique_name()
        ext = save_cropped_image(b64, upload_dir / f"{fname}.jpg")
        if ext:
            return f"static/images/slides/{fname}.{ext}", ""
        return "", "Помилка збереження зображення."

    upload = form.get("image")
    filename = getattr(upload, "filename", None)
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXT:
            return "", "Дозволені формати: JPG, PNG, WEBP."
        data = await upload.read()
        if len(data) > MAX_UPLOAD_SIZE:
            return "", "Файл занадто великий (макс 4 MB)."
        fname = f"{_unique_name()}.{ext}"
        (upload_dir / fname).write_bytes(data)
        return f"static/images/slides/{fname}", ""

    return "", ""


def _delete_slide_file(image: str | None) -> None:
    if image and "slides/" in image:
        path = PROJECT_ROOT / image
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass


@router.get("")
def hero_slides_page(request: Request, db: Session = Depends(get_db)):
    _ensure_seed_data(db)
    slides = db.execute(select(HeroSlide).order_by(HeroSlide.sort_order.asc(), HeroSlide.id.asc())).scalars().all()
    return admin_render(request, db, "admin/hero_slides.html", page_title="Хіро слайдер", active_page="hero_slides", slides=slides)


@router.post("")
async def hero_slides_action(request: Request, db: Session = Depends(get_db)):
    _ensure_seed_data(db)
    session = request.state.session
    form = await request.form()
    action = form.get("action") or ""

    if action == "toggle":
        return await _toggle(db, form)
    if action == "move":
        return await _move(db, form)

    flash = ""
    flash_type = "success"

    if action == "add":
        label = (form.get("label") or "").strip()
        title = (form.get("title") or "").strip()
        subtitle = (form.get("subtitle") or "").strip()

        if not title:
            flash, flash_type = "Заголовок обовʼязковий.", "error"
        else:
            image_path, err = await _handle_slide_image(form)
            if err:
                flash, flash_type = err, "error"
            elif not image_path:
                flash, flash_type = "Оберіть зображення.", "error"
            else:
                max_order = db.execute(select(func.coalesce(func.max(HeroSlide.sort_order), 0))).scalar_one()
                db.add(HeroSlide(image=image_path, label=label, title=title, subtitle=subtitle, sort_order=max_order + 1))
                db.commit()
                flash = "Слайд додано."

    elif action == "edit":
        slide_id = int(form.get("id") or 0)
        label = (form.get("label") or "").strip()
        title = (form.get("title") or "").strip()
        subtitle = (form.get("subtitle") or "").strip()

        if slide_id and title:
            new_img, _err = await _handle_slide_image(form)
            slide = db.get(HeroSlide, slide_id)
            if slide:
                if new_img:
                    _delete_slide_file(slide.image)
                    slide.image = new_img
                slide.label = label
                slide.title = title
                slide.subtitle = subtitle
                db.commit()
            flash = "Збережено."
        # else: silently no-op (no flash set) if id/title are missing.

    elif action == "delete":
        slide_id = int(form.get("id") or 0)
        if slide_id:
            slide = db.get(HeroSlide, slide_id)
            if slide:
                _delete_slide_file(slide.image)
                db.delete(slide)
                db.commit()
            flash = "Слайд видалено."

    if flash:
        session["admin_flash"] = flash
        session["admin_flash_type"] = flash_type
    return RedirectResponse("/admin/hero-slides", status_code=303)


async def _toggle(db: Session, form):
    is_ajax = bool(form.get("ajax"))
    slide_id = int(form.get("id") or 0)
    new_active = 0
    if slide_id:
        slide = db.get(HeroSlide, slide_id)
        if slide:
            slide.active = not slide.active
            db.commit()
            new_active = 1 if slide.active else 0
    if is_ajax:
        return JSONResponse({"ok": True, "active": new_active})
    return RedirectResponse("/admin/hero-slides", status_code=303)


async def _move(db: Session, form):
    is_ajax = bool(form.get("ajax"))
    slide_id = int(form.get("id") or 0)
    direction = form.get("dir") or ""

    if slide_id and direction in ("up", "down"):
        rows = db.execute(select(HeroSlide.id).order_by(HeroSlide.sort_order.asc(), HeroSlide.id.asc())).scalars().all()
        ids = list(rows)
        if slide_id in ids:
            pos = ids.index(slide_id)
            swap_pos = pos - 1 if direction == "up" else pos + 1
            if 0 <= swap_pos < len(ids):
                ids[pos], ids[swap_pos] = ids[swap_pos], ids[pos]
                for i, row_id in enumerate(ids):
                    db.execute(update(HeroSlide).where(HeroSlide.id == row_id).values(sort_order=i))
                db.commit()

    if is_ajax:
        return JSONResponse({"ok": True})
    return RedirectResponse("/admin/hero-slides", status_code=303)
