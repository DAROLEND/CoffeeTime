"""Admin product management across the 11 menu categories: list, read,
create, update, delete. `require_perm('products')` guards every route.

Create/update take multipart/form-data: either a raw `image` file or an
`image_b64` data-URI produced by the in-browser cropper."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import bad_request, not_found
from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.db.session import get_db
from app.dependencies import get_current_admin
from app.models.orders import OrderItem
from app.schemas.admin import AdminProduct, AdminProductsPage, ProductSaved
from app.schemas.common import SuccessResponse
from app.services.media import item_img
from app.services.permissions import require_perm
from app.services.storage import delete_stored_image, unique_filename, upload_image, upload_image_b64

router = APIRouter(
    prefix="/admin/products",
    tags=["admin"],
    dependencies=[Depends(get_current_admin), Depends(require_perm("products"))],
)

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
    """Parses a leading numeric prefix, 0.0 on anything else (never
    raises) — HTML `type=number` inputs already constrain the common
    case, this just handles whatever else comes through."""
    s = (raw or "").strip() if isinstance(raw, str) else raw
    if not s:
        return 0.0
    m = _FLOAT_RE.match(str(s))
    return float(m.group(0)) if m else 0.0


def _has_photo(image: str | None) -> bool:
    """A remote (Supabase) URL, or a local file that still exists."""
    if not image or "default.jpg" in image:
        return False
    if image.startswith("http"):
        return True
    return (PROJECT_ROOT / image).exists()


def _parse_category(raw: str) -> ProductCategory:
    try:
        cat = ProductCategory(raw)
    except ValueError:
        cat = None
    if cat not in ALLOWED:
        raise not_found("Невідома категорія.")
    return cat


def _scoop_diffs(raw: str | None) -> tuple[float | None, float | None]:
    try:
        opts = json.loads(raw or "")["options"]
        return float(opts[1]["price_diff"]), float(opts[2]["price_diff"])
    except (ValueError, KeyError, IndexError, TypeError):
        return None, None


def _product_out(row, cat: ProductCategory, sold: int = 0) -> dict:
    has_photo = _has_photo(row.image)
    diff2 = diff3 = None
    if cat == ProductCategory.ICE_CREAM:
        diff2, diff3 = _scoop_diffs(row.variant_options)
    return {
        "id": row.id, "category": cat.value, "category_label": CATEGORY_NAMES[cat],
        "name": row.name or "", "description": row.description or "",
        "price": float(row.price_per_kg if cat == ProductCategory.CAKE else row.price or 0),
        "image": item_img(row.image) if has_photo else "", "has_photo": has_photo, "sold": sold,
        "variant_options": getattr(row, "variant_options", None),
        "pieces_count": getattr(row, "pieces_count", None),
        "price_per_kg": float(row.price_per_kg) if cat == ProductCategory.CAKE else None,
        "min_weight": float(row.min_weight) if cat == ProductCategory.CAKE else None,
        "scoop_diff_2": diff2, "scoop_diff_3": diff3,
    }


def _variant_options_json(diff2: str, diff3: str) -> str:
    return json.dumps({
        "type": "scoops", "label": "Кількість кульок",
        "options": [
            {"id": "1", "label": "1 кулька", "price_diff": 0},
            {"id": "2", "label": "2 кульки", "price_diff": _floatval(diff2)},
            {"id": "3", "label": "3 кульки", "price_diff": _floatval(diff3)},
        ],
    }, ensure_ascii=False)


async def _store_image(category: ProductCategory, image_b64: str, upload: UploadFile | None) -> str:
    """Save a new photo; returns its stored path/URL, '' when none was sent.
    Raises a 400 on a bad file."""
    subfolder = CATEGORY_FOLDERS.get(category, "other")
    upload_dir = PROJECT_ROOT / "static" / "images" / "menu_items" / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    remote_base = f"menu_items/{subfolder}"

    if image_b64:
        fname = unique_filename()
        saved = upload_image_b64(image_b64, upload_dir / fname, f"{remote_base}/{fname}")
        if not saved:
            raise bad_request("Помилка збереження зображення.")
        return saved if saved.startswith("http") else f"static/images/menu_items/{subfolder}/{saved}"

    if upload is not None and upload.filename:
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if ext not in ALLOWED_EXT:
            raise bad_request("Дозволені формати: JPG, PNG, WebP, GIF.")
        file_name = f"{unique_filename()}.{ext}"
        mime = "image/png" if ext == "png" else ("image/webp" if ext == "webp" else "image/jpeg")
        saved = upload_image(await upload.read(), upload_dir / file_name, f"{remote_base}/{file_name}", mime)
        if not saved:
            raise bad_request("Не вдалося зберегти зображення.")
        return saved if saved.startswith("http") else f"static/images/menu_items/{subfolder}/{file_name}"
    return ""


def _sales(db: Session, cat: ProductCategory) -> dict[int, int]:
    rows = db.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity)).where(OrderItem.category == cat.value).group_by(OrderItem.product_id)
    ).all()
    return {int(pid): int(qty) for pid, qty in rows}


@router.get("", response_model=AdminProductsPage)
def list_products(category: str = "all", db: Session = Depends(get_db)):
    is_all = category == "all"
    cat_enum = None if is_all else _parse_category(category)

    products = []
    for cat in (ALLOWED if is_all else [cat_enum]):
        model = CATEGORY_MODEL_MAP[cat]
        sales = _sales(db, cat)
        for row in db.execute(select(model).order_by(model.id.desc())).scalars().all():
            products.append(_product_out(row, cat, sales.get(row.id, 0)))
    if is_all:
        products.sort(key=lambda p: p["name"])

    counts = []
    for cat in ALLOWED:
        model = CATEGORY_MODEL_MAP[cat]
        counts.append({"key": cat.value, "label": CATEGORY_NAMES[cat], "count": db.execute(select(func.count()).select_from(model)).scalar_one()})

    return {
        "is_all": is_all, "category": cat_enum.value if cat_enum else "all",
        "title": "Всі товари" if is_all else CATEGORY_NAMES[cat_enum],
        "categories": counts, "total_count": sum(c["count"] for c in counts), "products": products,
    }


@router.get("/{category}/{item_id}", response_model=AdminProduct)
def get_product(category: str, item_id: int, db: Session = Depends(get_db)):
    cat = _parse_category(category)
    row = db.get(CATEGORY_MODEL_MAP[cat], item_id)
    if row is None:
        raise not_found("Товар не знайдено.")
    return _product_out(row, cat, _sales(db, cat).get(row.id, 0))


@router.post("/{category}", response_model=ProductSaved, status_code=201)
async def create_product(
    category: str,
    name: str = Form(""), description: str = Form(""), price: str = Form(""),
    price_per_kg: str = Form(""), min_weight: str = Form(""),
    scoop_diff_2: str = Form(""), scoop_diff_3: str = Form(""), pieces_count: str = Form(""),
    image_b64: str = Form(""), image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    cat = _parse_category(category)
    name, description = name.strip(), description.strip()
    is_cake = cat == ProductCategory.CAKE
    price_value, per_kg = _floatval(price), _floatval(price_per_kg)
    weight = _floatval(min_weight) or 1.0

    errors = []
    if not name:
        errors.append("Введіть назву товару.")
    if is_cake and per_kg <= 0:
        errors.append("Ціна за кг має бути більша за 0.")
    if not is_cake and price_value <= 0:
        errors.append("Ціна має бути більша за 0.")
    if not image_b64 and not (image is not None and image.filename):
        errors.append("Оберіть зображення для завантаження.")
    if errors:
        raise bad_request(errors[0], code="validation", errors=errors)

    image_path = await _store_image(cat, image_b64, image)
    model = CATEGORY_MODEL_MAP[cat]
    if is_cake:
        row = model(name=name, description=description, price_per_kg=per_kg, price=per_kg, min_weight=weight, image=image_path)
    elif cat == ProductCategory.ICE_CREAM:
        row = model(name=name, description=description, price=price_value, variant_options=_variant_options_json(scoop_diff_2, scoop_diff_3), image=image_path)
    elif cat == ProductCategory.SUSHI_SET:
        row = model(name=name, description=description, price=price_value, pieces_count=max(0, int(_floatval(pieces_count))), image=image_path)
    else:
        row = model(name=name, description=description, price=price_value, image=image_path)
    db.add(row)
    db.commit()
    return {"product": _product_out(row, cat)}


@router.post("/{category}/{item_id}", response_model=ProductSaved)
async def update_product(
    category: str, item_id: int,
    name: str = Form(""), description: str = Form(""), price: str = Form(""),
    price_per_kg: str = Form(""), min_weight: str = Form(""),
    scoop_diff_2: str = Form(""), scoop_diff_3: str = Form(""), pieces_count: str = Form(""),
    image_b64: str = Form(""), image: UploadFile | None = File(None), remove_image: str = Form(""),
    db: Session = Depends(get_db),
):
    """Multipart update (POST, since browsers' FormData uploads are POST).
    Cakes are priced per kg: `price_per_kg`/`min_weight` apply to them."""
    cat = _parse_category(category)
    row = db.get(CATEGORY_MODEL_MAP[cat], item_id)
    if row is None:
        raise not_found("Товар не знайдено.")

    is_cake = cat == ProductCategory.CAKE
    name = name.strip()
    price_value = _floatval(price_per_kg) if is_cake and price_per_kg else _floatval(price)
    errors = []
    if not name:
        errors.append("Введіть назву товару.")
    if price_value <= 0:
        errors.append("Ціна має бути більша за 0.")
    if errors:
        raise bad_request(errors[0], code="validation", errors=errors)

    has_new = bool(image_b64) or (image is not None and bool(image.filename))
    if has_new:
        new_path = await _store_image(cat, image_b64, image)
        delete_stored_image(row.image, PROJECT_ROOT)
        row.image = new_path
    elif remove_image == "1":
        delete_stored_image(row.image, PROJECT_ROOT)
        row.image = ""

    row.name = name
    row.description = description.strip()
    row.price = price_value
    if is_cake:
        row.price_per_kg = price_value
        if min_weight:
            row.min_weight = _floatval(min_weight) or 1.0
    elif cat == ProductCategory.ICE_CREAM:
        row.variant_options = _variant_options_json(scoop_diff_2, scoop_diff_3)
    elif cat == ProductCategory.SUSHI_SET and pieces_count != "":
        row.pieces_count = max(0, int(_floatval(pieces_count)))
    db.commit()
    return {"product": _product_out(row, cat, _sales(db, cat).get(row.id, 0))}


@router.delete("/{category}/{item_id}", response_model=SuccessResponse)
def delete_product(category: str, item_id: int, db: Session = Depends(get_db)):
    cat = _parse_category(category)
    row = db.get(CATEGORY_MODEL_MAP[cat], item_id)
    if row is None:
        return {"success": True}
    image_path = row.image
    db.delete(row)
    db.commit()
    delete_stored_image(image_path, PROJECT_ROOT)
    return {"success": True}
