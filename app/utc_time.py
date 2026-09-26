"""Serialize MySQL wall-clock values with the configured database time zone."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import DB_TIME_ZONE


def mysql_datetime_as_utc(value: datetime) -> str:
    if value.tzinfo is not None:
        raise ValueError("MySQL datetime must be naive; check the database contract")
    return value.replace(tzinfo=ZoneInfo(DB_TIME_ZONE)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
