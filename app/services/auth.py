"""
Password hashing/verification + login rate-limiting.

Port of the auth-related pieces of forms/login.php, register.php,
reset.php, change_password.php, admin/admin_users.php.

Password compatibility: PHP's `password_hash($pw, PASSWORD_DEFAULT)` on
PHP 8.x produces a `$2y$` bcrypt hash. passlib's bcrypt backend treats
`$2y$`/`$2b$`/`$2a$` as interchangeable for verification, so existing
users' and admins' passwords keep working without any rehash/migration
step. New passwords are hashed with the same CryptContext going forward
(bit-for-bit compatible bcrypt output PHP could also verify, if it ever
needed to).

See tests/test_auth_compat.py for the concrete compatibility check
against real hashes pulled from CoffeeTime.sql (Phase 1 verification
step from the migration plan).
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
        # Unrecognized hash format — PHP's password_verify() returns false
        # in this case rather than raising; match that.
        return False


def is_bcrypt_hash(hashed: str) -> bool:
    try:
        return pwd_context.identify(hashed) == "bcrypt"
    except Exception:
        return False


def prune_old_attempts(db: Session, ip: str) -> None:
    """Mirrors: DELETE FROM login_attempts WHERE attempted_at < NOW() - INTERVAL {lockMinutes} MINUTE"""
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
