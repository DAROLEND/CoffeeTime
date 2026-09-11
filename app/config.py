"""
Central app configuration, read from the environment via pydantic-settings
(populated from `.env` in development).

DB engine is PostgreSQL (psycopg2), chosen for its permanently-free hosting
options (Supabase, Neon). DB_CHARSET is unused by Postgres but kept for
backward compatibility with older `.env` files.
"""
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App / site ---
    APP_ENV: str = "production"
    APP_URL: str = ""  # if unset, SITE_URL is derived from the request host (see dependencies.get_site_url)
    SESSION_LIFETIME: int = 3600  # seconds

    # --- Database ---
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

    # --- Mail ---
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = "Coffee Time"

    # --- Google (reviews import; currently unused) ---
    GOOGLE_API_KEY: str = ""
    GOOGLE_PLACE_ID: str = ""

    # --- Supabase storage ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "media"

    # --- Misc ---
    CAFE_PHONE: str = ""
    CAFE_INSTAGRAM: str = ""
    GA_ID: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def sqlalchemy_database_uri(self) -> str:
        # Unix socket takes priority over host/port when set.
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
