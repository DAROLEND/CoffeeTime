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

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.db.base import Base
import app.models  # noqa: F401 — registers all models on Base.metadata


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
