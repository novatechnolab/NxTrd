"""
TradeSignal NextGen — OHLCV Repository
ALL OHLCV read/write SQL lives here. No business logic.
Agents call this. Routers do not touch this directly.
Ported from reference: server.py L837-901
"""
import sqlite3
from datetime import datetime as dt
from core.db import get_db


def get_ohlcv(token: int, from_date: str, to_date: str,
              interval: str = 'day', db: sqlite3.Connection = None) -> list[dict]:
    """Fetch OHLCV rows for a token in a date range."""
    _close = db is None
    if _close:
        db = get_db()
    is_intraday = interval in ('minute', '5minute', '15minute', '30minute', '60minute')
    to_q = to_date + "T23:59:59" if len(to_date) == 10 else to_date
    from_q = from_date.replace(' ', 'T') if is_intraday else from_date
    rows = db.execute(
        'SELECT date, open, high, low, close, volume FROM ohlcv '
        'WHERE instrument_token = ? AND interval = ? AND date >= ? AND date <= ? '
        'ORDER BY date',
        (token, interval, from_q, to_q)
    ).fetchall()
    if not rows and is_intraday:
        latest_rows = db.execute(
            'SELECT date, open, high, low, close, volume FROM ohlcv '
            'WHERE instrument_token = ? AND interval = ? '
            'ORDER BY date DESC LIMIT 150',
            (token, interval)
        ).fetchall()
        rows = list(reversed(latest_rows))
    if _close:
        db.close()
    return [dict(r) for r in rows]


def get_latest_date(token: int, interval: str = 'day',
                    db: sqlite3.Connection = None) -> str | None:
    """Get the most recent cached date for a token."""
    _close = db is None
    if _close:
        db = get_db()
    row = db.execute(
        'SELECT MAX(date) as d FROM ohlcv WHERE instrument_token = ? AND interval = ?',
        (token, interval)
    ).fetchone()
    if _close:
        db.close()
    return row['d'] if row and row['d'] else None


def store_ohlcv(token: int, candles: list, interval: str = 'day',
                db: sqlite3.Connection = None):
    """Upsert OHLCV candles into cache."""
    _close = db is None
    if _close:
        db = get_db()
    now = dt.now().isoformat()
    is_intraday = interval in ('minute', '5minute', '15minute', '30minute', '60minute')
    data = []
    for c in candles:
        if not isinstance(c, dict):
            continue
        date_val = c.get('date', '')
        if hasattr(date_val, 'isoformat'):
            date_val = date_val.isoformat()
        date_str = str(date_val) if is_intraday else str(date_val).split('T')[0]
        if not date_str:
            continue
        data.append((token, date_str, c.get('open', 0), c.get('high', 0),
                     c.get('low', 0), c.get('close', 0), c.get('volume', 0),
                     interval, now))
    if data:
        db.executemany(
            'INSERT OR REPLACE INTO ohlcv '
            '(instrument_token, date, open, high, low, close, volume, interval, fetched_at) '
            'VALUES (?,?,?,?,?,?,?,?,?)',
            data
        )
        db.commit()
    if _close:
        db.close()
