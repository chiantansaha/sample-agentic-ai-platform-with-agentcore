"""Unix timestamp utilities for consistent time handling across the application.

All timestamps are stored as Unix timestamp (seconds since epoch) in UTC.
Frontend is responsible for converting to local timezone for display.
"""
import time
from datetime import datetime, timezone
from typing import Union, Optional
from decimal import Decimal


def now_timestamp() -> int:
    """Return current UTC time as Unix timestamp (seconds).

    Returns:
        int: Current Unix timestamp in seconds
    """
    return int(time.time())


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime object to Unix timestamp.

    Args:
        dt: datetime object (assumed UTC if no timezone info)

    Returns:
        int: Unix timestamp in seconds
    """
    if dt.tzinfo is None:
        # Assume UTC for naive datetime
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def timestamp_to_datetime(ts: int) -> datetime:
    """Convert Unix timestamp to datetime object (UTC).

    Args:
        ts: Unix timestamp in seconds

    Returns:
        datetime: UTC datetime object
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def parse_iso_to_timestamp(iso_string: str) -> int:
    """Convert ISO 8601 string to Unix timestamp.

    Used for migration from ISO string format to timestamp.

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        int: Unix timestamp in seconds
    """
    # Handle various ISO formats
    iso_string = iso_string.replace('Z', '+00:00')

    # Handle cases without timezone info
    if '+' not in iso_string and '-' not in iso_string[-6:]:
        iso_string = iso_string + '+00:00'

    try:
        dt = datetime.fromisoformat(iso_string)
    except ValueError:
        # Fallback for some edge cases
        dt = datetime.strptime(iso_string[:19], '%Y-%m-%dT%H:%M:%S')
        dt = dt.replace(tzinfo=timezone.utc)

    return int(dt.timestamp())


def parse_timestamp_value(value: Union[int, str, float, Decimal, None]) -> Optional[int]:
    """Parse timestamp value with backward compatibility.

    Handles both new timestamp format (int) and legacy ISO string format.
    Used in repositories during migration period.

    Args:
        value: Can be int (timestamp), float, Decimal (DynamoDB Number),
               or str (ISO format for backward compatibility)

    Returns:
        int: Unix timestamp in seconds, or None if value is None
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return int(value)

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        # Check if it's a numeric string (timestamp)
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        # Otherwise, parse as ISO string
        return parse_iso_to_timestamp(value)

    raise ValueError(f"Cannot parse timestamp value: {value} (type: {type(value)})")


def format_timestamp_for_display(ts: int, format_type: str = "datetime") -> str:
    """Format timestamp for debugging/logging (not for API responses).

    Args:
        ts: Unix timestamp in seconds
        format_type: "datetime", "date", or "time"

    Returns:
        str: Formatted datetime string in ISO format (UTC)
    """
    dt = timestamp_to_datetime(ts)

    if format_type == "date":
        return dt.strftime('%Y-%m-%d')
    elif format_type == "time":
        return dt.strftime('%H:%M:%S')
    else:
        return dt.isoformat()
