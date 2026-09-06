"""Phase 9 verification: cron/send_reminders.php's sending logic, ported
to app/services/reminders.py's process_due_reminders() (invoked by the
thin cron/send_reminders.py entry point)."""
from __future__ import annotations

import datetime

import app.services.reminders as reminders_module
from app.models.orders import Order, OrderReminder, ReminderStatus, ReminderType
from app.services.reminders import format_pickup, process_due_reminders

KYIV_TZ = reminders_module.KYIV_TZ


def _due_ready_time(hours_ahead: float) -> str:
    dt = datetime.datetime.now(KYIV_TZ) + datetime.timedelta(hours=hours_ahead)
    return dt.strftime("%Y-%m-%d %H:%M")


def _make_order(db_session, **kwargs) -> Order:
    defaults = dict(
        total=100, status="new", customer_name="Іван", customer_surname="Петренко",
        customer_email="ivan@example.com", phone="0991112233",
        ready_time=_due_ready_time(1), payment_method="cash_on_pickup", order_type="dine_in",
    )
    defaults.update(kwargs)
    order = Order(**defaults)
    db_session.add(order)
    db_session.flush()
    return order


def test_format_pickup_today_and_tomorrow():
    now = datetime.datetime.now(KYIV_TZ)
    today_str = now.strftime("%Y-%m-%d 18:00")
    tomorrow_str = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:30")

    assert format_pickup(today_str) == "сьогодні о 18:00"
    assert format_pickup(tomorrow_str) == "завтра о 09:30"


def test_format_pickup_falls_back_for_bad_format():
    assert format_pickup("18:00") == "18:00"
    assert format_pickup(None) == ""


def test_process_due_reminders_sends_telegram(db_session, monkeypatch):
    sent = {}
    monkeypatch.setattr(reminders_module, "send_telegram", lambda msg: sent.setdefault("msg", msg) or True)

    order = _make_order(db_session)
    db_session.add(OrderReminder(
        order_id=order.order_id, type=ReminderType.TELEGRAM_ADMIN,
        send_at=datetime.datetime.now(KYIV_TZ).replace(tzinfo=None) - datetime.timedelta(minutes=1),
    ))
    db_session.commit()

    results = process_due_reminders(db_session)
    assert len(results) == 1
    assert results[0]["status"] == "sent"
    assert f"#{order.order_id}" in sent["msg"]

    reminder = db_session.query(OrderReminder).filter_by(order_id=order.order_id).one()
    assert reminder.status.value == "sent"
    assert reminder.sent_at is not None


def test_process_due_reminders_sends_email(db_session, monkeypatch):
    sent = {}

    def _fake_send(to, subject, html_body, alt_body):
        sent.update(to=to, subject=subject)
        return True

    monkeypatch.setattr(reminders_module, "send_html_email", _fake_send)

    order = _make_order(db_session, customer_email="client@example.com")
    db_session.add(OrderReminder(
        order_id=order.order_id, type=ReminderType.EMAIL_CUSTOMER,
        send_at=datetime.datetime.now(KYIV_TZ).replace(tzinfo=None) - datetime.timedelta(minutes=1),
    ))
    db_session.commit()

    results = process_due_reminders(db_session)
    assert results[0]["status"] == "sent"
    assert sent["to"] == "client@example.com"
    assert str(order.order_id) in sent["subject"]


def test_process_due_reminders_marks_failed_on_exception(db_session, monkeypatch):
    def _boom(msg):
        raise RuntimeError("Telegram API down")

    monkeypatch.setattr(reminders_module, "send_telegram", _boom)

    order = _make_order(db_session)
    db_session.add(OrderReminder(
        order_id=order.order_id, type=ReminderType.TELEGRAM_ADMIN,
        send_at=datetime.datetime.now(KYIV_TZ).replace(tzinfo=None) - datetime.timedelta(minutes=1),
    ))
    db_session.commit()

    results = process_due_reminders(db_session)
    assert results[0]["status"] == "failed"

    reminder = db_session.query(OrderReminder).filter_by(order_id=order.order_id).one()
    assert reminder.status.value == "failed"
    assert "Telegram API down" in reminder.fail_reason


def test_process_due_reminders_ignores_not_yet_due(db_session, monkeypatch):
    monkeypatch.setattr(reminders_module, "send_telegram", lambda msg: True)

    order = _make_order(db_session)
    db_session.add(OrderReminder(
        order_id=order.order_id, type=ReminderType.TELEGRAM_ADMIN,
        send_at=datetime.datetime.now(KYIV_TZ).replace(tzinfo=None) + datetime.timedelta(hours=1),
    ))
    db_session.commit()

    assert process_due_reminders(db_session) == []


def test_process_due_reminders_ignores_already_sent(db_session, monkeypatch):
    monkeypatch.setattr(reminders_module, "send_telegram", lambda msg: True)

    order = _make_order(db_session)
    db_session.add(OrderReminder(
        order_id=order.order_id, type=ReminderType.TELEGRAM_ADMIN,
        send_at=datetime.datetime.now(KYIV_TZ).replace(tzinfo=None) - datetime.timedelta(minutes=1),
        status=ReminderStatus.SENT,
    ))
    db_session.commit()

    assert process_due_reminders(db_session) == []


def test_cron_script_prints_no_reminders_due(monkeypatch, capsys):
    import cron.send_reminders as cron_script

    monkeypatch.setattr(cron_script, "process_due_reminders", lambda db: [])
    monkeypatch.setattr(cron_script, "SessionLocal", lambda: _FakeSession())

    cron_script.main()
    out = capsys.readouterr().out
    assert "no reminders due" in out


def test_cron_script_prints_processed_reminders(monkeypatch, capsys):
    import cron.send_reminders as cron_script

    fake_results = [{"id": 1, "order_id": 42, "type": "telegram_admin", "status": "sent"}]
    monkeypatch.setattr(cron_script, "process_due_reminders", lambda db: fake_results)
    monkeypatch.setattr(cron_script, "SessionLocal", lambda: _FakeSession())

    cron_script.main()
    out = capsys.readouterr().out
    assert "processing 1 reminder(s)" in out
    assert "[1] order #42 telegram_admin → sent" in out


class _FakeSession:
    def close(self):
        pass


def test_email_reminder_skipped_without_customer_email(db_session, monkeypatch):
    called = []
    monkeypatch.setattr(reminders_module, "send_html_email", lambda *a, **k: called.append(1) or True)

    order = _make_order(db_session, customer_email=None)
    db_session.add(OrderReminder(
        order_id=order.order_id, type=ReminderType.EMAIL_CUSTOMER,
        send_at=datetime.datetime.now(KYIV_TZ).replace(tzinfo=None) - datetime.timedelta(minutes=1),
    ))
    db_session.commit()

    results = process_due_reminders(db_session)
    assert results[0]["status"] == "failed"
    assert not called
