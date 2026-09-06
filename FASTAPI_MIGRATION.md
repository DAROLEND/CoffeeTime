# Coffee Time — FastAPI port

This branch (`fastapi-migration`) is a from-scratch Python/FastAPI rewrite
of the PHP app on `main`, aiming for **identical logic, design, and
functionality** — same templates/CSS/JS, same MySQL schema (with three
explicitly-approved fixes, see below), same behavior end to end.

The full migration plan (phases, architecture decisions, and the bug-fix
decisions confirmed with the project owner before any code was written)
lives at `/Users/daro/.claude/plans/foamy-launching-axolotl.md`.

## Status: Phases 0–9 complete — full functional parity with the PHP app

Every PHP page/route has a FastAPI + Jinja2 equivalent: the public
storefront (menu, cart, checkout, LiqPay payments, customer auth/profile,
reviews, gallery), the full role-permissioned admin panel (dashboard,
orders, products, sauces, gallery, hero slider, about/dessert-banner
content, reviews, staff accounts, DB backup), and the reminders cron job.
187 pytest tests cover it. What remains is Phase 10 (this document,
`.env.example`, and the Docker/deploy mechanism — see below).

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
real flow).

### What's here

- `app/models/` — SQLAlchemy 2.0 models for all 25 existing tables, 1:1
  with `CoffeeTime.sql` (verified by reading the actual `CREATE TABLE`
  statements, not guessed).
- `app/constants/categories.py` — the canonical `ProductCategory` enum +
  `CATEGORY_MODEL_MAP`, replacing ~15 duplicated ad-hoc whitelist arrays
  in the PHP code.
- `app/services/` — one module per PHP concern: `csrf.py`/`auth.py`/
  `permissions.py` (helpers.php/perm.php), `cart.py`/`pricing.py`
  (add_to_cart.php family), `checkout.py`, `liqpay.py`, `telegram.py`,
  `mail.py`, `reminders.py` (schedule + send), `storage.py` (Supabase
  upload/delete), `media.py`, `settings.py` (site_settings EAV),
  `orders_admin.py`, `admin_common.py`, `enum_utils.py`.
- `app/middleware/session.py` — one unified server-side session
  (DB-backed, httponly+SameSite=Lax cookie), replacing PHP's two
  divergent session bootstraps.
- `app/dependencies.py` — the `admin/auth_check.php` equivalent
  (re-fetches admin role/permissions from the DB on every request).
- `app/routers/public/`, `app/routers/admin/` — every page/form/AJAX
  endpoint, one router module per PHP file (or small file group).
- `app/templates/` — Jinja2 templates, 1:1 with the PHP markup (same
  CSS classes, same inline `<style>`/`<script>` blocks where the
  original had them; `base.html`/`admin/admin_base.html` replace
  `header.php`/`footer.php` and `layout_top.php`/`layout_bottom.php`).
- `static/` — reused unchanged from `main`; no asset was touched.
- `alembic/versions/0001_baseline.py` — the exact current production
  schema. `alembic/versions/0002_port_fixes.py` — the 3 approved fixes:
  `orders.user_id` FK CASCADE→SET NULL, `sushi_sets` piece-count column
  consolidation (with data backfill), `users.email` widened from
  `varchar(30)`.
- `cron/send_reminders.py` — replaces `cron/send_reminders.php` (run on
  the same `*/15 * * * *` schedule).
- `tests/` — 187 pytest tests against an in-memory SQLite DB (schema
  created from the models directly, not via Alembic — MySQL-only SQL
  like `RAND()` is exercised separately, see below).

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

# the reminders cron job (same */15 min schedule as the PHP version):
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
manual testing against real MySQL.

## Docker

`Dockerfile.fastapi` + `docker-compose.fastapi.yml` (`main`'s PHP+Apache
`Dockerfile`/`docker-compose.yml` are untouched — separate files so both
stacks coexist). Three services: `app` (uvicorn, runs `alembic upgrade
head` on startup via `docker/entrypoint.sh`), `db` (mysql:8.0, fresh —
no `CoffeeTime.sql` import; Alembic builds the schema instead), `cron`
(runs `cron/send_reminders.py` every 15 minutes).

```bash
cp .env.example .env
docker compose -f docker-compose.fastapi.yml up --build
# app on http://localhost:8000
```

This was actually built and run end-to-end against real MySQL in Docker
(not just SQLite) during Phase 10, which caught two real bugs invisible
to the SQLite-based pytest suite (fixed, see git history):

1. `0001_baseline`'s 4 inline foreign keys had no explicit constraint
   `name=` — MySQL auto-names unnamed FKs itself, so `0002_port_fixes`'s
   `DROP FOREIGN KEY fk_orders_user` (etc.) failed against a freshly
   `alembic upgrade head`-migrated DB. Fixed by naming all 4 to match
   the real constraint names already in `CoffeeTime.sql`.
2. `app_sessions.data` (`TEXT`) had a `server_default="{}"` — MySQL
   rejects any DEFAULT on a TEXT/BLOB/JSON column outright (error 1101).
   Dropped; the app already always sets `.data` explicitly before every
   insert (see `app/middleware/session.py`), so no default was needed.

After both fixes: a full migration + admin login + dashboard/orders/
products navigation + the cron job's own due-reminders query all ran
successfully against a real containerized MySQL 8.0.

## Remaining before cutover

- Real production **data** hasn't been rehearsed through yet — the
  Docker MySQL above starts empty (schema-only, via Alembic). Cutting
  over an existing PHP-managed database uses the `alembic stamp
  0001_baseline` path documented above instead, which hasn't been
  exercised against a full data copy end to end.
