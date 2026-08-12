from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

INDONESIA_TIMEZONES = {
    "Asia/Jakarta": "WIB",
    "Asia/Makassar": "WITA",
    "Asia/Jayapura": "WIT",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_timezone(value: datetime | None, timezone_name: str = "Asia/Jakarta") -> datetime | None:
    normalized = as_utc(value)
    if normalized is None:
        return None
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = ZoneInfo("Asia/Jakarta")
    return normalized.astimezone(zone)


def iso(value: datetime | None) -> str | None:
    normalized = as_utc(value)
    return normalized.isoformat() if normalized else None


def local_iso(value: datetime | None, timezone_name: str = "Asia/Jakarta") -> str | None:
    localized = to_timezone(value, timezone_name)
    return localized.isoformat() if localized else None


def local_display(value: datetime | None, timezone_name: str = "Asia/Jakarta") -> str:
    localized = to_timezone(value, timezone_name)
    if localized is None:
        return "—"
    suffix = INDONESIA_TIMEZONES.get(timezone_name, localized.tzname() or timezone_name)
    return localized.strftime("%d %b %Y, %H:%M") + f" {suffix}"


def local_day_bounds(day: date | None = None, timezone_name: str = "Asia/Jakarta") -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_day = day or datetime.now(zone).date()
    start_local = datetime.combine(local_day, time.min, tzinfo=zone)
    end_local = datetime.combine(local_day, time.max, tzinfo=zone)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
