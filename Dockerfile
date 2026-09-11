# Coffee Time — FastAPI app image.
FROM python:3.12-slim-bookworm

# No system Postgres client libs needed — psycopg2-binary (see
# requirements.txt) ships its own bundled libpq.
WORKDIR /app

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
