"""
TradeSignal NextGen — Instruments Repository
ALL instruments read/write SQL queries live here. No business logic.
Ported from reference: server.py L904-958 & db_instruments.py
"""
import sqlite3
from datetime import datetime as dt
from typing import Optional, List, Dict, Any
from core.db import get_db, INDEX_ALIASES
import logging

logger = logging.getLogger(__name__)


def resolve_token(symbol: str, db: sqlite3.Connection = None) -> Optional[int]:
    """
    Symbol → instrument_token resolver.
    Priority: NSE equity → NSE index alias → BSE equity.
    Returns None if not found. Never hardcodes fallback tokens.
    """
    if not symbol:
        return None
    sym = symbol.strip().upper()
    _close = db is None
    if _close:
        db = get_db()
    try:
        for tradingsymbol in [sym, INDEX_ALIASES.get(sym)]:
            if not tradingsymbol:
                continue
            row = db.execute(
                "SELECT instrument_token FROM instruments "
                "WHERE tradingsymbol = ? AND exchange = 'NSE' LIMIT 1",
                (tradingsymbol,)
            ).fetchone()
            if row:
                return int(row[0])
        row = db.execute(
            "SELECT instrument_token FROM instruments "
            "WHERE tradingsymbol = ? AND exchange = 'BSE' LIMIT 1", (sym,)
        ).fetchone()
        if row:
            return int(row[0])
    except Exception as e:
        logger.warning(f"resolve_token failed for '{sym}': {e}")
    finally:
        if _close and db:
            db.close()
    return None


def store_instruments(instruments_list: List[Dict[str, Any]], db: sqlite3.Connection = None):
    """Bulk upsert instruments. Clears stale data first."""
    _close = db is None
    if _close:
        db = get_db()
    now = dt.now().isoformat()
    data = []
    for i in instruments_list:
        expiry = i.get('expiry', '')
        if hasattr(expiry, 'isoformat'):
            expiry = expiry.isoformat()
        data.append((
            i.get('instrument_token', 0), i.get('exchange', ''),
            i.get('tradingsymbol', ''), i.get('name', ''),
            i.get('segment', ''), i.get('lot_size', 0),
            i.get('instrument_type', ''), str(expiry),
            i.get('strike', 0), now
        ))
    if data:
        db.execute('DELETE FROM instruments')
        db.executemany(
            'INSERT OR REPLACE INTO instruments '
            '(instrument_token, exchange, tradingsymbol, name, segment, '
            'lot_size, instrument_type, expiry, strike, fetched_at) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            data
        )
        db.execute(
            'INSERT OR REPLACE INTO cache_meta (key, value, updated_at) VALUES (?,?,?)',
            ('instruments_fetched', now, now)
        )
        db.commit()
    if _close:
        db.close()


def get_all(db: sqlite3.Connection = None) -> List[Dict[str, Any]]:
    """Fetch all instruments in SQLite."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        rows = db.execute('SELECT * FROM instruments').fetchall()
        return [dict(r) for r in rows]
    finally:
        if _close and db:
            db.close()


def get_cached_instruments(exchange: str = "NFO", db: sqlite3.Connection = None) -> List[Dict[str, Any]]:
    """Fetch cached instruments from SQLite for the specified exchange."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM instruments WHERE exchange = ?", (exchange,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[DB Instruments] Error loading instruments for {exchange}: {e}")
        return []
    finally:
        if _close and db:
            db.close()


def get_instrument_by_symbol(symbol: str, exchange: str = "NFO", db: sqlite3.Connection = None) -> Optional[Dict[str, Any]]:
    """Fetch a single instrument by tradingsymbol and exchange."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM instruments WHERE tradingsymbol = ? AND exchange = ? LIMIT 1",
            (symbol, exchange)
        ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"[DB Instruments] Error loading symbol {symbol} ({exchange}): {e}")
        return None
    finally:
        if _close and db:
            db.close()


def get_fno_symbols(db: sqlite3.Connection = None) -> List[str]:
    """Fetch distinct F&O underlying names (from NFO-FUT)."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        rows = db.execute(
            "SELECT DISTINCT name FROM instruments WHERE exchange = 'NFO' AND segment = 'NFO-FUT'"
        ).fetchall()
        return [r[0].upper() for r in rows if r[0]]
    except Exception as e:
        logger.error(f"[DB Instruments] Error loading F&O symbols: {e}")
        return []
    finally:
        if _close and db:
            db.close()


def get_cash_only_symbols(db: sqlite3.Connection = None) -> List[str]:
    """Fetch list of Cash-only (non-F&O) stock trading symbols from NSE."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        fno_names = set(get_fno_symbols(db=db))
        rows = db.execute(
            "SELECT DISTINCT tradingsymbol FROM instruments WHERE exchange = 'NSE' AND instrument_type = 'EQ'"
        ).fetchall()
        symbols = []
        for r in rows:
            sym = r[0].upper()
            if sym in fno_names:
                continue
            if any(sym.endswith(suffix) for suffix in ["-BE", "-BZ", "-ST", "-TF", "-DE", "-SG"]):
                continue
            symbols.append(sym)
        return sorted(symbols)
    except Exception as e:
        logger.error(f"[DB Instruments] Error loading cash symbols: {e}")
        return []
    finally:
        if _close and db:
            db.close()


def is_fresh(max_age_hours: int = 12, db: sqlite3.Connection = None) -> bool:
    """Check if cached instruments were updated within max_age_hours."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        row = db.execute(
            'SELECT value FROM cache_meta WHERE key = ?', ('instruments_fetched',)
        ).fetchone()
        if not row:
            return False
        fetched = dt.fromisoformat(row['value'])
        return (dt.now() - fetched).total_seconds() < max_age_hours * 3600
    except (ValueError, TypeError):
        return False
    finally:
        if _close and db:
            db.close()
