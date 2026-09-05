"""Customer accounts, admin accounts, login rate-limiting, password resets."""
from __future__ import annotations

import datetime
import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminRole(str, enum.Enum):
    SUPER = "super"
    STAFF = "staff"


class User(Base):
    """Customer accounts (`users` table). Not to be confused with AdminUser."""

    __tablename__ = "users"

    client_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(60))
    # PHP schema had `varchar(30)` here — too short, truncates real emails
    # (already close to the limit for some seeded rows). Confirmed decision:
    # widen it; this fixes a latent bug without changing any current
    # behavior for existing data (every existing email already fits).
    email: Mapped[str] = mapped_column(String(255))
    # bcrypt hash, exactly 60 chars — PHP's `varchar(60)` fit this exactly,
    # kept as-is (passlib/bcrypt hashes are also 60 chars).
    password: Mapped[str] = mapped_column(String(60))
    client_name: Mapped[str | None] = mapped_column(String(255), default=None)
    client_surname: Mapped[str | None] = mapped_column(String(255), default=None)
    client_PhoneNumber: Mapped[str | None] = mapped_column(String(20), default=None)  # noqa: N815 (matches existing DB column name)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    role: Mapped[AdminRole] = mapped_column(
        SAEnum(AdminRole, values_callable=lambda e: [m.value for m in e]), default=AdminRole.STAFF
    )
    # JSON array of permission keys from all_perms(): orders_view, orders_edit,
    # products, content, reviews. Stored as text (not a JSON column type) to
    # match the existing column exactly; encode/decode explicitly in services.
    permissions: Mapped[str] = mapped_column(Text, default="[]")
    display_name: Mapped[str] = mapped_column(String(100), default="")


class LoginAttempt(Base):
    """Backs the 5-attempts/15-minutes IP lockout in forms/login.php."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(45))
    attempted_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255))
    token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
