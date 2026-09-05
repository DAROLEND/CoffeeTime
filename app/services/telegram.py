"""Port of includes/telegram.php: send_telegram(), notify_new_order(),
notify_order_from_db()."""
from __future__ import annotations

from html import escape

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory
from app.models.orders import Order, OrderItem


def send_telegram(message: str, parse_mode: str = "HTML") -> bool:
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = httpx.post(
            url,
            data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message, "parse_mode": parse_mode},
            timeout=httpx.Timeout(5.0, connect=3.0),
        )
        data = resp.json()
    except Exception:
        return False
    return bool(data.get("ok"))


def notify_new_order(
    order_id: int, first_name: str, last_name: str, phone: str,
    ready_time: str, payment: str, total: float, items: list[dict],
) -> None:
    pay_label = "💳 Картка (онлайн)" if payment == "card_online" else "💵 Готівка"

    item_lines = ""
    for it in items:
        item_lines += "  • {} × {} — {} ₴\n".format(
            escape(it["name"]), int(it["quantity"]),
            f"{float(it['price']) * int(it['quantity']):,.0f}".replace(",", " "),
        )

    message = (
        f"🛍 <b>Нове замовлення #{order_id}</b>\n\n"
        f"👤 <b>{escape(first_name)} {escape(last_name)}</b>\n"
        f"📞 {escape(phone)}\n"
        f"🕐 Час готовності: <b>{escape(ready_time)}</b>\n"
        f"💳 Оплата: {pay_label}\n\n"
        f"📋 <b>Товари:</b>\n{item_lines}\n"
        "💰 <b>Сума: {} ₴</b>".format(f"{total:,.0f}".replace(",", " "))
    )
    send_telegram(message)


def notify_order_from_db(db: Session, order_id: int) -> None:
    """Used by liqpay_callback.php after a confirmed card payment (and by
    the dev-bypass path when the real webhook can't reach localhost)."""
    order = db.get(Order, order_id)
    if not order:
        return

    rows = db.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
    items = []
    for row in rows:
        name = "—"
        try:
            category = ProductCategory(row.category)
            model = CATEGORY_MODEL_MAP[category]
            product = db.get(model, row.product_id)
            if product:
                name = product.name
        except ValueError:
            pass
        items.append({"name": name, "quantity": row.quantity, "price": float(row.price)})

    notify_new_order(
        order_id, order.customer_name or "", order.customer_surname or "",
        order.phone or "", order.ready_time or "", order.payment_method or "",
        float(order.total), items,
    )
