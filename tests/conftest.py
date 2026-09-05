"""Shared pytest fixtures: an in-memory SQLite DB (schema created directly
from the SQLAlchemy models, not via Alembic) wired into the FastAPI app in
place of the configured MySQL engine, plus a TestClient.

This is a template/route-rendering smoke test, not a MySQL-fidelity
check — MySQL-specific SQL (e.g. `func.rand()`) is exercised separately
by `alembic upgrade head --sql` (see FASTAPI_MIGRATION.md) since SQLite
doesn't understand MySQL's RAND(). Tests here seed around that instead of
avoiding real routes.
"""
from __future__ import annotations

import os

# Must be set BEFORE any `app.*` module is imported: app/config.py's
# get_settings() is @lru_cache'd, and app/db/base.py + app/main.py both
# call it at import time. Left at the default APP_ENV=production, the
# session cookie is marked Secure (see app/middleware/session.py), which
# a plain-http TestClient silently refuses to store/resend between
# requests — session state would appear to "not persist" across calls
# even though the middleware logic is correct. This bit us once already
# while writing the Phase 3 cart tests; setting it here up front avoids
# every future test file needing to remember it.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DB_NAME", "coffeetime_test")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.db.base import Base
import app.models  # noqa: F401 — registers all models on Base.metadata


@pytest.fixture(autouse=True, scope="session")
def _fast_bcrypt_for_tests():
    """Production hashing (app/services/auth.py) intentionally uses
    passlib's bcrypt default cost (12 rounds) — that's the whole point of
    bcrypt being slow. But the same cost factor applied ~100+ times across
    this test suite (every register/login/change-password test hashes at
    least once) turned a few-second run into several minutes on this
    sandbox's CPU. Lower the rounds for the test process only; nothing in
    app/ reads this — it patches the module-level CryptContext instance
    Auth's hash_password()/verify_password() already call by name."""
    from passlib.context import CryptContext

    import app.services.auth as auth_module

    auth_module.pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)


@pytest.fixture()
def sqlite_engine():
    # A file-backed (not :memory:) SQLite DB via StaticPool so every
    # connection in the pool sees the same schema/data — the session
    # middleware and the route's `get_db` dependency each open their own
    # connection per request, which a plain :memory: DB can't share.
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(sqlite_engine):
    TestSessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(sqlite_engine, db_session, monkeypatch):
    import app.middleware.session as session_mw
    from app.db.session import get_db
    from app.main import app

    TestSessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(session_mw, "SessionLocal", TestSessionLocal)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
