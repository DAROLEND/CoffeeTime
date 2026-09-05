"""Per-request DB session dependency (FastAPI equivalent of `$conn` being
available to every PHP page via `require_once 'db/db.php'`)."""
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
