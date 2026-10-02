"""Time helpers. Côte d'Ivoire is on GMT all year, so a UTC date is also the local date."""

from datetime import UTC, date, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, always returns aware UTC. Behaves the same on SQLite and PostgreSQL."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return ensure_utc(value).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def campaign_of(day: date, start_month: int = 10) -> str:
    """Cocoa main campaign opens on 1 October: 2026-10-02 belongs to "2026-2027"."""
    start_year = day.year if day.month >= start_month else day.year - 1
    return f"{start_year}-{start_year + 1}"


def campaign_bounds(campaign: str, start_month: int = 10) -> tuple[datetime, datetime]:
    start_year = int(campaign.split("-")[0])
    start = datetime(start_year, start_month, 1, tzinfo=UTC)
    end = datetime(start_year + 1, start_month, 1, tzinfo=UTC)
    return start, end
