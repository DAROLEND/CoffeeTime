"""Admin hero-slider management: add/edit/delete/reorder/toggle slides.
Seeds 3 default slides on a genuinely empty table (see _ensure_seed_data),
so a fresh install always has something to show."""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.errors import bad_request, not_found
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.cms import HeroSlide
from app.schemas.admin import AdminHeroSlide, SlideMoveRequest, SlideToggleResult
from app.schemas.common import SuccessResponse
from app.services.media import item_img, save_cropped_image
from app.services.permissions import require_perm

router = APIRouter(
    prefix="/admin/hero-slides",
    tags=["admin"],
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
    if db.execute(select(func.count()).select_from(HeroSlide)).scalar_one() == 0:
        for image, title, subtitle, order in SEED_SLIDES:
            db.add(HeroSlide(image=image, title=title, subtitle=subtitle, sort_order=order))
        db.commit()


def _slide_out(s: HeroSlide) -> dict:
    return {
        "id": s.id, "image": item_img(s.image), "label": s.label or "", "title": s.title or "",
        "subtitle": s.subtitle or "", "sort_order": s.sort_order or 0, "active": bool(s.active),
    }


async def _store_image(image_b64: str, upload: UploadFile | None) -> str:
    """Returns the saved path, '' if no image was sent; 400 on a bad one."""
    upload_dir = PROJECT_ROOT / "static" / "images" / "slides"
    upload_dir.mkdir(parents=True, exist_ok=True)
    fname = f"slide_{secrets.token_hex(4)}"

    if image_b64:
        ext = save_cropped_image(image_b64, upload_dir / f"{fname}.jpg")
        if not ext:
            raise bad_request("Помилка збереження зображення.")
        return f"static/images/slides/{fname}.{ext}"

    if upload is not None and upload.filename:
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if ext not in ALLOWED_EXT:
            raise bad_request("Дозволені формати: JPG, PNG, WEBP.")
        data = await upload.read()
        if len(data) > MAX_UPLOAD_SIZE:
            raise bad_request("Файл занадто великий (макс 4 MB).")
        (upload_dir / f"{fname}.{ext}").write_bytes(data)
        return f"static/images/slides/{fname}.{ext}"
    return ""


def _delete_slide_file(image: str | None) -> None:
    if image and "slides/" in image:
        path = PROJECT_ROOT / image
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass


def _ordered(db: Session) -> list[HeroSlide]:
    return db.execute(select(HeroSlide).order_by(HeroSlide.sort_order.asc(), HeroSlide.id.asc())).scalars().all()


@router.get("", response_model=list[AdminHeroSlide])
def list_slides(db: Session = Depends(get_db)):
    _ensure_seed_data(db)
    return [_slide_out(s) for s in _ordered(db)]


@router.post("", response_model=AdminHeroSlide, status_code=201)
async def add_slide(
    label: str = Form(""), title: str = Form(""), subtitle: str = Form(""),
    image_b64: str = Form(""), image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    title = title.strip()
    if not title:
        raise bad_request("Заголовок обовʼязковий.")
    image_path = await _store_image(image_b64, image)
    if not image_path:
        raise bad_request("Оберіть зображення.")
    max_order = db.execute(select(func.coalesce(func.max(HeroSlide.sort_order), 0))).scalar_one()
    slide = HeroSlide(image=image_path, label=label.strip(), title=title, subtitle=subtitle.strip(), sort_order=max_order + 1)
    db.add(slide)
    db.commit()
    return _slide_out(slide)


@router.post("/{slide_id}", response_model=AdminHeroSlide)
async def edit_slide(
    slide_id: int,
    label: str = Form(""), title: str = Form(""), subtitle: str = Form(""),
    image_b64: str = Form(""), image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    slide = db.get(HeroSlide, slide_id)
    if slide is None:
        raise not_found("Слайд не знайдено.")
    title = title.strip()
    if not title:
        raise bad_request("Заголовок обовʼязковий.")
    new_img = await _store_image(image_b64, image)
    if new_img:
        _delete_slide_file(slide.image)
        slide.image = new_img
    slide.label = label.strip()
    slide.title = title
    slide.subtitle = subtitle.strip()
    db.commit()
    return _slide_out(slide)


@router.post("/{slide_id}/toggle", response_model=SlideToggleResult)
def toggle_slide(slide_id: int, db: Session = Depends(get_db)):
    slide = db.get(HeroSlide, slide_id)
    if slide is None:
        raise not_found("Слайд не знайдено.")
    slide.active = not slide.active
    db.commit()
    return {"ok": True, "active": bool(slide.active)}


@router.post("/{slide_id}/move", response_model=SuccessResponse)
def move_slide(slide_id: int, body: SlideMoveRequest, db: Session = Depends(get_db)):
    """Swap with the neighbour, then renumber every slide 0..n-1 so gaps
    or duplicate sort_order values can't accumulate."""
    ids = [s.id for s in _ordered(db)]
    if slide_id not in ids:
        raise not_found("Слайд не знайдено.")
    pos = ids.index(slide_id)
    swap = pos - 1 if body.dir == "up" else pos + 1
    if 0 <= swap < len(ids):
        ids[pos], ids[swap] = ids[swap], ids[pos]
        for i, row_id in enumerate(ids):
            db.execute(update(HeroSlide).where(HeroSlide.id == row_id).values(sort_order=i))
        db.commit()
    return {"success": True}


@router.delete("/{slide_id}", response_model=SuccessResponse)
def delete_slide(slide_id: int, db: Session = Depends(get_db)):
    slide = db.get(HeroSlide, slide_id)
    if slide is not None:
        _delete_slide_file(slide.image)
        db.delete(slide)
        db.commit()
    return {"success": True}
