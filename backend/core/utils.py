"""
TradeSignal NextGen — Shared Utilities
Provides IST time helpers and Indian market hours status checks.
"""
from datetime import datetime, time
import pytz

IST = pytz.timezone("Asia/Kolkata")


def now_ist() -> datetime:
    """Return current datetime in Asia/Kolkata timezone."""
    return datetime.now(IST)


def normalize_timestamp(ts) -> str:
    """Convert datetime or string to HH:MM:SS format."""
    if isinstance(ts, datetime):
        return ts.astimezone(IST).strftime("%H:%M:%S")
    return str(ts)


def is_weekend() -> bool:
    """Check if today is Saturday (5) or Sunday (6)."""
    return now_ist().weekday() in (5, 6)


def is_premarket() -> bool:
    """Check if current time is within pre-market window (09:00 - 09:15 IST on weekdays)."""
    if is_weekend():
        return False
    current_time = now_ist().time()
    return time(9, 0) <= current_time < time(9, 15)


def is_market_hours() -> bool:
    """Check if current time is within live NSE market hours (09:15 - 15:40 IST on weekdays)."""
    if is_weekend():
        return False
    current_time = now_ist().time()
    return time(9, 15) <= current_time <= time(15, 40)
