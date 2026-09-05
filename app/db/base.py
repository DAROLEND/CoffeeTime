"""
SQLAlchemy engine + declarative base.

Replaces the mysqli half of db/db.php (the PDO handle it also opened was
dead code — grep confirmed `$pdo` was never used anywhere else in the PHP
codebase — so there is nothing to replicate there).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,   # mirrors mysqli's implicit reconnect-on-use tolerance
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass
