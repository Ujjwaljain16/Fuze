"""Timestamps in API responses."""
from datetime import datetime, timezone
from typing import Optional


def iso_utc(value: Optional[datetime]) -> Optional[str]:
    """ISO 8601 with an explicit UTC offset.

    Most columns are naive DateTime holding UTC (the database runs in UTC). Serialized bare,
    "2026-10-12T10:00:00" is read by JavaScript's Date as *local* time, so saved times and
    dates shifted by the viewer's offset. Naive values are marked UTC; aware ones converted.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
