# Coffee Time — онлайн-замовлення для кафе

### 🔗 Живий сайт: **[coffeetime.onrender.com](https://coffeetime.onrender.com)**

Повноцінний сайт для кафе **Coffee Time** (м. Гусятин) з меню, онлайн-замовленнями,
оплатою через LiqPay та адмін-панеллю з розмежуванням прав.

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
| Frontend | HTML, CSS, Vanilla JS |
| Backend | Python 3.12, FastAPI, Jinja2 |
| БД | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Оплата | LiqPay SDK |
| Сповіщення | Telegram Bot API, smtplib (Gmail SMTP) |
| Інфраструктура | Docker, uvicorn |
| Тести | pytest, SQLite fixtures |

## Функціонал

- Каталог меню з фільтрацією, пошуком і категоріями
- Кошик із варіантами: розмір піци, борти, соуси, вага торту, морозиво на вагу
- Оформлення замовлення з вибором часу (барабанний picker) та типом оплати
- Онлайн-оплата через LiqPay (з sandbox-режимом)
- Telegram-сповіщення адміністратору при новому замовленні
- Email-нагадування клієнту перед готовністю замовлення (cron-джоба)
- Авторизація, реєстрація, відновлення паролю
- Профіль користувача з історією замовлень
- Відгуки клієнтів
- Адмін-панель з розмежуванням прав (super/staff): товари, замовлення,
  соуси, галерея, hero-слайдер, контент сторінки "Про нас"/банер дня,
  персонал, резервна копія БД

## Запуск через Docker

```bash
git clone https://github.com/DAROLEND/CoffeeTime.git && cd CoffeeTime
cp .env.example .env
# відредагувати .env (DB_NAME, DB_USER, DB_PASS, APP_URL, TELEGRAM_*, LIQPAY_*, MAIL_* тощо)

docker compose up -d --build
# сайт на http://localhost:8000
# схема БД створюється автоматично через Alembic при першому запуску
```

## Локальний запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # налаштувати DB_* під локальний PostgreSQL

alembic upgrade head
uvicorn app.main:app --reload

# reminders cron-джоба (окремим процесом, кожні 15 хв):
python cron/send_reminders.py
```

## Деплой

Конфіг для безкоштовного хостингу на [Render](https://render.com) — `render.yaml`
(web-сервіс + cron-джоба нагадувань, БД — окремий безкоштовний Postgres,
напр. [Supabase](https://supabase.com) чи [Neon](https://neon.tech)).

## Тести

```bash
pytest tests/ -v
```

187 тестів: логіка кошика, оформлення замовлення, платіжні колбеки,
аутентифікація, CSRF, права адмінів і рендеринг усіх сторінок.
Ганяються проти SQLite в пам'яті — швидко і без зовнішніх залежностей.

## Адмін-панель

```
/admin/login
```

## Змінні середовища

Всі секрети зберігаються в `.env` (не комітиться). Дивись `.env.example`.

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
