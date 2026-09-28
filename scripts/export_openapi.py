"""Write the API's OpenAPI schema to a file without starting a server
(or connecting to a database), so the frontend can regenerate its types
offline or in CI:

    python scripts/export_openapi.py frontend/openapi.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# The engine is created lazily-connected, so any DB settings will do.
os.environ.setdefault("DB_NAME", "coffeetime")
os.environ.setdefault("APP_ENV", "development")

from app.main import app  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {out}")
