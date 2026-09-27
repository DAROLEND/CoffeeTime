# Coffee Time — онлайн-замовлення для кафе

*Also available in [English](README.md).*

### 🔗 Живий сайт: **[coffeetime.onrender.com](https://coffeetime.onrender.com)**

Повноцінний сайт для кафе **Coffee Time** (м. Гусятин) з меню, онлайн-замовленнями,
оплатою через LiqPay та адмін-панеллю з розмежуванням прав.

Проєкт складається з **JSON API на FastAPI** і **SPA на React + TypeScript**, яка
з ним працює. Контракт між ними — OpenAPI-схема API: типи запитів і відповідей
на фронтенді генеруються з неї.

> Хостинг на безкоштовному плані Render — сервіс засинає після 15 хв
> бездіяльності, тож перше відкриття може зайняти до хвилини.

## Скріншоти

| | |
|---|---|
| ![Головна](static/images/preview/homepage.png) | ![Меню](static/images/preview/menu.png) |
| **Головна** — hero-слайдер з фото кафе, CTA-кнопка | **Меню** — каталог з пошуком, категоріями та фільтрами |
| ![Кошик](static/images/preview/cart.png) | ![Оформлення](static/images/preview/cart2.png) |
| **Кошик** — список товарів, зведення замовлення | **Оформлення** — тип доставки, контакти, барабанний picker часу |
| ![Профіль](static/images/preview/profile.png) | ![Адмін](static/images/preview/admin.png) |
| **Профіль** — історія замовлень зі статусами та оцінками | **Адмін** — дашборд зі статистикою, графіком та топ-товарами |

## Стек

| Шар | Технології |
|-----|-----------|
| Frontend | React 19, TypeScript, Vite, React Router 7, TanStack Query 5, openapi-fetch + openapi-typescript |
| Backend | Python 3.12, FastAPI (JSON API під `/api`), Pydantic v2 |
| БД | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Оплата | LiqPay |
| Сповіщення | Telegram Bot API, smtplib (Gmail SMTP) |
| Інфраструктура | Docker, uvicorn, Render (API web service + static site) |
| Тести | pytest (API, SQLite fixtures), Vitest + Testing Library (фронтенд) |

## Структура

```
app/                    бекенд на FastAPI
  main.py               застосунок, обробники помилок → {detail, code, errors}
  api/                  роутер /api (залежність CSRF), хелпери помилок
  routers/public/       сесія, меню, кошик, оформлення, оплата, авторизація, профіль, відгуки, сторінки
  routers/admin/        дашборд, замовлення, товари, соуси, галерея, відгуки, hero-слайди, …
  schemas/              Pydantic-моделі запитів і відповідей → /openapi.json
  services/             бізнес-логіка (ціни, кошик, оформлення, LiqPay, нагадування, …)
  models/               моделі SQLAlchemy
alembic/                міграції
cron/send_reminders.py  email-нагадування (кожні 15 хв)
frontend/               SPA на React
  src/api/              типізований клієнт (schema.d.ts генерується), CSRF, query-хуки
  src/features/         сторінки сайту: головна, меню, кошик, оформлення, оплата, авторизація, профіль, …
  src/admin/            адмін-панель (окремий lazy-чанк)
  src/styles/           CSS сайту, ізольований по сторінках (див. postcss-scope-pages.ts)
tests/                  тести бекенду
```

## Функціонал

- Каталог меню з фільтрацією, пошуком і категоріями
- Кошик із варіантами: розмір піци, сирний борт, соуси, вага торту, кульки морозива, начинки фаст-фуду
- **Кожна ціна рахується на сервері** з бази — клієнт надсилає тільки вибір
- Оформлення замовлення з вибором часу (барабанний picker у часовому поясі кафе) та типом оплати
- Онлайн-оплата через LiqPay (з sandbox-режимом), сторінка очікування опитує статус платежу
- Telegram-сповіщення адміністратору при новому замовленні
- Email-нагадування клієнту перед готовністю замовлення (cron-джоба)
- Авторизація, реєстрація, відновлення паролю
- Профіль користувача з історією замовлень та оцінками
- Відгуки клієнтів з модерацією
- Адмін-панель з розмежуванням прав (super/staff): товари, замовлення,
  соуси, галерея, hero-слайдер, контент сторінки "Про нас"/банер дня,
  персонал, резервна копія БД

## Правила API

- Усі маршрути — під `/api`; інтерактивна документація — на `/docs`.
- Авторизація — серверна сесія в httponly-cookie (`coffeetime_session`,
  `Secure` у продакшені, `SameSite=Lax`). Без JWT.
- CSRF: `GET /api/csrf-token`, далі заголовок `X-CSRF-Token` на кожному
  POST/PUT/PATCH/DELETE. Фронтенд-клієнт робить це сам і один раз повторює
  запит, якщо токен застарів.
- Помилки завжди мають вигляд `{"detail": "...", "code": "...", "errors": [...]}`.
- У продакшені SPA і API на одному origin (static site проксує `/api/*`),
  тому CORS не потрібен.

## Локальний запуск

Бекенд:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # налаштувати DB_* під локальний PostgreSQL

alembic upgrade head
uvicorn app.main:app --reload          # API на http://localhost:8000/api, документація на /docs

# reminders cron-джоба (окремим процесом, кожні 15 хв):
python cron/send_reminders.py
```

Фронтенд (Node 20.19+ або 22):

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 — проксує /api і /static на :8000
```

`API_URL` перенаправляє dev-проксі на інший бекенд (`API_URL=https://… npm run dev`).

Після зміни схем API перегенеруйте TypeScript-типи:

```bash
npm run gen:api            # з /openapi.json запущеного бекенду
npm run gen:api:offline    # або прямо з коду, без сервера
```

## Запуск через Docker

```bash
git clone https://github.com/DAROLEND/CoffeeTime.git && cd CoffeeTime
cp .env.example .env
# відредагувати .env (DB_NAME, DB_USER, DB_PASS, APP_URL, TELEGRAM_*, LIQPAY_*, MAIL_* тощо)

docker compose up -d --build   # API + Postgres на http://localhost:8000
cd frontend && npm install && npm run dev   # SPA на http://localhost:5173
```

Схема БД створюється автоматично через Alembic при першому запуску.

## Деплой

`render.yaml` — Blueprint для [Render](https://render.com) з трьома сервісами:

- **coffeetime-fastapi** — API (Docker web service, health check `/api/health`);
- **coffeetime-web** — SPA як static site: `cd frontend && npm ci && npm run build`,
  публікується з `frontend/dist`, rewrites `/api/*` і `/static/*` → API,
  `/*` → `/index.html`;
- **coffeetime-reminders** — cron-джоба нагадувань.

БД — окремий безкоштовний Postgres (напр. [Supabase](https://supabase.com) чи
[Neon](https://neon.tech)). `APP_URL` на API — це публічний origin SPA:
з нього будуються URL повернення/колбеку LiqPay і посилання для скидання паролю.

## Тести

```bash
pytest tests/ -v               # бекенд: 236 тестів
cd frontend && npm test        # фронтенд: Vitest + Testing Library
cd frontend && npm run build   # перевірка типів (tsc -b) + продакшен-збірка
```

Тести бекенду ганяються проти SQLite в пам'яті й покривають ціноутворення
кошика, оформлення, платіжні колбеки, авторизацію, CSRF, права адмінів і всі
маршрути API. Тести фронтенду покривають логіку цін і слотів часу,
CSRF-клієнт і ключові екрани (вхід, кошик) проти заглушки API.

## Адмін-панель

```
/admin   (вхід на /login з адмін-акаунтом)
```

## Змінні середовища

Всі секрети зберігаються в `.env` (не комітиться). Дивись `.env.example`.

```
APP_URL=https://yourdomain.com     # публічний origin SPA
FRONTEND_URL=                      # необов'язково: GET / на API редіректить сюди
DB_NAME=coffeetime
DB_USER=coffeetime
DB_PASS=secret
TELEGRAM_BOT_TOKEN=
LIQPAY_PUBLIC_KEY=
LIQPAY_PRIVATE_KEY=
MAIL_USERNAME=
MAIL_PASSWORD=
```
