#!/bin/sh
# Coffee Time (FastAPI) — container entrypoint.
# Waits for Postgres, brings the schema up to date via Alembic, then execs
# the real command (uvicorn by default — see Dockerfile's CMD).
# POSIX sh (not bash) — plain Debian slim images aren't guaranteed to
# have bash, so the TCP wait below uses Python's socket module instead
# of a bash `/dev/tcp` redirect.
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "[entrypoint] Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
python -c "
import socket, sys, time
host, port = '${DB_HOST}', int('${DB_PORT}')
for attempt in range(1, 31):
    try:
        with socket.create_connection((host, port), timeout=2):
            print('[entrypoint] Postgres TCP port is open.')
            sys.exit(0)
    except OSError:
        print(f'[entrypoint] Attempt {attempt}/30...')
        time.sleep(2)
print('[entrypoint] Postgres not reachable after 30 attempts — starting anyway.')
"

echo "[entrypoint] Running Alembic migrations (alembic upgrade head)..."
# On a fresh DB this creates the whole schema. Pointing at a database
# that already has these tables? Run `alembic stamp 0001_baseline` once
# by hand first — this image won't guess that for you, to avoid
# silently reinterpreting a database it didn't create.
alembic upgrade head

echo "[entrypoint] Starting app: $*"
exec "$@"
