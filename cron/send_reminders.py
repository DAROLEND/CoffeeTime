#!/usr/bin/env python3
"""Coffee Time — Reminder cron job.

Run every 15 minutes, e.g. via crontab:
    */15 * * * * /path/to/venv/bin/python /path/to/coffee-time-fastapi/cron/send_reminders.py >> /tmp/ct_reminders.log 2>&1

Finds pending reminders with send_at <= now() and sends them (Telegram to
the admin, or email to the customer). All the actual logic lives in
app.services.reminders.process_due_reminders() — testable in isolation,
without shelling out to this script — this file is just the entry point
that wires up a DB session and prints progress."""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import SessionLocal  # noqa: E402
from app.services.reminders import process_due_reminders  # noqa: E402


def main() -> None:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = SessionLocal()
    try:
        results = process_due_reminders(db)
    finally:
        db.close()

    if not results:
        print(f"{now_str} — no reminders due")
        return

    print(f"{now_str} — processing {len(results)} reminder(s)")
    for r in results:
        print(f"  [{r['id']}] order #{r['order_id']} {r['type']} → {r['status']}")


if __name__ == "__main__":
    main()
