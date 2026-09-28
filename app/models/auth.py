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
    email: Mapped[str] = mapped_column(String(255))
    # bcrypt hashes are always exactly 60 chars.
    password: Mapped[str] = mapped_column(String(60))
    client_name: Mapped[str | None] = mapped_column(String(255), default=None)
    client_surname: Mapped[str | None] = mapped_column(String(255), default=None)
    client_PhoneNumber: Mapped[str | None] = mapped_column(String(20), default=None)  # noqa: N815
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    role: Mapped[AdminRole] = mapped_column(
        SAEnum(AdminRole, name="admin_role", values_callable=lambda e: [m.value for m in e]), default=AdminRole.STAFF
    )
    # JSON array of permission keys: orders_view, orders_edit, products,
    # content, reviews. Stored as text; encode/decode explicitly in services.
    permissions: Mapped[str] = mapped_column(Text, default="[]")
    display_name: Mapped[str] = mapped_column(String(100), default="")


class LoginAttempt(Base):
    """Backs the 5-attempts/15-minutes IP lockout on login."""

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
