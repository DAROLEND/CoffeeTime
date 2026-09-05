"""SMTP email sending — replaces PHPMailer usage in forms/forgot.php and
(later, Phase 9) cron/send_reminders.php. Same STARTTLS/env-driven config."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings


def send_html_email(to: str, subject: str, html_body: str, alt_body: str) -> bool:
    settings = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM or settings.MAIL_USERNAME}>"
    msg["To"] = to
    msg.attach(MIMEText(alt_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT, timeout=10) as server:
            server.starttls()
            if settings.MAIL_USERNAME:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_FROM or settings.MAIL_USERNAME, [to], msg.as_string())
        return True
    except Exception:
        return False
