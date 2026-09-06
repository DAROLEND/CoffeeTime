"""Phase 8 (9/n, final) verification: admin/backup.php port.

Confirmed fixes applied: (1) require_super() — PHP checked only
auth_check.php (any logged-in admin), so any staff account could trigger
a full DB dump/download by hitting the URL directly; (2) DB credentials
now come from the real app config instead of PHP's hardcoded
'localhost'/'root'/''/'CoffeeTime', which was disconnected from any real
deployment's actual database.

mysqldump itself isn't invoked for real here — subprocess.run is
monkeypatched, matching how this project avoids depending on external
system binaries in tests."""
from __future__ import annotations

import re
import subprocess

import app.routers.admin.backup as backup_module
from app.models.auth import AdminUser
from app.services.auth import hash_password


def _login_admin(client, db_session, username="boss", role="super", perms="[]"):
    admin = AdminUser(username=username, password=hash_password("adminpass1"), role=role, permissions=perms)
    db_session.add(admin)
    db_session.commit()
    resp = client.get("/login")
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', resp.text).group(1)
    client.post("/login", data={"csrf_token": token, "email": username, "password": "adminpass1"}, follow_redirects=False)
    return admin


def _fake_mysqldump_success(cmd, stdout, stderr, timeout):
    stdout.write(b"-- fake mysqldump output\n")

    class _Result:
        returncode = 0
        stderr = b""

    return _Result()


def test_backup_requires_super(client, db_session):
    """Confirmed fix: PHP's backup.php had no permission check at all
    beyond being logged in as some admin."""
    _login_admin(client, db_session, role="staff", perms='["products", "content", "orders_view", "orders_edit", "reviews"]')
    resp = client.get("/admin/backup", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/dashboard"


def test_backup_downloads_sql_dump(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_mysqldump_success)
    _login_admin(client, db_session)

    resp = client.get("/admin/backup")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["cache-control"] == "no-store"
    assert b"fake mysqldump output" in resp.content

    # The temp dump file is deleted after being read back and served.
    assert list((tmp_path / "backups").glob("*.sql")) == []


def test_backup_uses_real_config_credentials(client, db_session, monkeypatch, tmp_path):
    """Confirmed fix: credentials passed to mysqldump come from the real
    app config, not PHP's hardcoded root/empty-password/localhost."""
    monkeypatch.setattr(backup_module, "PROJECT_ROOT", tmp_path)
    captured = {}

    def _capture(cmd, stdout, stderr, timeout):
        captured["cmd"] = cmd
        stdout.write(b"ok")

        class _Result:
            returncode = 0
            stderr = b""

        return _Result()

    monkeypatch.setattr(subprocess, "run", _capture)
    _login_admin(client, db_session)

    from app.config import get_settings
    settings = get_settings()

    client.get("/admin/backup")
    cmd = captured["cmd"]
    assert f"--user={settings.DB_USER}" in cmd
    assert f"--host={settings.DB_HOST}" in cmd
    assert settings.DB_NAME in cmd


def test_backup_handles_mysqldump_failure(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(backup_module, "PROJECT_ROOT", tmp_path)

    def _fail(cmd, stdout, stderr, timeout):
        class _Result:
            returncode = 1
            stderr = b"mysqldump: command not found"

        return _Result()

    monkeypatch.setattr(subprocess, "run", _fail)
    _login_admin(client, db_session)

    resp = client.get("/admin/backup")
    assert resp.status_code == 500
    assert "Помилка створення резервної копії" in resp.text
