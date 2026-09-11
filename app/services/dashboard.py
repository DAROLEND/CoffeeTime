"""Port of admin/dashboard.php's data-prep logic (the staff-home stats,
the full-dashboard stats/chart data/recent-orders/top-products)."""
from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.models.catalog import Sauce
from app.models.cms import Gallery, HeroSlide, SiteReview, SiteSetting
from app.models.orders import Order, OrderItem
from app.services.permissions import has_perm, is_super

CAT_MAP = {
    "coffee_items": "Кава", "fast_food_items": "Фаст-фуд", "pizza_items": "Піца",
    "mini_pizza_items": "Міні-піца", "cold_drink_items": "Холодні напої",
    "ice_cream_items": "Морозиво", "dessert_items": "Десерти", "sushi_items": "Суші",
    "sushi_sets": "Сети суші", "salad_items": "Салати", "cake_items": "Торти на замовлення",
}

STATUS_INFO = {
    "new": ("Нове", "badge-new"), "processing": ("В обробці", "badge-processing"),
    "ready": ("Готово", "badge-ready"), "done": ("Виконано", "badge-done"),
    "cancelled": ("Скасовано", "badge-cancelled"),
}


def status_info(s: str) -> tuple[str, str]:
    return STATUS_INFO.get(s, STATUS_INFO["new"])


def payment_badge(order: dict) -> tuple[str, str, str]:
    """Returns (css_class, icon_name, label) for paymentBadge()."""
    ps, pm = order.get("payment_status") or "", order.get("payment_method") or ""
    if ps == "paid":
        return "pay-paid", "paid-card", "Оплачено"
    if "cash" in pm:
        return "pay-cash", "paid-cash", "Готівка"
    return "pay-unpaid", "paid-pending", "Не оплачено"


def stat_compare(today: float, yesterday: float, suffix: str = "") -> dict:
    diff = today - yesterday
    if diff > 0:
        return {"direction": "up", "text": f"↑ +{diff:,.0f}".replace(",", " ") + f"{suffix} від вчора"}
    if diff < 0:
        return {"direction": "down", "text": f"↓ {diff:,.0f}".replace(",", " ") + f"{suffix} від вчора"}
    return {"direction": "eq", "text": "= як вчора"}


def get_staff_home_stats(db: Session, request) -> tuple[dict, dict]:
    staff_stats: dict = {}
    cat_counts: dict = {}

    if has_perm(request, "products"):
        total = 0
        for tbl, label in CAT_MAP.items():
            model = CATEGORY_MODEL_MAP[ProductCategory(tbl)]
            cnt = db.execute(select(func.count()).select_from(model)).scalar_one()
            total += cnt
            cat_counts[tbl] = {"label": label, "count": cnt}
        staff_stats["products_total"] = total
        staff_stats["sauces_total"] = db.execute(select(func.count()).select_from(Sauce)).scalar_one()

    if has_perm(request, "reviews"):
        staff_stats["reviews_total"] = db.execute(select(func.count()).select_from(SiteReview)).scalar_one()
        staff_stats["reviews_week"] = db.execute(
            select(func.count()).select_from(SiteReview).where(SiteReview.created_at > datetime.datetime.utcnow() - datetime.timedelta(days=7))
        ).scalar_one()

    if has_perm(request, "content"):
        rows = db.execute(select(Gallery.category, func.count()).group_by(Gallery.category)).all()
        gallery_cats = {r[0].value if hasattr(r[0], "value") else r[0]: r[1] for r in rows}
        staff_stats["gallery_total"] = sum(gallery_cats.values())
        staff_stats["gallery_cats"] = gallery_cats

        slides_total = db.execute(select(func.count()).select_from(HeroSlide)).scalar_one()
        # COUNT(*) WHERE active, not SUM(active): Postgres has no sum(boolean)
        # (MySQL summed the old TINYINT(1) column). NULL active stays uncounted
        # either way.
        slides_active = db.execute(
            select(func.count()).select_from(HeroSlide).where(HeroSlide.active.is_(True))
        ).scalar_one()
        staff_stats["slides_total"] = slides_total
        staff_stats["slides_active"] = int(slides_active or 0)

        settings_rows = db.execute(
            select(SiteSetting).where(SiteSetting.key.in_(["about_title", "about_photo", "about_text"]))
        ).scalars().all()
        for row in settings_rows:
            staff_stats["about_" + row.key.replace("about_", "")] = row.value

    return staff_stats, cat_counts


def get_full_dashboard_stats(db: Session) -> dict:
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    def orders_count_sum(day: datetime.date) -> tuple[int, float]:
        row = db.execute(
            select(func.count(), func.coalesce(func.sum(Order.total), 0))
            .where(func.date(Order.created_at) == day)
        ).first()
        return int(row[0] or 0), float(row[1] or 0)

    today_orders, today_revenue = orders_count_sum(today)
    yest_orders, yest_revenue = orders_count_sum(yesterday)

    today_clients = db.execute(
        select(func.count(func.distinct(Order.user_id))).where(func.date(Order.created_at) == today, Order.user_id.isnot(None))
    ).scalar_one()
    yest_clients = db.execute(
        select(func.count(func.distinct(Order.user_id))).where(func.date(Order.created_at) == yesterday, Order.user_id.isnot(None))
    ).scalar_one()

    now = datetime.datetime.utcnow()
    week_reviews = db.execute(select(func.count()).select_from(SiteReview).where(SiteReview.created_at > now - datetime.timedelta(days=7))).scalar_one()
    prev_reviews = db.execute(
        select(func.count()).select_from(SiteReview).where(SiteReview.created_at.between(now - datetime.timedelta(days=14), now - datetime.timedelta(days=7)))
    ).scalar_one()

    total_clients = db.execute(select(func.count(func.distinct(Order.user_id))).where(Order.user_id.isnot(None))).scalar_one()

    avg_check = round(today_revenue / today_orders) if today_orders > 0 else 0
    avg_check_yest = round(yest_revenue / yest_orders) if yest_orders > 0 else 0

    hours_data = [0] * 24
    for h, c in db.execute(select(func.extract("hour", Order.created_at), func.count()).where(func.date(Order.created_at) == today).group_by(func.extract("hour", Order.created_at))).all():
        hours_data[int(h)] = c

    def daily_series(days: int) -> tuple[list[int], list[str]]:
        cutoff = today - datetime.timedelta(days=days - 1)
        raw = dict(db.execute(
            select(func.date(Order.created_at), func.count()).where(Order.created_at >= cutoff).group_by(func.date(Order.created_at))
        ).all())
        raw = {(d if isinstance(d, datetime.date) else datetime.date.fromisoformat(str(d))): c for d, c in raw.items()}
        values, labels = [], []
        for i in range(days - 1, -1, -1):
            day = today - datetime.timedelta(days=i)
            values.append(raw.get(day, 0))
            labels.append(day.strftime("%d.%m"))
        return values, labels

    week_data, week_labels = daily_series(7)
    month_data, month_labels = daily_series(30)

    recent_rows = db.execute(
        select(Order, func.count(OrderItem.id).label("items_count"))
        .outerjoin(OrderItem, OrderItem.order_id == Order.order_id)
        .group_by(Order.order_id).order_by(Order.created_at.desc()).limit(10)
    ).all()
    recent_orders = []
    for row in recent_rows:
        o = row.Order
        recent_orders.append({
            "order_id": o.order_id,
            "full_name": f"{o.customer_name or ''} {o.customer_surname or ''}".strip() or "—",
            "phone": o.phone or "—", "total": float(o.total),
            "status": o.status.value if hasattr(o.status, "value") else o.status,
            "payment_status": o.payment_status.value if hasattr(o.payment_status, "value") else o.payment_status,
            "payment_method": o.payment_method, "created_at": o.created_at,
        })

    top_products = _get_top_products(db, None, None)

    return {
        "today_orders": today_orders, "today_revenue": today_revenue,
        "yest_orders": yest_orders, "yest_revenue": yest_revenue,
        "today_clients": today_clients, "yest_clients": yest_clients,
        "week_reviews": week_reviews, "prev_reviews": prev_reviews,
        "total_clients": total_clients, "avg_check": avg_check, "avg_check_yest": avg_check_yest,
        "hours_data": hours_data, "week_data": week_data, "week_labels": week_labels,
        "month_data": month_data, "month_labels": month_labels,
        "recent_orders": recent_orders, "top_products": top_products,
    }


_TOP_PRODUCTS_CATEGORIES = {
    "coffee_items", "fast_food_items", "pizza_items", "mini_pizza_items", "cold_drink_items",
    "dessert_items", "sushi_items", "sushi_sets", "salad_items", "cake_items", "ice_cream_items",
}


def _get_top_products(db: Session, date_from: datetime.date | None, date_to: datetime.date | None, limit: int = 5) -> list[dict]:
    stmt = (
        select(
            OrderItem.product_id, OrderItem.category,
            func.sum(OrderItem.quantity).label("sold"),
            func.count(func.distinct(OrderItem.order_id)).label("orders_count"),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label("total_revenue"),
            func.round(func.avg(OrderItem.price), 0).label("avg_unit_price"),
        )
        .group_by(OrderItem.product_id, OrderItem.category)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )
    if date_from and date_to:
        stmt = stmt.join(Order, Order.order_id == OrderItem.order_id).where(func.date(Order.created_at).between(date_from, date_to))

    rows = db.execute(stmt).all()
    products = []
    for row in rows:
        if row.category not in _TOP_PRODUCTS_CATEGORIES:
            continue
        model = CATEGORY_MODEL_MAP[ProductCategory(row.category)]
        product = db.get(model, row.product_id)
        deleted = product is None
        name = product.name if product else "Видалений товар"
        raw_img = (product.image if product else "") or ""
        image = "" if (not raw_img or raw_img == "static/images/menu_items/default.jpg") else raw_img
        products.append({
            "name": name, "image": image, "deleted": deleted,
            "sold": int(row.sold or 0), "orders_count": int(row.orders_count or 0),
            "total_revenue": float(row.total_revenue or 0),
            "unit_price": f"{float(row.avg_unit_price or 0):,.0f}".replace(",", " "),
        })
    return products


def get_top_products_for_period(db: Session, period: str, date_from: str | None, date_to: str | None) -> list[dict]:
    today = datetime.date.today()
    if period == "week":
        return _get_top_products(db, today - datetime.timedelta(days=6), today)
    if period == "month":
        return _get_top_products(db, today - datetime.timedelta(days=29), today)
    if period == "custom" and date_from and date_to:
        return _get_top_products(db, datetime.date.fromisoformat(date_from), datetime.date.fromisoformat(date_to))
    return _get_top_products(db, None, None)


def get_chart_data_for_date(db: Session, date: datetime.date) -> list[int]:
    hours = [0] * 24
    for h, c in db.execute(
        select(func.extract("hour", Order.created_at), func.count()).where(func.date(Order.created_at) == date).group_by(func.extract("hour", Order.created_at))
    ).all():
        hours[int(h)] = c
    return hours
