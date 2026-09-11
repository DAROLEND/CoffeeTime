"""Image-path resolution (item_img) and a base64 data-URI decoder for the
admin upload pipeline (save_cropped_image)."""
from __future__ import annotations

import base64
import re
from pathlib import Path

DEFAULT_IMAGE = "static/images/menu_items/default.jpg"

_DATA_URI_RE = re.compile(r"^data:image/(jpeg|png|webp);base64,(.+)$", re.DOTALL)


def item_img(raw: str | None, prefix: str = "/") -> str:
    """Resolve a DB-stored image path/URL for use in an <img src>.

    Empty/default-placeholder paths return '' so templates can do
    `{% if item.image_url %}`.
    Absolute http(s) URLs (Supabase-hosted images) pass through unchanged.
    Everything else is treated as root-relative to the app's static tree.
    """
    raw = (raw or "").strip()
    if raw == "" or raw == DEFAULT_IMAGE:
        return ""
    if raw.startswith("http"):
        return raw
    return prefix + raw.lstrip("/")


def save_cropped_image(b64: str, dest_path: str | Path) -> str:
    """Decode a cropper.js data-URI and write it to dest_path (extension
    corrected to match the actual image type). Returns the extension used,
    or '' on any validation failure."""
    match = _DATA_URI_RE.match(b64)
    if not match:
        return ""
    data = base64.b64decode(match.group(2), validate=False)
    if not data or len(data) < 100:
        return ""
    ext = "jpg" if match.group(1) == "jpeg" else match.group(1)
    dest = Path(dest_path).with_suffix(f".{ext}")
    dest.write_bytes(data)
    return ext
