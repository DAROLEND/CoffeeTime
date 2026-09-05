"""Port of the homepage's local helper functions from pages/index.php:
fetchPopularItems(), fetchTopOrderedItems(), reviewAvatarColor()."""
from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.models.orders import Order, OrderItem
from app.services.media import item_img

_AVATAR_MAP = {
    "А": "#8B4513", "Б": "#8B4513", "В": "#8B4513", "Г": "#8B4513", "Д": "#8B4513",
    "Е": "#d4a96a", "Є": "#d4a96a", "Ж": "#d4a96a", "З": "#d4a96a", "И": "#d4a96a",
    "І": "#d4a96a", "Ї": "#d4a96a", "Й": "#d4a96a", "К": "#d4a96a", "Л": "#d4a96a",
    "М": "#5a2d0c", "Н": "#5a2d0c", "О": "#5a2d0c", "П": "#5a2d0c", "Р": "#5a2d0c", "С": "#5a2d0c",
}


def review_avatar_color(name: str) -> str:
    ch = (name[:1] or "").upper()
    return _AVATAR_MAP.get(ch, "#c4956a")


def _row_to_dict(row) -> dict:
    return {
        "id": row.id, "name": row.name, "description": row.description,
        "image": item_img(row.image), "popularity": row.popularity, "price": float(row.price),
    }


def fetch_popular_items(db: Session, categories: list[ProductCategory], limit: int = 5) -> list[dict]:
    items: list[dict] = []
    for category in categories:
        model = CATEGORY_MODEL_MAP[category]
        rows = db.execute(
            select(model).order_by(model.popularity.desc()).limit(limit)
        ).scalars().all()
        for row in rows:
            d = _row_to_dict(row)
            d["table"] = category.value
            items.append(d)
    items.sort(key=lambda x: x["popularity"], reverse=True)
    return items[:limit]


def fetch_top_ordered_items(
    db: Session, categories: list[ProductCategory], limit: int = 3, days: int = 0
) -> list[dict]:
    if not categories:
        return []
    cat_values = [c.value for c in categories]

    stmt = (
        select(
            OrderItem.product_id,
            OrderItem.category,
            func.sum(OrderItem.quantity).label("total_ordered"),
        )
        .join(Order, OrderItem.order_id == Order.order_id)
        .where(OrderItem.category.in_(cat_values))
        .group_by(OrderItem.product_id, OrderItem.category)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )
    if days > 0:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        stmt = stmt.where(Order.created_at >= cutoff)

    rows = db.execute(stmt).all()

    items: list[dict] = []
    for row in rows:
        category = ProductCategory(row.category)
        model = CATEGORY_MODEL_MAP[category]
        product = db.get(model, row.product_id)
        if product:
            d = _row_to_dict(product)
            d["table"] = category.value
            items.append(d)

    if len(items) >= 3:
        return items

    popular = fetch_popular_items(db, categories, limit)
    existing_ids = {i["id"] for i in items}
    for p in popular:
        if p["id"] not in existing_ids:
            items.append(p)
        if len(items) >= limit:
            break
    return items
