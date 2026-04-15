from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utcnow() -> datetime:
    return datetime.now(UTC)


def start_of_day() -> datetime:
    now = utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day() -> datetime:
    return start_of_day() + timedelta(days=1)


def within_next_days(days: int) -> datetime:
    return utcnow() + timedelta(days=days)
