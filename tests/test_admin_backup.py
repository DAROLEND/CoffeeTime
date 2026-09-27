"""Tests for the admin database backup download: super-admin restriction,
and credentials passed to pg_dump.

pg_dump itself isn't invoked for real here — subprocess.run is
monkeypatched, matching how this project avoids depending on external
system binaries in tests."""
from __future__ import annotations

import subprocess

import app.routers.admin.backup as backup_module
from tests.helpers import login_admin


def _fake_pg_dump_success(cmd, stdout, stderr, timeout, env=None):
    stdout.write(b"-- fake pg_dump output\n")

    class _Result:
        returncode = 0
        stderr = b""

    return _Result()


def test_backup_requires_super(api, db_session):
    """Only super-admins may download the database backup."""
    login_admin(api, db_session, role="staff", perms='["products", "content", "orders_view", "orders_edit", "reviews"]')
    resp = api.get("/api/admin/backup")
    assert resp.status_code == 403


def test_backup_downloads_sql_dump(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_pg_dump_success)
    login_admin(api, db_session)

    resp = api.get("/api/admin/backup")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["cache-control"] == "no-store"
    assert b"fake pg_dump output" in resp.content

    # The temp dump file is deleted after being read back and served.
    assert list((tmp_path / "backups").glob("*.sql")) == []


def test_backup_uses_real_config_credentials(api, db_session, monkeypatch, tmp_path):
    """Credentials passed to pg_dump come from the real app config.

    The password specifically must NOT be on the command line (where any
    other process could read it out of /proc) — pg_dump takes it from
    PGPASSWORD in the child environment instead."""
    monkeypatch.setattr(backup_module, "PROJECT_ROOT", tmp_path)
    captured = {}

    def _capture(cmd, stdout, stderr, timeout, env=None):
        captured["cmd"] = cmd
        captured["env"] = env
        stdout.write(b"ok")

        class _Result:
            returncode = 0
            stderr = b""

        return _Result()

    monkeypatch.setattr(subprocess, "run", _capture)
    login_admin(api, db_session)

    from app.config import get_settings
    settings = get_settings()

    api.get("/api/admin/backup")
    cmd = captured["cmd"]
    assert cmd[0] == "pg_dump"
    assert f"--username={settings.DB_USER}" in cmd
    assert f"--host={settings.DB_HOST}" in cmd
    assert f"--port={settings.DB_PORT}" in cmd
    assert settings.DB_NAME in cmd
    assert captured["env"]["PGPASSWORD"] == settings.DB_PASS
    assert not any("PGPASSWORD" in part or settings.DB_PASS in part for part in cmd if settings.DB_PASS)


def test_backup_handles_pg_dump_failure(api, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module, "PROJECT_ROOT", tmp_path)

    def _fail(cmd, stdout, stderr, timeout, env=None):
        class _Result:
            returncode = 1
            stderr = b"pg_dump: command not found"

        return _Result()

    monkeypatch.setattr(subprocess, "run", _fail)
    login_admin(api, db_session)

    resp = api.get("/api/admin/backup")
    assert resp.status_code == 500
    assert "Помилка створення резервної копії" in resp.json()["detail"]
    assert resp.json()["errors"] == ["pg_dump: command not found"]
