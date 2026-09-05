# Coffee Time — FastAPI port (in progress)

This branch (`fastapi-migration`) is a from-scratch Python/FastAPI rewrite
of the PHP app on `main`, aiming for **identical logic, design, and
functionality** — same templates/CSS/JS, same MySQL schema (with three
explicitly-approved fixes, see below), same behavior end to end.

The full migration plan (phases, architecture decisions, and the bug-fix
decisions confirmed with the project owner before any code was written)
lives at `/Users/daro/.claude/plans/foamy-launching-axolotl.md`.

## Status: Phase 0 + Phase 1 complete (foundations only)

No page routes exist yet — this is intentionally just the base layer the
rest of the app builds on. What's here:

- `app/models/` — SQLAlchemy 2.0 models for all 25 existing tables, 1:1
  with `CoffeeTime.sql` (verified by reading the actual `CREATE TABLE`
  statements, not guessed).
- `app/constants/categories.py` — the canonical `ProductCategory` enum,
  replacing ~15 duplicated ad-hoc whitelist arrays in the PHP code.
- `app/services/csrf.py`, `auth.py`, `permissions.py` — ports of
  `includes/helpers.php` (CSRF) and `admin/includes/perm.php`.
- `app/middleware/session.py` — one unified server-side session
  (DB-backed, httponly+SameSite=Lax cookie), replacing PHP's two
  divergent session bootstraps.
- `app/dependencies.py` — the `admin/auth_check.php` equivalent
  (re-fetches admin role/permissions from the DB on every request).
- `alembic/versions/0001_baseline.py` — the exact current production
  schema. `alembic/versions/0002_port_fixes.py` — the 3 approved fixes:
  `orders.user_id` FK CASCADE→SET NULL, `sushi_sets` piece-count column
  consolidation (with data backfill), `users.email` widened from
  `varchar(30)`.

## Running it

```bash
python3 -m venv .venv-fastapi
source .venv-fastapi/bin/activate
pip install -r requirements.txt

# point at a real MySQL (same one the PHP app uses, or a dev copy)
cp .env.example .env   # fill in DB_* at minimum

# on a FRESH database:
alembic upgrade head

# on the EXISTING production database (already matches 0001_baseline):
alembic stamp 0001_baseline
alembic upgrade head   # applies only the 0002 fixes

uvicorn app.main:app --reload
```

## Verifying without a live MySQL

`alembic upgrade head --sql` compiles both migrations to plain SQL
without needing a DB connection — useful to sanity-check them in an
environment with no MySQL server (this is how they were verified during
development here). `pytest` covers what doesn't need a live DB yet:
bcrypt/PHP password-hash compatibility (against real hashes from
`CoffeeTime.sql`), the category enum, and CSRF token logic.

```bash
pytest tests/ -v
alembic upgrade head --sql   # or: --sql -x from_rev:to_rev
```

## Next step

Phase 2 (public read-only pages: index/menu/gallery/reviews + the
`base.html` Jinja2 layout mirroring `includes/header.php`/`footer.php`) —
see the plan file for the full phase breakdown.
