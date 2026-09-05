"""Port of includes/reminders.php's schedule_reminders()."""
from __future__ import annotations

import datetime
import re
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.orders import OrderReminder, ReminderType

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
