"""
TradeSignal NextGen — Journal & Notes Repository
ALL SQL queries for notes and trading journal records live here. No business logic.
Ported from reference: server.py L7765-8172
"""
import sqlite3
from datetime import datetime as dt
from typing import Optional, List, Dict, Any
from core.db import get_db


def get_all_notes(symbol: Optional[str] = None, db: sqlite3.Connection = None) -> List[Dict[str, Any]]:
    """Retrieve all notes, optionally filtered by symbol, ordered by updated_at DESC."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        if symbol:
            rows = db.execute(
                "SELECT * FROM notes WHERE symbol = ? ORDER BY updated_at DESC",
                (symbol.strip().upper(),)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        if _close and db:
            db.close()


def add_note(title: str, content: str, symbol: Optional[str] = None,
             sentiment: str = "NEUTRAL", db: sqlite3.Connection = None) -> int:
    """Insert a new note and return the created note ID."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        now = dt.now().isoformat()
        sym = symbol.strip().upper() if symbol else None
        cur = db.execute(
            "INSERT INTO notes (title, content, symbol, sentiment, created_at, updated_at, sync_status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'PENDING')",
            (title, content, sym, sentiment, now, now)
        )
        db.commit()
        return cur.lastrowid
    finally:
        if _close and db:
            db.close()


def update_note(note_id: int, title: str, content: str, symbol: Optional[str] = None,
                sentiment: str = "NEUTRAL", db: sqlite3.Connection = None) -> bool:
    """Update an existing note by ID."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        now = dt.now().isoformat()
        sym = symbol.strip().upper() if symbol else None
        cur = db.execute(
            "UPDATE notes SET title = ?, content = ?, symbol = ?, sentiment = ?, updated_at = ?, sync_status = 'PENDING' "
            "WHERE id = ?",
            (title, content, sym, sentiment, now, note_id)
        )
        db.commit()
        return cur.rowcount > 0
    finally:
        if _close and db:
            db.close()


def delete_note(note_id: int, db: sqlite3.Connection = None) -> bool:
    """Delete a note by ID."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        cur = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        db.commit()
        return cur.rowcount > 0
    finally:
        if _close and db:
            db.close()
