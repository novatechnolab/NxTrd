"""
TradeSignal NextGen — News Repository
ALL stored_news read/write SQL queries live here. No business logic.
Ported from reference: server.py L8750-8850
"""
import sqlite3
from datetime import datetime as dt
from typing import List, Dict, Any
from core.db import get_db


def get_recent_news(limit: int = 50, db: sqlite3.Connection = None) -> List[Dict[str, Any]]:
    """Fetch most recent stored news ordered by timestamp DESC."""
    _close = db is None
    if _close:
        db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM stored_news ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if _close and db:
            db.close()


def store_news_items(news_items: List[Dict[str, Any]], db: sqlite3.Connection = None) -> int:
    """Upsert news items into stored_news."""
    if not news_items:
        return 0
    _close = db is None
    if _close:
        db = get_db()
    now = dt.now().isoformat()
    data = []
    for item in news_items:
        title = item.get("title", "").strip()
        if not title:
            continue
        data.append((
            title,
            item.get("summary", ""),
            item.get("source", ""),
            item.get("url", ""),
            item.get("sentiment", "NEUTRAL"),
            float(item.get("score", 0.0)),
            item.get("category", "GENERAL"),
            item.get("impact_rating", "LOW"),
            item.get("impacted_stocks", ""),
            item.get("takeaway", ""),
            int(item.get("priority_score", 0)),
            float(item.get("timestamp", dt.now().timestamp())),
            item.get("time", dt.now().strftime("%H:%M:%S")),
            now
        ))
    try:
        if data:
            db.executemany("""
                INSERT OR REPLACE INTO stored_news
                (title, summary, source, url, sentiment, score, category, impact_rating,
                 impacted_stocks, takeaway, priority_score, timestamp, time, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            db.commit()
            return len(data)
        return 0
    finally:
        if _close and db:
            db.close()
