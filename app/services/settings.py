"""Generic key/value settings store helper (site_settings table),
used by pages/index.php's About/dessert-banner sections and the
corresponding admin content-editor pages (Phase 8)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cms import SiteSetting


def get_settings_by_prefix(db: Session, prefix: str) -> dict[str, str]:
    rows = db.execute(
        select(SiteSetting).where(SiteSetting.key.like(f"{prefix}%"))
    ).scalars().all()
    return {row.key: row.value for row in rows}


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(SiteSetting, key)
    if row is None:
        db.add(SiteSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()
