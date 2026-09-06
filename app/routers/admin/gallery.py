"""Port of admin/admin_gallery.php. Already had require_perm('content')
in PHP — no permission-check fix needed."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.cms import Gallery, GalleryCategory
from app.config import get_settings
from app.services.csrf import is_ajax
from app.services.permissions import require_perm
from app.services.storage import supabase_delete, unique_filename, upload_image
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/gallery",
    dependencies=[Depends(get_current_admin), Depends(require_perm("content"))],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
ALLOWED_CATS = {"food", "interior"}


def _parse_cat(raw: str | None) -> str:
    return raw if raw in ALLOWED_CATS else "food"


def _delete_gallery_file(filename: str) -> None:
    """`gallery.filename` stores a bare filename for locally-saved photos
    (unlike the product-item pipeline, which stores a full relative path)
    — so, unlike delete_stored_image(), the gallery dir has to be prepended
    here, exactly as PHP's `$galleryDir . $row['filename']` does."""
    if not filename:
        return
    if filename.startswith("http"):
        settings = get_settings()
        from urllib.parse import urlparse

        parsed = urlparse(filename).path
        prefix = f"/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"
        if parsed.startswith(prefix):
            supabase_delete(parsed[len(prefix):])
    else:
        path = PROJECT_ROOT / "static" / "images" / "gallery" / filename
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass


@router.get("")
def gallery_page(request: Request, db: Session = Depends(get_db), cat: str = "", uploaded: int | None = None):
    filter_cat = cat.strip()
    clauses = []
    if filter_cat in ALLOWED_CATS:
        clauses.append(Gallery.category == filter_cat)

    rows = db.execute(select(Gallery).where(*clauses).order_by(Gallery.created_at.desc())).scalars().all()

    return admin_render(
        request, db, "admin/admin_gallery.html", page_title="Галерея", active_page="gallery",
        images=rows, filter_cat=filter_cat, counts=_counts(db), uploaded=uploaded, errors=[],
    )


@router.post("")
async def gallery_post(request: Request, db: Session = Depends(get_db)):
    if is_ajax(request):
        return await _gallery_action(request, db)
    return await _gallery_upload(request, db)


async def _gallery_action(request: Request, db: Session) -> JSONResponse:
    try:
        data = await request.json()
    except ValueError:
        data = {}
    action = data.get("action") or ""

    if action == "delete":
        item_id = int(data.get("id") or 0)
        row = db.get(Gallery, item_id)
        if not row:
            return JSONResponse({"success": False})
        _delete_gallery_file(row.filename)
        db.delete(row)
        db.commit()
        return JSONResponse({"success": True})

    if action == "set_category":
        item_id = int(data.get("id") or 0)
        new_cat = _parse_cat(data.get("category"))
        row = db.get(Gallery, item_id)
        if not row:
            return JSONResponse({"success": False})
        row.category = new_cat
        db.commit()
        return JSONResponse({"success": True})

    if action == "set_alt":
        item_id = int(data.get("id") or 0)
        alt = (data.get("alt") or "").strip()[:255]
        row = db.get(Gallery, item_id)
        if not row:
            return JSONResponse({"success": False})
        row.alt = alt
        db.commit()
        return JSONResponse({"success": True})

    return JSONResponse({"success": False})


async def _gallery_upload(request: Request, db: Session):
    form = await request.form()
    uploads = form.getlist("photos[]") or form.getlist("photos")
    category = _parse_cat(form.get("category"))
    alt = (form.get("alt") or "").strip()[:255]

    gallery_dir = PROJECT_ROOT / "static" / "images" / "gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    uploaded_count = 0
    for upload in uploads:
        filename = getattr(upload, "filename", None)
        if not filename:
            continue
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXT:
            errors.append(f"{filename}: непідтримуваний формат.")
            continue

        new_name = f"{unique_filename('gallery_')}.{ext}"
        mime = "image/png" if ext == "png" else ("image/gif" if ext == "gif" else ("image/webp" if ext == "webp" else "image/jpeg"))
        data = await upload.read()
        saved = upload_image(data, gallery_dir / new_name, f"gallery/{new_name}", mime)
        if saved:
            # `saved` is either a Supabase public URL, or (fallback) the
            # bare filename — gallery.filename stores exactly that (no
            # directory prefix), matching PHP; the "static/images/gallery/"
            # prefix is added at render time instead (see the template).
            file_alt = alt or Path(filename).stem
            db.add(Gallery(filename=saved, alt=file_alt, category=category))
            db.commit()
            uploaded_count += 1
        else:
            errors.append(f"Не вдалося зберегти {filename}")

    if uploaded_count > 0:
        return RedirectResponse(f"/admin/gallery?uploaded={uploaded_count}", status_code=303)

    # No action attribute on the upload <form> — the browser resubmits to
    # the current URL, query string included, exactly like PHP reading
    # $_GET['cat'] back on this same POST.
    filter_cat = request.query_params.get("cat", "").strip()
    clauses = [Gallery.category == filter_cat] if filter_cat in ALLOWED_CATS else []
    return admin_render(
        request, db, "admin/admin_gallery.html", page_title="Галерея", active_page="gallery",
        images=db.execute(select(Gallery).where(*clauses).order_by(Gallery.created_at.desc())).scalars().all(),
        filter_cat=filter_cat, counts=_counts(db), uploaded=None, errors=errors,
    )


def _counts(db: Session) -> dict:
    counts = {"all": 0, "food": 0, "interior": 0}
    for category, c in db.execute(select(Gallery.category, func.count()).group_by(Gallery.category)).all():
        key = category.value if hasattr(category, "value") else category
        counts[key] = c
        counts["all"] += c
    return counts
