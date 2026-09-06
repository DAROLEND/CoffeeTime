"""Port of includes/reminders.php's schedule_reminders() (order-creation
time) and cron/send_reminders.php's per-row send logic (the actual cron
job — see cron/send_reminders.py, a thin wrapper around
process_due_reminders() below)."""
from __future__ import annotations

import datetime
import re
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.orders import Order, OrderReminder, ReminderStatus, ReminderType
from app.services.mail import send_html_email
from app.services.telegram import send_telegram

KYIV_TZ = ZoneInfo("Europe/Kyiv")
_READY_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def schedule_reminders(db: Session, order_id: int, ready_time: str, customer_email: str | None) -> None:
    if not _READY_TIME_RE.match(ready_time):
        return

    now = datetime.datetime.now(KYIV_TZ)
    pickup = datetime.datetime.strptime(ready_time + ":00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=KYIV_TZ)

    diff_seconds = (pickup - now).total_seconds()
    if diff_seconds <= 0:
        return

    diff_hours = diff_seconds / 3600
    diff_days = diff_seconds / 86400

    reminders: list[tuple[str, datetime.datetime]] = []

    # 2h before — skip if pickup is before 09:00 to avoid early-morning noise
    if diff_hours >= 3:
        two_hour_before = pickup - datetime.timedelta(hours=2)
        if pickup.hour >= 9:
            reminders.append((ReminderType.TELEGRAM_ADMIN, two_hour_before))
            if customer_email:
                reminders.append((ReminderType.EMAIL_CUSTOMER, two_hour_before))

    if diff_days >= 1:
        evening_before = (pickup - datetime.timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0)
        if evening_before > now:
            reminders.append((ReminderType.TELEGRAM_ADMIN, evening_before))
            if customer_email:
                reminders.append((ReminderType.EMAIL_CUSTOMER, evening_before))

    if diff_days >= 2:
        evening_two_before = (pickup - datetime.timedelta(days=2)).replace(hour=19, minute=0, second=0, microsecond=0)
        if evening_two_before > now:
            reminders.append((ReminderType.TELEGRAM_ADMIN, evening_two_before))
            if customer_email:
                reminders.append((ReminderType.EMAIL_CUSTOMER, evening_two_before))

    if not reminders:
        return

    for reminder_type, send_at in reminders:
        db.add(OrderReminder(order_id=order_id, type=reminder_type, send_at=send_at.replace(tzinfo=None)))
    db.commit()


# ── cron/send_reminders.php's sending logic ──────────────────────────────────


def format_pickup(ready_time: str | None) -> str:
    """Port of format_pickup(): 'сьогодні о HH:MM' / 'завтра о HH:MM' /
    'DD.MM.YYYY о HH:MM', falling back to the raw string for the old
    bare-"HH:MM" ready_time format."""
    if not ready_time or not _READY_TIME_RE.match(ready_time):
        return ready_time or ""
    dt = datetime.datetime.strptime(ready_time + ":00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=KYIV_TZ)
    now = datetime.datetime.now(KYIV_TZ)
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)
    t = dt.strftime("%H:%M")
    if dt.date() == today:
        return f"сьогодні о {t}"
    if dt.date() == tomorrow:
        return f"завтра о {t}"
    return f"{dt.strftime('%d.%m.%Y')} о {t}"


def _email_template(name: str, headline: str, body: str, order_id: int, pickup: str) -> str:
    """Port of send_reminders.php's email_template() (also duplicated,
    unported, in the throwaway cron/preview_email.php dev tool)."""
    settings = get_settings()
    phone = settings.CAFE_PHONE
    instagram = settings.CAFE_INSTAGRAM
    from_name = settings.MAIL_FROM_NAME or "Coffee Time"

    contact_line = ""
    if phone:
        contact_line += f'<a href="tel:{phone}" style="color:#b07840;text-decoration:none;">{phone}</a>'
    if instagram:
        if contact_line:
            contact_line += " &nbsp;·&nbsp; "
        contact_line += f'<a href="{instagram}" style="color:#b07840;text-decoration:none;">Instagram</a>'
    footer_text = f"Маєте питання? {contact_line} ☕" if contact_line else "Маєте питання? Відповімо на будь-який запит ☕"

    return f"""<!DOCTYPE html>
<html lang="uk">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#faf7f2;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#faf7f2;padding:32px 16px;">
  <tr><td align="center">
    <table width="100%" style="max-width:520px;background:#fff;border-radius:16px;border:1px solid #f0e8df;overflow:hidden;">
      <tr><td style="background:#FFC107;padding:24px 32px;text-align:center;">
        <p style="margin:0;font-size:28px;">☕</p>
        <p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#5a2d00;">{from_name}</p>
      </td></tr>
      <tr><td style="padding:32px;">
        <p style="margin:0 0 8px;font-size:22px;font-weight:700;color:#2c1810;">{headline}</p>
        <p style="margin:0 0 20px;font-size:15px;color:#666;line-height:1.6;">Привіт, {name}! {body}</p>
        <table cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
          <tr><td style="background:#fff8e1;border:1px solid #ffe082;border-radius:50px;padding:10px 28px;
                         font-size:15px;font-weight:700;color:#8B4513;white-space:nowrap;">
            ⏰ {pickup}
          </td></tr>
        </table>
        <p style="margin:0;font-size:13px;color:#aaa;text-align:center;">Замовлення №{order_id}</p>
      </td></tr>
      <tr><td style="padding:16px 32px;border-top:1px solid #f0e8df;text-align:center;">
        <p style="margin:0;font-size:12px;color:#bbb;">{footer_text}</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def send_reminder_telegram(order: Order) -> bool:
    name = f"{order.customer_name or ''} {order.customer_surname or ''}".strip()
    phone = order.phone or ""
    pickup = format_pickup(order.ready_time)
    total = f"{float(order.total):.2f} ₴"

    hours_left = None
    if order.ready_time and _READY_TIME_RE.match(order.ready_time):
        pickup_dt = datetime.datetime.strptime(order.ready_time + ":00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=KYIV_TZ)
        now = datetime.datetime.now(KYIV_TZ)
        # PHP: $diff->days*24 + $diff->h, from $pickupDt->diff($now) — a
        # non-negative, whole-hours difference regardless of which side
        # is earlier, unlike the plain (signed, fractional) subtraction
        # in send_reminder_email() below. Preserved as-is (an existing
        # PHP asymmetry between the two functions, not a bug to fix).
        hours_left = int(abs((pickup_dt - now).total_seconds()) // 3600)

    if hours_left is not None and hours_left <= 3:
        urgency = "\U0001f534 <b>Скоро!</b> Починайте готувати"
    elif hours_left is not None and hours_left <= 6:
        urgency = "\U0001f7e1 Нагадування — сьогодні"
    else:
        urgency = "\U0001f514 Нагадування — завтра"

    msg = (
        f"{urgency}\n\n"
        f"\U0001f4e6 Замовлення <b>#{order.order_id}</b>\n"
        f"\U0001f464 {name}\n"
        f'\U0001f4de <a href="tel:{phone}">{phone}</a>\n'
        f"⏰ Готовність: <b>{pickup}</b>\n"
        f"\U0001f4b0 Сума: {total}"
    )
    return send_telegram(msg)


def send_reminder_email(order: Order) -> bool:
    if not order.customer_email:
        return False

    pickup = format_pickup(order.ready_time)
    name = order.customer_name or ""
    order_id = order.order_id

    hours_left = None
    if order.ready_time and _READY_TIME_RE.match(order.ready_time):
        pickup_dt = datetime.datetime.strptime(order.ready_time + ":00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=KYIV_TZ)
        now = datetime.datetime.now(KYIV_TZ)
        hours_left = (pickup_dt - now).total_seconds() / 3600

    if hours_left is not None and hours_left <= 3:
        subject = f"☕ Ваше замовлення №{order_id} готується — до зустрічі!"
        headline = "Зовсім скоро!"
        body = f"Ваше замовлення вже готується. Чекаємо вас о <strong>{pickup}</strong> \U0001f389"
    else:
        subject = f"⏰ Нагадування про замовлення №{order_id} в Coffee Time"
        headline = "Нагадуємо про ваше замовлення"
        body = (
            f"Не забудьте — ваше замовлення заплановано на <strong>{pickup}</strong>.<br>"
            "Ми почнемо готувати заздалегідь, щоб усе було свіжим саме до вашого приходу."
        )

    html_body = _email_template(name, headline, body, order_id, pickup)
    alt_body = body.replace("<br>", "\n").replace("<strong>", "").replace("</strong>", "")
    return send_html_email(order.customer_email, subject, html_body, alt_body)


def process_due_reminders(db: Session, limit: int = 50) -> list[dict]:
    """Port of send_reminders.php's main loop: fetch pending reminders due
    now, send each (Telegram to admin, or email to customer), and record
    the outcome. Returns a per-reminder result list for the cron script
    to print (and for tests to assert against)."""
    now = datetime.datetime.now(KYIV_TZ).replace(tzinfo=None)
    rows = db.execute(
        select(OrderReminder, Order)
        .join(Order, Order.order_id == OrderReminder.order_id)
        .where(OrderReminder.status == ReminderStatus.PENDING, OrderReminder.send_at <= now)
        .order_by(OrderReminder.send_at)
        .limit(limit)
    ).all()

    results = []
    for reminder, order in rows:
        success = False
        fail_reason = None
        try:
            if reminder.type == ReminderType.TELEGRAM_ADMIN:
                success = send_reminder_telegram(order)
            else:
                success = send_reminder_email(order)
        except Exception as exc:  # noqa: BLE001 — mirrors PHP's catch (Throwable $e)
            fail_reason = str(exc)[:255]

        reminder.status = ReminderStatus.SENT if success else ReminderStatus.FAILED
        reminder.sent_at = datetime.datetime.now(KYIV_TZ).replace(tzinfo=None)
        reminder.fail_reason = fail_reason
        db.commit()

        results.append({
            "id": reminder.id, "order_id": order.order_id,
            "type": reminder.type.value if hasattr(reminder.type, "value") else reminder.type,
            "status": reminder.status.value if hasattr(reminder.status, "value") else reminder.status,
        })

    return results
