"""
Central app configuration.

Mirrors, in one place, what the PHP app read from three separate files:
- includes/env.php     -> just loaded .env, defined nothing itself
- includes/config.php  -> LIQPAY_*, SITE_URL, SITE_PATH, APP_ENV
- db/db.php            -> DB_HOST/PORT/NAME/USER/PASS/CHARSET/SOCKET

Values are read from the environment (populated from `.env` via
python-dotenv / pydantic-settings), with the same defaults the PHP code
used, so an existing `.env` file works unchanged.

DB engine: PostgreSQL (psycopg2). The original PHP app used MySQL, but
that was purely a PHP-ecosystem default — nothing in this port's SQL is
MySQL-specific, so the FastAPI/SQLAlchemy version runs on Postgres
instead, which has a real permanently-free hosting story (Supabase,
Neon) that MySQL no longer does. DB_CHARSET is kept only for backward
compatibility with an old `.env`; Postgres is UTF-8 by default and
never needs it.
"""
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App / site ---
    APP_ENV: str = "production"
    APP_URL: str = ""  # if unset, SITE_URL is derived from the request host (see dependencies.get_site_url)
    SESSION_LIFETIME: int = 3600  # seconds, matches PHP session.gc_maxlifetime

    # --- Database (same names/defaults as db/db.php, port now Postgres's) ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = "postgres"
    DB_PASS: str = ""
    DB_CHARSET: str = "utf8mb4"  # unused by Postgres, kept for an old .env's sake
    DB_SOCKET: str | None = None

    # --- LiqPay ---
    LIQPAY_PUBLIC_KEY: str = ""
    LIQPAY_PRIVATE_KEY: str = ""
    LIQPAY_SANDBOX: int = 1

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- Mail (PHPMailer -> smtplib equivalent) ---
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = "Coffee Time"

    # --- Google (index.php reviews import script; feature confirmed unused today) ---
    GOOGLE_API_KEY: str = ""
    GOOGLE_PLACE_ID: str = ""

    # --- Supabase storage (includes/storage.php) ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "media"

    # --- Misc, used ad hoc in PHP templates but missing from .env.example ---
    CAFE_PHONE: str = ""
    CAFE_INSTAGRAM: str = ""
    GA_ID: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def sqlalchemy_database_uri(self) -> str:
        # mirrors db/db.php's DSN construction (unix socket takes priority),
        # ported to Postgres's psycopg2 driver/query-param names.
        # User/password are percent-encoded — Supabase's pooler user is
        # "postgres.<project-ref>" (a literal dot) and a generated DB
        # password routinely contains "@"/"/" etc., either of which
        # breaks the URL's own delimiters if inserted raw.
        driver = "postgresql+psycopg2"
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASS)
        if self.DB_SOCKET:
            return f"{driver}://{user}:{password}@/{self.DB_NAME}?host={self.DB_SOCKET}"
        return f"{driver}://{user}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
