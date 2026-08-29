"""
TradeSignal NextGen — Alerts Repository
FNO alerts, premium spike records read/write. No business logic.
"""
import sqlite3
from datetime import datetime as dt
from core.db import get_db


def store_fno_alert(run_id: str, universe: str, mode: str,
                    result: dict, summary: dict,
                    db: sqlite3.Connection = None):
    import json
    _close = db is None
    if _close:
        db = get_db()
    db.execute(
        'INSERT INTO fno_alerts (run_id, scanned_at, universe, mode, result_json, summary_json) '
        'VALUES (?,?,?,?,?,?)',
        (run_id, dt.now().isoformat(), universe, mode,
         json.dumps(result), json.dumps(summary))
    )
    db.commit()
    if _close:
        db.close()


def get_recent_fno_alerts(limit: int = 50, db: sqlite3.Connection = None) -> list[dict]:
    import json
    _close = db is None
    if _close:
        db = get_db()
    rows = db.execute(
        'SELECT * FROM fno_alerts ORDER BY scanned_at DESC LIMIT ?', (limit,)
    ).fetchall()
    if _close:
        db.close()
    result = []
    for r in rows:
        row = dict(r)
        row['result'] = json.loads(row.pop('result_json', '{}'))
        row['summary'] = json.loads(row.pop('summary_json', '{}'))
        result.append(row)
    return result
