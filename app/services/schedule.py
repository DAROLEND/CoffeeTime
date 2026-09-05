"""1:1 port of the schedule helpers in includes/helpers.php:
get_cafe_schedule(), get_next_available_time(), is_cafe_open_at().

Used by pages/checkout.php's time picker validation and (duplicated as
static markup in includes/footer.php — kept as a single source of truth
here) the footer's "Години роботи" listing.
"""
from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def get_cafe_schedule() -> dict[int, dict[str, str]]:
    """1=Mon ... 7=Sun (ISO weekday, matches PHP DateTime::format('N'))."""
    return {
        1: {"open": "08:00", "close": "20:00"},
        2: {"open": "08:00", "close": "20:00"},
        3: {"open": "08:00", "close": "20:00"},
        4: {"open": "08:00", "close": "20:00"},
        5: {"open": "08:00", "close": "20:00"},
        6: {"open": "10:00", "close": "20:00"},
        7: {"open": "12:00", "close": "20:00"},
    }


def _with_time(dt: datetime.datetime, hh: int, mm: int, ss: int = 0) -> datetime.datetime:
    return dt.replace(hour=hh, minute=mm, second=ss, microsecond=0)


def get_next_available_time(now: datetime.datetime | None = None) -> dict | None:
    schedule = get_cafe_schedule()
    now = now or datetime.datetime.now(KYIV_TZ)

    for i in range(8):
        check = now if i == 0 else _with_time(now + datetime.timedelta(days=i), 0, 0, 0)

        dow = check.isoweekday()
        day = schedule[dow]
        open_h, open_m = (int(x) for x in day["open"].split(":"))
        close_h, close_m = (int(x) for x in day["close"].split(":"))

        open_dt = _with_time(check, open_h, open_m)
        close_dt = _with_time(check, close_h, close_m)

        earliest = now + datetime.timedelta(minutes=15)
        rem = earliest.minute % 5
        if rem != 0:
            earliest = earliest + datetime.timedelta(minutes=(5 - rem))
        earliest = _with_time(earliest, earliest.hour, earliest.minute, 0)

        if i == 0:
            if now < close_dt and earliest < close_dt:
                t = open_dt if earliest < open_dt else earliest
                return {
                    "time": t.strftime("%H:%M"),
                    "date": "сьогодні",
                    "date_label": "",
                    "is_today": True,
                    "datetime": t,
                }
        else:
            return {
                "time": day["open"],
                "date": check.strftime("%d.%m"),
                "date_label": "завтра" if i == 1 else check.strftime("%d.%m"),
                "is_today": False,
                "datetime": open_dt,
            }

    return None


def is_cafe_open_at(dt: datetime.datetime) -> bool:
    schedule = get_cafe_schedule()
    dow = dt.isoweekday()
    if dow not in schedule:
        return False

    oh, om = (int(x) for x in schedule[dow]["open"].split(":"))
    ch, cm = (int(x) for x in schedule[dow]["close"].split(":"))

    open_dt = _with_time(dt, oh, om)
    close_dt = _with_time(dt, ch, cm)

    return open_dt <= dt < close_dt
