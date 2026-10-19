from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import re

def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def parse_datetime_flexible(val: Optional[Union[datetime, str, int, float]]) -> datetime:
    """
    Parses datetime, ISO strings, or relative strings ("8 min ago", "just now") into a UTC datetime.
    """
    now = datetime.now(timezone.utc)
    if val is None:
        return now
    if isinstance(val, datetime):
        return to_utc(val)
    if isinstance(val, (int, float)):
        # Treat as minutes ago
        return now - timedelta(minutes=float(val))
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str or val_str.lower() in ("just now", "now"):
            return now
        # Check relative time string
        m = re.match(r"^([\d.]+)\s*(min|minute|hr|hour|day|d)s?\s*ago$", val_str, re.IGNORECASE)
        if m:
            num = float(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith("min"):
                return now - timedelta(minutes=num)
            elif unit.startswith("h"):
                return now - timedelta(hours=num)
            elif unit.startswith("d"):
                return now - timedelta(days=num)
        # Try ISO format
        try:
            return to_utc(datetime.fromisoformat(val_str))
        except ValueError:
            pass
        # Try standard formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return to_utc(datetime.strptime(val_str, fmt))
            except ValueError:
                continue
    return now

def calculate_time_diff(dt: Optional[datetime]) -> timedelta:
    if dt is None:
        return timedelta(seconds=0)
    now = datetime.now(timezone.utc)
    utc_dt = to_utc(dt)
    diff = now - utc_dt
    if diff.total_seconds() < 0:
        return timedelta(seconds=0)
    return diff

def format_time_ago(dt: Optional[datetime]) -> str:
    """
    Calculates how long it has been since an action happened and returns a formatted string.
    Example: 'just now', '5 min ago', '2 hr ago', '3 days ago'.
    """
    if dt is None:
        return "just now"
    diff = calculate_time_diff(dt)
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if minutes < 1:
        return "just now"
    elif minutes < 60:
        return f"{minutes} min ago" if minutes != 1 else "1 min ago"
    elif hours < 24:
        return f"{hours} hr ago" if hours != 1 else "1 hr ago"
    elif days < 30:
        return f"{days} days ago" if days != 1 else "1 day ago"
    else:
        months = days // 30
        return f"{months} months ago" if months != 1 else "1 month ago"

def calculate_minutes_ago(dt: Optional[datetime]) -> int:
    """
    Calculates how many minutes have elapsed since the action happened.
    """
    if dt is None:
        return 0
    diff = calculate_time_diff(dt)
    return int(diff.total_seconds() / 60)
