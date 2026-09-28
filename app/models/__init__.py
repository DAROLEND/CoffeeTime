"""Import every model module so `Base.metadata` sees all tables (needed for
Alembic autogenerate and for `Base.metadata.create_all()` in tests)."""
from app.models import auth, catalog, cms, orders, reservations, session_store  # noqa: F401
