# Migration notes: PHP → FastAPI

This project started as a PHP 8 + MySQL app and was rewritten from
scratch in Python/FastAPI, aiming for **identical logic, design, and
functionality** — same templates/CSS/JS, same MySQL schema (with three
explicitly-approved fixes, see below), same behavior end to end. This
document is the technical record of that port: what changed on purpose,
what was found and fixed along the way, and what's still open.

## Status: complete — full functional parity with the original PHP app

Every PHP page/route has a FastAPI + Jinja2 equivalent: the public
storefront (menu, cart, checkout, LiqPay payments, customer auth/profile,
reviews, gallery), the full role-permissioned admin panel (dashboard,
orders, products, sauces, gallery, hero slider, about/dessert-banner
content, reviews, staff accounts, DB backup), and the reminders cron job.
187 pytest tests cover it.

### Confirmed bug fixes applied during the port (not silent scope changes)

- `orders.user_id` FK: `ON DELETE CASCADE` → `SET NULL` (Alembic
  `0002_port_fixes`).
- `admin/view_order.php`'s invalid `require_perm('orders')` → the real
  `orders_view` key.
- Missing `require_perm('products')` on product add/edit/delete/ajax-delete
  (PHP checked only "some admin is logged in").
- Missing `require_super()` on `admin/backup.php`, whose DB credentials
  were also hardcoded and disconnected from any real deployment —
  reimplemented against the app's real config.
- Missing CSRF protection on `admin/admin_users.php` (every other admin
  form already had none either, so this was the one genuine gap, not a
  pattern applied elsewhere).
- `admin/admin_reviews.php`'s dead duplicate-DELETE branch (a second,
  unreachable POST handler that ran the same DELETE twice) — dropped
  rather than reproduced.

### Confirmed-dead PHP not ported

`admin/update_order.php`, `admin/delete_item.php`,
`admin/restore_mini_pizza.php` (as a route — its 2 seed rows aren't
needed, live data already has real hero_slides rows),
`db/fetch_google_reviews.php`, `cron/preview_email.php` (self-described
"Temporary preview — delete after review" dev tool, never wired into any
real flow), `pages/clear_cart.php` (a full-page-redirect variant that
nothing links to or fetches — the site only ever calls the
JSON-returning `forms/clear_cart.php`, which is ported), and
`includes/validate.php` (a sanitize/validate helper library never
`require_once`'d anywhere in the original codebase — every form that
validates input did so with its own inline logic instead, which is what
got ported route-by-route).

### What's here

- `app/models/` — SQLAlchemy 2.0 models for all 25 tables, 1:1 with the
  original schema (verified by reading the actual `CREATE TABLE`
  statements, not guessed).
- `app/constants/categories.py` — the canonical `ProductCategory` enum +
  `CATEGORY_MODEL_MAP`, replacing ~15 duplicated ad-hoc whitelist arrays
  in the original PHP code.
- `app/services/` — one module per concern: `csrf.py`/`auth.py`/
  `permissions.py`, `cart.py`/`pricing.py`, `checkout.py`, `liqpay.py`,
  `telegram.py`, `mail.py`, `reminders.py` (schedule + send),
  `storage.py` (Supabase upload/delete), `media.py`, `settings.py`
  (site_settings EAV), `orders_admin.py`, `admin_common.py`,
  `enum_utils.py`.
- `app/middleware/session.py` — one unified server-side session
  (DB-backed, httponly+SameSite=Lax cookie), replacing PHP's two
  divergent session bootstraps.
- `app/dependencies.py` — re-fetches admin role/permissions from the DB
  on every request (the `admin/auth_check.php` equivalent).
- `app/routers/public/`, `app/routers/admin/` — every page/form/AJAX
  endpoint, one router module per original PHP file (or small file
  group).
- `app/templates/` — Jinja2 templates, 1:1 with the original markup
  (same CSS classes, same inline `<style>`/`<script>` blocks where the
  original had them).
- `static/` — reused unchanged; no asset was touched.
- `alembic/versions/0001_baseline.py` — the exact original production
  schema. `alembic/versions/0002_port_fixes.py` — the 3 approved fixes:
  `orders.user_id` FK CASCADE→SET NULL, `sushi_sets` piece-count column
  consolidation (with data backfill), `users.email` widened from
  `varchar(30)`.
- `cron/send_reminders.py` — the reminders cron job (run every 15 min).
- `tests/` — 187 pytest tests against an in-memory SQLite DB (schema
  created from the models directly, not via Alembic — MySQL-only SQL
  like `RAND()` is exercised separately, see below).

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# point at a real MySQL
cp .env.example .env   # fill in DB_* at minimum

# on a FRESH database:
alembic upgrade head

# cutting over an EXISTING database that already matches 0001_baseline's
# shape (e.g. a prior PHP-managed deployment of this same schema):
alembic stamp 0001_baseline
alembic upgrade head   # applies only the 0002 fixes

uvicorn app.main:app --reload

# the reminders cron job (run every 15 min):
python cron/send_reminders.py
```

## Verifying without a live MySQL

`alembic upgrade head --sql` compiles both migrations to plain SQL
without needing a DB connection — useful to sanity-check them in an
environment with no MySQL server (this is how they were verified during
development here).

```bash
pytest tests/ -v
alembic upgrade head --sql   # or: --sql -x from_rev:to_rev
```

`pytest` runs against SQLite (fast, no external service needed), which
doesn't understand a couple of MySQL-only constructs the app relies on
— `ORDER BY RAND()` (the dessert-of-the-day banner's random-photo
fallback, in both the public homepage and its admin editor) most
notably. Tests that would hit that path instead seed a
`dessert_banner_image` `site_settings` row to skip it; the query itself
is only verified to compile via `alembic upgrade head --sql` and by
manual testing against real MySQL (see below).

## Docker

`Dockerfile` + `docker-compose.yml`: three services — `app` (uvicorn,
runs `alembic upgrade head` on startup via `docker/entrypoint.sh`), `db`
(mysql:8.0, schema built by Alembic rather than importing a SQL dump),
`cron` (runs `cron/send_reminders.py` every 15 minutes).

```bash
cp .env.example .env
docker compose up --build
# app on http://localhost:8000
```

This was actually built and run end-to-end against real MySQL in
Docker — the only point in this port's development where a real MySQL
engine was involved, everything else having been verified against the
SQLite test fixtures — which caught two real bugs invisible to the
SQLite-based pytest suite:

1. `0001_baseline`'s 4 inline foreign keys had no explicit constraint
   `name=` — MySQL auto-names unnamed FKs itself, so `0002_port_fixes`'s
   `DROP FOREIGN KEY fk_orders_user` (etc.) failed against a freshly
   `alembic upgrade head`-migrated DB. Fixed by naming all 4 to match
   the real constraint names from the original schema.
2. `app_sessions.data` (`TEXT`) had a `server_default="{}"` — MySQL
   rejects any DEFAULT on a TEXT/BLOB/JSON column outright (error 1101).
   Dropped; the app already always sets `.data` explicitly before every
   insert (see `app/middleware/session.py`), so no default was needed.

After both fixes: a full migration + admin login + dashboard/orders/
products navigation + the cron job's own due-reminders query all ran
successfully against a real containerized MySQL 8.0.

## Known remaining gap

Real production **data** hasn't been rehearsed through this yet — the
Docker MySQL above starts empty (schema-only, via Alembic). Cutting over
an existing database uses the `alembic stamp 0001_baseline` path
documented above instead, which hasn't been exercised against a full
data copy end to end.
