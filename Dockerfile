# Coffee Time — FastAPI app image.
FROM python:3.12-slim-bookworm

# The app itself needs no system Postgres libs (psycopg2-binary ships a
# bundled libpq), but the admin DB-backup route shells out to pg_dump —
# so install the client. It must be version 17+: pg_dump refuses to dump
# a server newer than itself, and the hosted DB (Supabase) is on 17,
# while bookworm's own postgresql-client is 15. Hence the PGDG repo.
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && install -d /usr/share/postgresql-common/pgdg \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
 && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client-17 \
 && apt-get purge -y curl gnupg \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY static/ ./static/
COPY cron/ ./cron/
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Writable dirs for uploads (menu item photos, gallery, hero slides,
# about/dessert-banner images) — same tree the app writes to when
# Supabase isn't configured, matching the PHP image's equivalent dirs.
RUN mkdir -p static/images/menu_items static/images/gallery static/images/slides static/images/main \
 && useradd --create-home --uid 1000 appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
