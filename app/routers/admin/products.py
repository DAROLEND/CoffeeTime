"""Port of admin/manage_items.php, admin/add_item.php, admin/edit_item.php,
admin/ajax_delete_item.php.

Confirmed fix applied: `require_perm('products')` on every route in this
router. PHP only ever checked it on manage_items.php's listing page —
add_item.php/edit_item.php/ajax_delete_item.php checked just "some admin
is logged in" via auth_check.php, so any staff account (regardless of
assigned permissions) could create/edit/delete products by hitting those
URLs directly. All four now share the same permission."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.orders import OrderItem
from app.services.permissions import require_perm
from app.services.storage import delete_stored_image, unique_filename, upload_image, upload_image_b64
from app.templating import admin_render

router = APIRouter(
    prefix="/admin/manage-items",
    dependencies=[Depends(get_current_admin), Depends(require_perm("products"))],
)

# .../CoffeeTime-release (repo root — where static/images/... lives)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

ALLOWED = [
    ProductCategory.COFFEE, ProductCategory.FAST_FOOD, ProductCategory.PIZZA, ProductCategory.MINI_PIZZA,
    ProductCategory.COLD_DRINK, ProductCategory.ICE_CREAM, ProductCategory.DESSERT, ProductCategory.SUSHI,
    ProductCategory.SUSHI_SET, ProductCategory.SALAD, ProductCategory.CAKE,
]
CATEGORY_NAMES = {
    ProductCategory.COFFEE: "Кава", ProductCategory.FAST_FOOD: "Фаст-фуд",
    ProductCategory.PIZZA: "Піца", ProductCategory.MINI_PIZZA: "Міні-піца",
    ProductCategory.COLD_DRINK: "Холодні напої", ProductCategory.ICE_CREAM: "Морозиво",
    ProductCategory.DESSERT: "Десерти", ProductCategory.SUSHI: "Суші",
    ProductCategory.SUSHI_SET: "Сети суші", ProductCategory.SALAD: "Салати",
    ProductCategory.CAKE: "Торти на замовлення",
}
CATEGORY_FOLDERS = {
    ProductCategory.COFFEE: "coffee", ProductCategory.COLD_DRINK: "cold_drinks",
    ProductCategory.ICE_CREAM: "ice_cream", ProductCategory.DESSERT: "desserts",
    ProductCategory.FAST_FOOD: "fast_food", ProductCategory.PIZZA: "pizza",
    ProductCategory.MINI_PIZZA: "mini_pizza", ProductCategory.SUSHI: "sushi",
    ProductCategory.SUSHI_SET: "sushi", ProductCategory.SALAD: "salads",
    ProductCategory.CAKE: "cakes",
}
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}

_FLOAT_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)")


def _floatval(raw) -> float:
    """PHP's floatval(): parses a leading numeric prefix, 0.0 on anything
    else (never raises) — HTML `type=number` inputs already constrain the
    common case, this just matches the fallback behavior exactly."""
    s = (raw or "").strip() if isinstance(raw, str) else raw
    if not s:
        return 0.0
    m = _FLOAT_RE.match(str(s))
    return float(m.group(0)) if m else 0.0


def _has_photo(image: str | None) -> bool:
    """Port of manage_items.php's $hasPhoto check. `file_exists()` on an
    http(s) Supabase URL always returns false in PHP (no local file at
    that path) — so, faithfully reproduced, a Supabase-hosted photo never
    counts as "has photo" on this page and falls back to the placeholder
    icon. That's an existing display quirk, not something introduced
    here; not in scope to fix (not one of the confirmed bugs)."""
    if not image or "default.jpg" in image:
        return False
    return (PROJECT_ROOT / image).exists()


def _item_js_payload(item, has_photo: bool) -> str:
    """Mirrors `$itemForJs = array_merge($item, [...]); json_encode(...)`
    — the inline JSON the "Редагувати" button embeds for the edit modal
    to prefill from, without a extra round trip to the server."""
    data = {
        "id": item.id, "name": item.name, "description": item.description or "",
        "price": float(item.price) if hasattr(item, "price") else None,
        "image": item.image if has_photo else "",
    }
    if hasattr(item, "variant_options"):
        data["variant_options"] = item.variant_options
    if hasattr(item, "pieces_count"):
        data["pieces_count"] = item.pieces_count
    return json.dumps(data, ensure_ascii=False)


def _parse_category(raw: str) -> ProductCategory | None:
    try:
        cat = ProductCategory(raw)
    except ValueError:
        return None
    return cat if cat in ALLOWED else None


def _variant_options_json(form) -> str:
    diff2 = _floatval(form.get("scoop_diff_2"))
    diff3 = _floatval(form.get("scoop_diff_3"))
    return json.dumps({
        "type": "scoops", "label": "Кількість кульок",
        "options": [
            {"id": "1", "label": "1 кулька", "price_diff": 0},
            {"id": "2", "label": "2 кульки", "price_diff": diff2},
            {"id": "3", "label": "3 кульки", "price_diff": diff3},
        ],
    }, ensure_ascii=False)


async def _handle_image_upload(form, category: ProductCategory) -> tuple[str, list[str]]:
    """Shared upload_image_b64/upload_image branch from add_item.php +
    edit_item.php. Returns (image_path, errors) — image_path is '' if
    nothing new was uploaded or an error occurred."""
    errors: list[str] = []
    subfolder = CATEGORY_FOLDERS.get(category, "other")
    upload_dir = PROJECT_ROOT / "static" / "images" / "menu_items" / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    remote_base = f"menu_items/{subfolder}"

    image_b64 = form.get("image_b64") or ""
    upload = form.get("image")
    has_upload_file = bool(getattr(upload, "filename", None))

    image_path = ""
    if image_b64:
        fname = unique_filename()
        saved = upload_image_b64(image_b64, upload_dir / fname, f"{remote_base}/{fname}")
        if saved:
            image_path = saved if saved.startswith("http") else f"static/images/menu_items/{subfolder}/{saved}"
        else:
            errors.append("Помилка збереження зображення.")
    elif has_upload_file:
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if ext not in ALLOWED_EXT:
            errors.append("Дозволені формати: JPG, PNG, WebP, GIF.")
        else:
            file_name = f"{unique_filename()}.{ext}"
            mime = "image/png" if ext == "png" else ("image/webp" if ext == "webp" else "image/jpeg")
            data = await upload.read()
            saved = upload_image(data, upload_dir / file_name, f"{remote_base}/{file_name}", mime)
            if saved:
                image_path = saved if saved.startswith("http") else f"static/images/menu_items/{subfolder}/{file_name}"
            else:
                errors.append("Не вдалося зберегти зображення.")
    return image_path, errors


@router.get("")
def manage_items_page(request: Request, db: Session = Depends(get_db), category: str = "all", saved: int | None = None):
    is_all = category == "all"
    cat_enum = None if is_all else _parse_category(category)
    if not is_all and cat_enum is None:
        is_all = True
    cat_title = "Всі товари" if is_all else CATEGORY_NAMES.get(cat_enum, category)

    popularity: dict[int, int] = {}
    if not is_all:
        rows = db.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity))
            .where(OrderItem.category == cat_enum.value)
            .group_by(OrderItem.product_id)
        ).all()
        popularity = {int(pid): int(qty) for pid, qty in rows}

    def _entry(row, table: ProductCategory) -> dict:
        has_photo = _has_photo(row.image)
        return {
            "row": row, "table": table, "has_photo": has_photo,
            "item_json": _item_js_payload(row, has_photo),
        }

    products = []
    if is_all:
        for cat in ALLOWED:
            model = CATEGORY_MODEL_MAP[cat]
            rows = db.execute(select(model).order_by(model.id.desc())).scalars().all()
            for row in rows:
                products.append(_entry(row, cat))
        products.sort(key=lambda it: it["row"].name)
    else:
        model = CATEGORY_MODEL_MAP[cat_enum]
        rows = db.execute(select(model).order_by(model.id.desc())).scalars().all()
        products = [_entry(row, cat_enum) for row in rows]

    tab_counts = {}
    for cat in ALLOWED:
        model = CATEGORY_MODEL_MAP[cat]
        tab_counts[cat.value] = db.execute(select(func.count()).select_from(model)).scalar_one()
    tab_counts["all"] = sum(tab_counts.values())

    return admin_render(
        request, db, "admin/manage_items.html", page_title="Товари", active_page="products",
        is_all=is_all, category=(cat_enum.value if cat_enum else "all"), cat_title=cat_title,
        allowed=ALLOWED, category_names=CATEGORY_NAMES, tab_counts=tab_counts,
        products=products, popularity=popularity, saved=saved is not None,
    )


@router.get("/add")
def add_item_form(request: Request, db: Session = Depends(get_db), category: str = ""):
    cat_enum = _parse_category(category)
    if cat_enum is None:
        return RedirectResponse("/admin/manage-items", status_code=303)
    return admin_render(
        request, db, "admin/product_add.html", page_title="Додати товар", active_page="products",
        category=cat_enum.value, cat_title=CATEGORY_NAMES[cat_enum], errors=[], form_data={},
    )


@router.post("/add")
async def add_item_submit(request: Request, db: Session = Depends(get_db), category: str = ""):
    cat_enum = _parse_category(category)
    if cat_enum is None:
        return RedirectResponse("/admin/manage-items", status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    desc = (form.get("description") or "").strip()
    price = _floatval(form.get("price"))
    price_per_kg = _floatval(form.get("price_per_kg"))
    min_weight = _floatval(form.get("min_weight")) or 1.0
    is_cake = cat_enum == ProductCategory.CAKE

    errors: list[str] = []
    if not name:
        errors.append("Введіть назву товару.")
    if is_cake:
        if price_per_kg <= 0:
            errors.append("Ціна за кг має бути більша за 0.")
        if min_weight <= 0:
            min_weight = 1.0
    else:
        if price <= 0:
            errors.append("Ціна має бути більша за 0.")

    image_b64 = form.get("image_b64") or ""
    upload = form.get("image")
    has_upload_file = bool(getattr(upload, "filename", None))
    if not image_b64 and not has_upload_file:
        errors.append("Оберіть зображення для завантаження.")

    image_path = ""
    if not errors:
        image_path, upload_errors = await _handle_image_upload(form, cat_enum)
        errors.extend(upload_errors)

    if not errors and image_path:
        model = CATEGORY_MODEL_MAP[cat_enum]
        if is_cake:
            db.add(model(name=name, description=desc, price_per_kg=price_per_kg, min_weight=min_weight, image=image_path))
        elif cat_enum == ProductCategory.ICE_CREAM:
            db.add(model(name=name, description=desc, price=price, variant_options=_variant_options_json(form), image=image_path))
        else:
            db.add(model(name=name, description=desc, price=price, image=image_path))
        db.commit()
        return RedirectResponse(f"/admin/manage-items?category={cat_enum.value}&saved=1", status_code=303)

    return admin_render(
        request, db, "admin/product_add.html", page_title="Додати товар", active_page="products",
        category=cat_enum.value, cat_title=CATEGORY_NAMES[cat_enum], errors=errors, form_data=form,
        status_code=200,
    )


@router.get("/edit")
def edit_item_form(request: Request, db: Session = Depends(get_db), category: str = "", id: int = 0):
    cat_enum = _parse_category(category)
    if cat_enum is None or id <= 0:
        return RedirectResponse("/admin/manage-items", status_code=303)

    model = CATEGORY_MODEL_MAP[cat_enum]
    product = db.get(model, id)
    if not product:
        return RedirectResponse(f"/admin/manage-items?category={cat_enum.value}", status_code=303)

    return admin_render(
        request, db, "admin/product_edit.html", page_title="Редагувати товар", active_page="products",
        category=cat_enum.value, cat_title=CATEGORY_NAMES[cat_enum], product=product, errors=[],
    )


@router.post("/edit")
async def edit_item_submit(request: Request, db: Session = Depends(get_db), category: str = "", id: int = 0):
    cat_enum = _parse_category(category)
    if cat_enum is None or id <= 0:
        return RedirectResponse("/admin/manage-items", status_code=303)

    model = CATEGORY_MODEL_MAP[cat_enum]
    product = db.get(model, id)
    if not product:
        return RedirectResponse(f"/admin/manage-items?category={cat_enum.value}", status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    desc = (form.get("description") or "").strip()
    price = _floatval(form.get("price"))
    image_path = product.image

    errors: list[str] = []
    if not name:
        errors.append("Введіть назву товару.")
    if price <= 0:
        errors.append("Ціна має бути більша за 0.")

    image_b64 = form.get("image_b64") or ""
    upload = form.get("image")
    has_upload_file = bool(getattr(upload, "filename", None))
    remove_image = (form.get("remove_image") or "") == "1"

    if remove_image and not image_b64 and not has_upload_file:
        delete_stored_image(image_path, PROJECT_ROOT)
        image_path = ""
    elif image_b64 or has_upload_file:
        new_path, upload_errors = await _handle_image_upload(form, cat_enum)
        errors.extend(upload_errors)
        if new_path:
            delete_stored_image(product.image, PROJECT_ROOT)
            image_path = new_path

    if not errors:
        product.name = name
        product.description = desc
        product.price = price
        product.image = image_path
        if cat_enum == ProductCategory.ICE_CREAM:
            product.variant_options = _variant_options_json(form)
        elif cat_enum == ProductCategory.SUSHI_SET:
            product.pieces_count = max(0, int(_floatval(form.get("pieces_count"))))
        db.commit()
        return RedirectResponse(f"/admin/manage-items?category={cat_enum.value}&saved=1", status_code=303)

    return admin_render(
        request, db, "admin/product_edit.html", page_title="Редагувати товар", active_page="products",
        category=cat_enum.value, cat_title=CATEGORY_NAMES[cat_enum], product=product, errors=errors,
        status_code=200,
    )


@router.post("/delete")
async def ajax_delete_item(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except ValueError:
        data = {}
    item_id = int(data.get("id") or 0)
    cat_enum = _parse_category(str(data.get("category") or ""))

    if not item_id or cat_enum is None:
        return JSONResponse({"success": False, "error": "Invalid input"})

    model = CATEGORY_MODEL_MAP[cat_enum]
    product = db.get(model, item_id)
    if not product:
        return JSONResponse({"success": True})

    image_path = product.image
    db.delete(product)
    db.commit()
    if image_path:
        local = PROJECT_ROOT / image_path
        if local.exists():
            try:
                local.unlink()
            except OSError:
                pass

    return JSONResponse({"success": True})
