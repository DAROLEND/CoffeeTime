# Coffee Time — online ordering for a café

*Також доступно [українською](README.uk.md).*

### 🔗 Live site: **[coffeetime.onrender.com](https://coffeetime.onrender.com)**

A complete website for the **Coffee Time** café (Husiatyn, Ukraine) with a menu, online ordering,
payment via LiqPay, and an admin panel with role-based permissions.

> Hosted on Render's free tier — the service sleeps after 15 minutes of
> inactivity, so the first load can take up to a minute.

## Screenshots

| | |
|---|---|
| ![Homepage](static/images/preview/homepage.png) | ![Menu](static/images/preview/menu.png) |
| **Homepage** — hero slider with café photos, CTA button | **Menu** — catalog with search, categories and filters |
| ![Cart](static/images/preview/cart.png) | ![Checkout](static/images/preview/cart2.png) |
| **Cart** — item list, order summary | **Checkout** — delivery type, contact info, a drum-style time picker |
| ![Profile](static/images/preview/profile.png) | ![Admin](static/images/preview/admin.png) |
| **Profile** — order history with statuses and ratings | **Admin** — dashboard with stats, a chart, and top items |

## Stack

| Layer | Technologies |
|-----|-----------|
| Frontend | HTML, CSS, Vanilla JS |
| Backend | Python 3.12, FastAPI, Jinja2 |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Payments | LiqPay SDK |
| Notifications | Telegram Bot API, smtplib (Gmail SMTP) |
| Infrastructure | Docker, uvicorn |
| Tests | pytest, SQLite fixtures |

## Features

- Menu catalog with filtering, search, and categories
- Cart with variants: pizza size, crust, sauces, cake weight, ice cream by weight
- Checkout with time selection (drum-style picker) and payment type
- Online payment via LiqPay (with sandbox mode)
- Telegram notification to the admin on every new order
- Email reminder to the customer before the order is ready (cron job)
- Authentication, registration, password recovery
- User profile with order history
- Customer reviews
- Admin panel with role-based permissions (super/staff): products, orders,
  sauces, gallery, hero slider, "About us" page content / banner of the day,
  staff, database backup

## Running with Docker

```bash
git clone https://github.com/DAROLEND/CoffeeTime.git && cd CoffeeTime
cp .env.example .env
# edit .env (DB_NAME, DB_USER, DB_PASS, APP_URL, TELEGRAM_*, LIQPAY_*, MAIL_*, etc.)

docker compose up -d --build
# site at http://localhost:8000
# the DB schema is created automatically via Alembic on first run
```

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # configure DB_* for your local PostgreSQL

alembic upgrade head
uvicorn app.main:app --reload

# reminders cron job (as a separate process, every 15 minutes):
python cron/send_reminders.py
```

## Deployment

Config for free hosting on [Render](https://render.com) — `render.yaml`
(web service + reminders cron job, DB as a separate free Postgres,
e.g. [Supabase](https://supabase.com) or [Neon](https://neon.tech)).

## Tests

```bash
pytest tests/ -v
```

187 tests: cart logic, checkout, payment callbacks,
authentication, CSRF, admin permissions, and rendering of every page.
Run against an in-memory SQLite database — fast, no external dependencies.

## Admin panel

```
/admin/login
```

## Environment variables

All secrets are kept in `.env` (not committed). See `.env.example`.

```
APP_URL=https://yourdomain.com
DB_NAME=coffeetime
DB_USER=coffeetime
DB_PASS=secret
TELEGRAM_BOT_TOKEN=
LIQPAY_PUBLIC_KEY=
LIQPAY_PRIVATE_KEY=
MAIL_USERNAME=
MAIL_PASSWORD=
```
