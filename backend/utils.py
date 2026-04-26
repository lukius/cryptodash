from datetime import datetime


def utc_isoformat(dt: datetime) -> str:
    """Serialize a UTC datetime to ISO 8601 with explicit 'Z' suffix.

    Accepts naive UTC datetimes (as stored by SQLite's DateTime column) and
    UTC-aware datetimes (e.g. from datetime.now(timezone.utc)).  In both cases
    the output is an unambiguous UTC string that JavaScript's Date() parser
    treats as UTC rather than local time.
    """
    return dt.replace(tzinfo=None).isoformat() + "Z"
