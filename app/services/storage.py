"""Supabase Storage integration for admin image uploads (product photos,
gallery, hero slides, sauces, ...), with a transparent fallback to local
disk storage when Supabase isn't configured."""
from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.services.media import save_cropped_image


def supabase_upload(local_path: str | Path, remote_path: str, mime: str = "image/webp") -> str | None:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        return None

    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{settings.SUPABASE_BUCKET}/{remote_path.lstrip('/')}"
    try:
        data = Path(local_path).read_bytes()
    except OSError:
        return None

    try:
        resp = httpx.post(
            url,
            content=data,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": mime,
                "x-upsert": "true",  # overwrite if exists
            },
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
    except httpx.HTTPError:
        return None

    if 200 <= resp.status_code < 300:
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{remote_path.lstrip('/')}"
    return None


def supabase_delete(remote_path: str) -> None:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        return

    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{settings.SUPABASE_BUCKET}/{remote_path.lstrip('/')}"
    try:
        httpx.request(
            "DELETE", url,
            headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"},
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
    except httpx.HTTPError:
        pass


def delete_stored_image(image_path: str | None, project_root: str | Path) -> None:
    """Remove a previously-stored image, whether it lives in Supabase
    (an http(s) URL) or on local disk (a root-relative path)."""
    if not image_path:
        return
    settings = get_settings()
    if image_path.startswith("http"):
        parsed = urlparse(image_path).path
        prefix = f"/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"
        if parsed.startswith(prefix):
            supabase_delete(parsed[len(prefix):])
    else:
        local = Path(project_root) / image_path
        if local.exists():
            try:
                local.unlink()
            except OSError:
                pass


def upload_image(data: bytes, local_dest: str | Path, remote_path: str, mime: str = "image/webp") -> str | None:
    """Write an uploaded file's bytes into place, then mirror it to
    Supabase if configured. Returns the value to store in the DB: a
    Supabase public URL, or (fallback) just the filename, which callers
    turn into a root-relative path. Takes raw bytes rather than a
    temp-file path, since Starlette's `UploadFile` has no guaranteed
    on-disk path to move from."""
    local_dest = Path(local_dest)
    try:
        local_dest.write_bytes(data)
    except OSError:
        return None

    supabase_url = supabase_upload(local_dest, remote_path, mime)
    if supabase_url:
        return supabase_url
    return local_dest.name


def upload_image_b64(b64: str, local_dest: str | Path, remote_path: str) -> str | None:
    """Decode a cropper.js data-URI and store it, same fallback rules as
    upload_image()."""
    ext = save_cropped_image(b64, Path(str(local_dest) + ".jpg"))
    if not ext:
        return None

    final_local = Path(str(local_dest) + f".{ext}")
    final_remote = f"{remote_path}.{ext}"
    mime = "image/png" if ext == "png" else "image/jpeg"

    supabase_url = supabase_upload(final_local, final_remote, mime)
    if supabase_url:
        return supabase_url
    return final_local.name


def unique_filename(prefix: str = "item_") -> str:
    """A collision-safe unique token; the exact format doesn't matter
    since it's never parsed back, only used as an opaque on-disk/remote
    filename."""
    return f"{prefix}{uuid.uuid4().hex}"
