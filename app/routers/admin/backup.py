"""
Admin database backup download. Restricted to super-admins.

pg_dump is invoked with an argv list rather than a shell string, so there
is no shell-escaping to get wrong; the password is passed via PGPASSWORD
in the child env rather than the command line, which would otherwise
expose it in the container's process list.
"""
from __future__ import annotations

import datetime
import os
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
        "pg_dump",
        f"--host={settings.DB_HOST}",
        f"--port={settings.DB_PORT}",
        f"--username={settings.DB_USER}",
        "--no-owner",
        "--no-privileges",
        settings.DB_NAME,
    ]
    env = {**os.environ, "PGPASSWORD": settings.DB_PASS}
    try:
        with open(tmp_file, "wb") as out:
            result = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, timeout=300, env=env)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return PlainTextResponse(
            f"<p>Помилка створення резервної копії. Перевірте, чи встановлено pg_dump.</p><pre>{exc}</pre>",
            status_code=500,
        )

    if result.returncode != 0 or not tmp_file.exists():
        error_output = result.stderr.decode(errors="replace") if result.stderr else ""
        return PlainTextResponse(
            f"<p>Помилка створення резервної копії. Перевірте, чи встановлено pg_dump.</p><pre>{error_output}</pre>",
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
