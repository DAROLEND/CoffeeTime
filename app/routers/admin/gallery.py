"""Admin gallery management: browsing, category/alt-text editing,
deletion, and multi-photo upload."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.config import get_settings
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.cms import Gallery
from app.routers.public.pages import gallery_url
from app.schemas.admin import AdminGalleryPage, GalleryPatch, GalleryUploadResult
from app.schemas.common import SuccessResponse
from app.services.enum_utils import enum_value
from app.services.permissions import require_perm
from app.services.storage import supabase_delete, unique_filename, upload_image

router = APIRouter(
    prefix="/admin/gallery",
    tags=["admin"],
    dependencies=[Depends(get_current_admin), Depends(require_perm("content"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
ALLOWED_CATS = {"food", "interior"}


def _delete_gallery_file(filename: str) -> None:
    """`gallery.filename` stores a bare filename for locally-saved photos
    (unlike the product pipeline, which stores a full relative path), so
    the gallery dir is prepended here."""
    if not filename:
        return
    if filename.startswith("http"):
        parsed = urlparse(filename).path
        prefix = f"/storage/v1/object/public/{get_settings().SUPABASE_BUCKET}/"
        if parsed.startswith(prefix):
            supabase_delete(parsed[len(prefix):])
        return
    path = PROJECT_ROOT / "static" / "images" / "gallery" / filename
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _counts(db: Session) -> dict:
    counts = {"all": 0, "food": 0, "interior": 0}
    for category, c in db.execute(select(Gallery.category, func.count()).group_by(Gallery.category)).all():
        counts[enum_value(category)] = c
        counts["all"] += c
    return counts


@router.get("", response_model=AdminGalleryPage)
def gallery_page(cat: str = "", db: Session = Depends(get_db)):
    filter_cat = cat.strip() if cat.strip() in ALLOWED_CATS else ""
    clauses = [Gallery.category == filter_cat] if filter_cat else []
    rows = db.execute(select(Gallery).where(*clauses).order_by(Gallery.created_at.desc(), Gallery.id.desc())).scalars().all()
    return {
        "images": [
            {"id": r.id, "url": gallery_url(r.filename), "alt": r.alt or "", "category": enum_value(r.category),
             "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else ""}
            for r in rows
        ],
        "counts": _counts(db),
        "filter": filter_cat,
    }


@router.post("", response_model=GalleryUploadResult)
async def upload_photos(
    photos: list[UploadFile] = File(...), category: str = Form("food"), alt: str = Form(""),
    db: Session = Depends(get_db),
):
    category = category if category in ALLOWED_CATS else "food"
    alt = alt.strip()[:255]
    gallery_dir = PROJECT_ROOT / "static" / "images" / "gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    uploaded = 0
    for upload in photos:
        filename = upload.filename or ""
        if not filename:
            continue
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXT:
            errors.append(f"{filename}: непідтримуваний формат.")
            continue
        new_name = f"{unique_filename('gallery_')}.{ext}"
        mime = {"png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/jpeg")
        saved = upload_image(await upload.read(), gallery_dir / new_name, f"gallery/{new_name}", mime)
        if not saved:
            errors.append(f"Не вдалося зберегти {filename}")
            continue
        # `saved` is a Supabase URL or (local fallback) the bare filename.
        db.add(Gallery(filename=saved, alt=alt or Path(filename).stem, category=category))
        db.commit()
        uploaded += 1
    return {"uploaded": uploaded, "errors": errors}


@router.patch("/{photo_id}", response_model=SuccessResponse)
def update_photo(photo_id: int, body: GalleryPatch, db: Session = Depends(get_db)):
    row = db.get(Gallery, photo_id)
    if row is None:
        raise not_found("Фото не знайдено.")
    if body.category is not None:
        row.category = body.category
    if body.alt is not None:
        row.alt = body.alt.strip()[:255]
    db.commit()
    return {"success": True}


@router.delete("/{photo_id}", response_model=SuccessResponse)
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    row = db.get(Gallery, photo_id)
    if row is None:
        raise not_found("Фото не знайдено.")
    _delete_gallery_file(row.filename)
    db.delete(row)
    db.commit()
    return {"success": True}
