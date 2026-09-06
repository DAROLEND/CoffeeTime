"""Shared helper for a recurring SQLAlchemy Enum gotcha: reading a column
back from the DB gives you the Python enum member, but an object that was
constructed in memory with a plain string (`Order(status="done")` — common
in tests, and anywhere a row is mutated and re-read before being
expired/refreshed) keeps that literal string until the row round-trips
through the DB. Call sites that compare against `.value` need to handle
both shapes; this is the one place that logic lives."""
from __future__ import annotations


def enum_value(x) -> str:
    return x.value if hasattr(x, "value") else (x or "")
