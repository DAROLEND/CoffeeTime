"""Port of admin/backup.php.

Confirmed fixes applied:
1. require_super() added — PHP checked only auth_check.php (any logged-in
   admin), meaning any staff account could trigger a full DB dump/download
   by hitting this URL directly.
2. DB credentials: PHP hardcoded 'localhost'/'root'/''/'CoffeeTime',
   completely disconnected from the real db/db.php config — broken
   against any real deployment. Reimplemented against the actual
   app/config.py settings (the same DB_* values the app itself connects
   with), and passed to mysqldump as an argv list (not a shell string)
   so there's no shell-escaping to get wrong."""
from __future__ import annotations

import datetime
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response

from app.config import get_settings
from app.dependencies import get_current_admin
from app.services.permissions import require_super

router = APIRouter(prefix="/admin/backup", dependencies=[Depends(get_current_admin), Depends(require_super)])

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@router.get("")
def download_backup():
    settings = get_settings()
    filename = f"coffeetime_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.sql"
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
    tmp_file = backup_dir / filename

    cmd = [
        "mysqldump",
        f"--user={settings.DB_USER}",
        f"--password={settings.DB_PASS}",
        f"--host={settings.DB_HOST}",
        f"--port={settings.DB_PORT}",
        "--single-transaction",
        "--routines",
        settings.DB_NAME,
    ]
    try:
        with open(tmp_file, "wb") as out:
            result = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, timeout=300)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return PlainTextResponse(
            f"<p>Помилка створення резервної копії. Перевірте, чи встановлено mysqldump.</p><pre>{exc}</pre>",
            status_code=500,
        )

    if result.returncode != 0 or not tmp_file.exists():
        error_output = result.stderr.decode(errors="replace") if result.stderr else ""
        return PlainTextResponse(
            f"<p>Помилка створення резервної копії. Перевірте, чи встановлено mysqldump.</p><pre>{error_output}</pre>",
            status_code=500,
        )

    data = tmp_file.read_bytes()
    tmp_file.unlink()

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
