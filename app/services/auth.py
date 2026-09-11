"""
Password hashing/verification + login rate-limiting.

passlib's bcrypt backend treats the `$2y$`/`$2b$`/`$2a$` hash-format
variants as interchangeable for verification, so existing stored password
hashes keep working regardless of which variant produced them.
"""
from __future__ import annotations

import datetime

from passlib.context import CryptContext
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.auth import LoginAttempt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        # Unrecognized hash format — treat as a failed verification rather
        # than raising.
        return False


def is_bcrypt_hash(hashed: str) -> bool:
    try:
        return pwd_context.identify(hashed) == "bcrypt"
    except Exception:
        return False


def prune_old_attempts(db: Session, ip: str) -> None:
    """Deletes login_attempts rows older than the lockout window."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=LOCK_MINUTES)
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < cutoff))
    db.commit()


def count_recent_attempts(db: Session, ip: str) -> int:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=LOCK_MINUTES)
    stmt = select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.ip == ip, LoginAttempt.attempted_at > cutoff
    )
    return db.execute(stmt).scalar_one()


def record_failed_attempt(db: Session, ip: str) -> None:
    db.add(LoginAttempt(ip=ip))
    db.commit()


def is_locked_out(db: Session, ip: str) -> bool:
    prune_old_attempts(db, ip)
    return count_recent_attempts(db, ip) >= MAX_ATTEMPTS
