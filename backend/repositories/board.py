"""
TradeSignal NextGen — Repository: board & snapshots
Reads EOD gainers snapshots, futures buildup snapshots, and EOD alert history from SQLite.
"""
import os
import sqlite3
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

CACHE_DB_PATH = os.environ.get(
    "CACHE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "tradesignal_cache.db")
)


def _get_cache_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(CACHE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_gainers_snapshot(date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the latest EOD Option Gainers Board snapshot from SQLite."""
    if not os.path.exists(CACHE_DB_PATH):
        return None
    try:
        conn = _get_cache_conn()
        cur = conn.cursor()
        if date_str:
            cur.execute(
                "SELECT snapshot_json FROM fno_gainers_snapshots WHERE snapshot_date = ?",
                (date_str,)
            )
        else:
            cur.execute(
                "SELECT snapshot_json FROM fno_gainers_snapshots ORDER BY snapshot_date DESC LIMIT 1"
            )
        row = cur.fetchone()
        conn.close()
        if row and row["snapshot_json"]:
            data = json.loads(row["snapshot_json"])
            if isinstance(data, dict):
                data["is_eod_snapshot"] = True
            return data
    except Exception as e:
        logger.warning(f"Error fetching gainers snapshot: {e}")
    return None


def get_latest_futures_buildup_snapshot(date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the latest Futures Buildup snapshot from SQLite."""
    if not os.path.exists(CACHE_DB_PATH):
        return None
    try:
        conn = _get_cache_conn()
        cur = conn.cursor()
        if date_str:
            cur.execute(
                "SELECT payload_json FROM fno_futures_buildup_snapshot WHERE date = ?",
                (date_str,)
            )
        else:
            cur.execute(
                "SELECT payload_json FROM fno_futures_buildup_snapshot ORDER BY id DESC LIMIT 1"
            )
        row = cur.fetchone()
        conn.close()
        if row and row["payload_json"]:
            return json.loads(row["payload_json"])
    except Exception as e:
        logger.warning(f"Error fetching futures buildup snapshot: {e}")
    return None


def get_eod_alerts(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve Prem Spikes and Live Breakouts from SQLite for EOD summary."""
    if not os.path.exists(CACHE_DB_PATH):
        return {"status": "ok", "prem_spikes": [], "live_breakouts": []}
    try:
        conn = _get_cache_conn()
        cur = conn.cursor()
        target_date = date_str
        if not target_date:
            cur.execute("SELECT snapshot_date FROM fno_gainers_snapshots ORDER BY snapshot_date DESC LIMIT 1")
            r = cur.fetchone()
            if r:
                target_date = r[0]

        prem_alerts = []
        if target_date:
            cur.execute(
                """SELECT id as seq, alert_time as time, symbol, tradingsymbol, opt_type, strike, ltp, old_ltp,
                          premium_spike_pct, board_gain_pct, open_prem, label
                   FROM premium_spike_alerts
                   WHERE alert_date = ? ORDER BY id DESC LIMIT 200""",
                (target_date,)
            )
            for row in cur.fetchall():
                d = dict(row)
                d["q"] = "A" if (d.get("premium_spike_pct") or 0) >= 30 else "B"
                prem_alerts.append(d)

        live_breakouts = []
        if target_date:
            cur.execute(
                """SELECT alert_date as date, alert_time as time, timestamp, symbol, direction, grade, ltp, vol_multiplier, move_pct, trigger_epoch
                   FROM live_breakout_alerts
                   WHERE alert_date = ? ORDER BY id DESC LIMIT 100""",
                (target_date,)
            )
            for row in cur.fetchall():
                live_breakouts.append(dict(row))

        conn.close()
        return {
            "status": "ok",
            "date": target_date,
            "prem_spikes": prem_alerts,
            "live_breakouts": live_breakouts,
            "total_alerts": len(prem_alerts) + len(live_breakouts),
            "alerts": prem_alerts,
            "count": len(prem_alerts) + len(live_breakouts)
        }
    except Exception as e:
        logger.warning(f"Error fetching EOD alerts: {e}")
        return {"status": "ok", "prem_spikes": [], "live_breakouts": []}
