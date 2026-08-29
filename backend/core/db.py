"""
TradeSignal NextGen — Database Layer
SQLite WAL mode + proper time-series indexes.
Pure connection factory and schema initializer.
All read/write SQL queries live in the repositories/ layer.

Ported from reference: server.py L653-960
"""
import os
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

def _resolve_default_db() -> str:
    for cand in [
        os.path.join(os.path.dirname(__file__), "..", "tradesignal_cache.db"),
        os.path.join(os.path.dirname(__file__), "..", "tradesignal_nextgen.db"),
    ]:
        cand_path = os.path.abspath(cand)
        if os.path.isfile(cand_path) and os.path.getsize(cand_path) > 0:
            return cand_path
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tradesignal_cache.db"))

DB_PATH = os.environ.get("DB_PATH", _resolve_default_db())

# ── Index aliases for NSE symbol resolution ───────────────────────────
INDEX_ALIASES: dict[str, str] = {
    'NIFTY50':         'NIFTY 50',
    'NIFTY':           'NIFTY 50',
    'BANKNIFTY':       'NIFTY BANK',
    'NIFTYBANK':       'NIFTY BANK',
    'FINNIFTY':        'NIFTY FIN SERVICE',
    'NIFTYFINSERVICE': 'NIFTY FIN SERVICE',
    'INDIAVIX':        'INDIA VIX',
    'SENSEX':          'SENSEX',
}


def get_db(db_path: str = None) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and 64MB page cache (laptop & Termux parity)."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def init_db(db_path: str = None):
    """Create all tables and indexes. Called once on application startup."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS ohlcv (
            instrument_token INTEGER NOT NULL,
            date             TEXT NOT NULL,
            open             REAL NOT NULL,
            high             REAL NOT NULL,
            low              REAL NOT NULL,
            close            REAL NOT NULL,
            volume           INTEGER NOT NULL,
            interval         TEXT NOT NULL DEFAULT 'day',
            fetched_at       TEXT NOT NULL,
            PRIMARY KEY (instrument_token, date, interval)
        );

        CREATE TABLE IF NOT EXISTS instruments (
            instrument_token INTEGER PRIMARY KEY,
            exchange         TEXT,
            tradingsymbol    TEXT,
            name             TEXT,
            segment          TEXT,
            lot_size         INTEGER,
            instrument_type  TEXT,
            expiry           TEXT,
            strike           REAL,
            fetched_at       TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cache_meta (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fno_alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id       TEXT NOT NULL,
            scanned_at   TEXT NOT NULL,
            universe     TEXT NOT NULL,
            mode         TEXT NOT NULL,
            result_json  TEXT NOT NULL,
            summary_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            content       TEXT NOT NULL,
            symbol        TEXT,
            sentiment     TEXT DEFAULT 'NEUTRAL',
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            notion_page_id TEXT,
            sync_status   TEXT DEFAULT 'PENDING'
        );

        CREATE TABLE IF NOT EXISTS notion_config (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS rvol_baseline (
            symbol         TEXT PRIMARY KEY,
            average_volume REAL NOT NULL,
            date           TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stored_news (
            title          TEXT PRIMARY KEY,
            summary        TEXT,
            source         TEXT,
            url            TEXT,
            sentiment      TEXT,
            score          REAL,
            category       TEXT,
            impact_rating  TEXT,
            impacted_stocks TEXT,
            takeaway       TEXT,
            priority_score INTEGER,
            timestamp      REAL,
            time           TEXT,
            fetched_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fno_shareholding (
            symbol               TEXT PRIMARY KEY,
            quarter              TEXT NOT NULL,
            promoters            REAL,
            fii                  REAL,
            dii                  REAL,
            public               REAL,
            total_institutional  REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS first_hour_predictions (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            date                  TEXT NOT NULL,
            symbol                TEXT NOT NULL,
            pattern_key           TEXT NOT NULL,
            or_direction          TEXT NOT NULL,
            move_bucket           TEXT NOT NULL,
            predicted_outcome     TEXT NOT NULL,
            prediction_confidence REAL NOT NULL,
            or_high               REAL,
            or_low                REAL,
            or_close              REAL,
            actual_outcome        TEXT,
            validation_result     TEXT,
            status                TEXT NOT NULL DEFAULT 'PREDICTED',
            validated_at          TEXT,
            created_at            TEXT NOT NULL,
            UNIQUE(date, symbol)
        );

        CREATE TABLE IF NOT EXISTS fno_futures_buildup_snapshot (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT,
            timestamp    TEXT,
            payload_json TEXT
        );

        CREATE TABLE IF NOT EXISTS fno_gainers_snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT UNIQUE NOT NULL,
            snapshot_json TEXT NOT NULL,
            updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS premium_spike_alerts (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_date        TEXT NOT NULL,
            alert_time        TEXT NOT NULL,
            timestamp         REAL NOT NULL,
            token             INTEGER NOT NULL,
            symbol            TEXT NOT NULL,
            tradingsymbol     TEXT NOT NULL,
            opt_type          TEXT NOT NULL,
            strike            REAL NOT NULL,
            label             TEXT,
            layer             TEXT,
            direction         TEXT,
            open_prem         REAL,
            old_ltp           REAL,
            ltp               REAL,
            premium_spike_pct REAL,
            board_gain_pct    REAL,
            old_spot          REAL,
            spot              REAL,
            spot_spike_pct    REAL,
            interval_volume   INTEGER,
            consistency       REAL,
            is_eod_snapshot   INTEGER DEFAULT 0,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(alert_date, token, alert_time) ON CONFLICT IGNORE
        );

        CREATE TABLE IF NOT EXISTS live_breakout_alerts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_date     TEXT NOT NULL,
            alert_time     TEXT NOT NULL,
            timestamp      REAL NOT NULL,
            symbol         TEXT NOT NULL,
            direction      TEXT,
            grade          TEXT,
            ltp            REAL,
            vol_multiplier REAL,
            move_pct       REAL,
            trigger_epoch  REAL,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(alert_date, symbol, grade, alert_time) ON CONFLICT IGNORE
        );

        CREATE TABLE IF NOT EXISTS oi_spurt_log (
            date          TEXT NOT NULL,
            symbol        TEXT NOT NULL,
            spurt_time    TEXT NOT NULL,
            oi_change_pct REAL NOT NULL,
            PRIMARY KEY (date, symbol)
        );

        -- Time-series indexes — critical for latency parity on queries
        CREATE INDEX IF NOT EXISTS idx_ohlcv_token_interval ON ohlcv(instrument_token, interval);
        CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON ohlcv(date);
        CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_ts ON ohlcv(instrument_token, date DESC);
        CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(tradingsymbol, exchange);
        CREATE INDEX IF NOT EXISTS idx_instruments_segment ON instruments(segment);
        CREATE INDEX IF NOT EXISTS idx_fno_alerts_time ON fno_alerts(scanned_at);
        CREATE INDEX IF NOT EXISTS idx_stored_news_time ON stored_news(timestamp);
        CREATE INDEX IF NOT EXISTS idx_ffbs_date ON fno_futures_buildup_snapshot(date);
        CREATE INDEX IF NOT EXISTS idx_fgs_date ON fno_gainers_snapshots(snapshot_date);
        CREATE INDEX IF NOT EXISTS idx_psa_date ON premium_spike_alerts(alert_date);
        CREATE INDEX IF NOT EXISTS idx_psa_symbol ON premium_spike_alerts(symbol);
        CREATE INDEX IF NOT EXISTS idx_lba_date ON live_breakout_alerts(alert_date);
        CREATE INDEX IF NOT EXISTS idx_lba_symbol ON live_breakout_alerts(symbol);
        CREATE INDEX IF NOT EXISTS idx_osl_date ON oi_spurt_log(date);
    ''')
    conn.commit()

    # Seed fno_shareholding if JSON seed file exists
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fno_shareholding")
        if cursor.fetchone()[0] == 0:
            seed_path = os.path.join(os.path.dirname(__file__), '..', 'fno_shareholding.json')
            if os.path.exists(seed_path):
                with open(seed_path) as f:
                    seed_data = json.load(f)
                records = [
                    (r.get("symbol"), r.get("quarter"), r.get("promoters", 0.0),
                     r.get("fii", 0.0), r.get("dii", 0.0), r.get("public", 0.0),
                     r.get("total_institutional", 0.0))
                    for r in seed_data
                ]
                conn.executemany("""
                    INSERT OR REPLACE INTO fno_shareholding
                    (symbol, quarter, promoters, fii, dii, public, total_institutional, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, records)
                conn.commit()
                logger.info(f"Seeded fno_shareholding with {len(records)} records")
    except Exception as e:
        logger.warning(f"fno_shareholding seed skipped: {e}")

    conn.close()
    logger.info(f"DB initialized at: {target_path}")


def get_cache_stats(db_path: str = None) -> dict:
    """Compute OHLCV and instruments cache stats for UI DataCache card."""
    target_path = db_path or DB_PATH
    conn = get_db(target_path)
    try:
        cur = conn.cursor()
        ohlcv_count = cur.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]
        instruments_count = cur.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
        unique_tokens = cur.execute("SELECT COUNT(DISTINCT instrument_token) FROM ohlcv").fetchone()[0]
        db_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
        return {
            "status": "ok",
            "ohlcv_candles": ohlcv_count,
            "instruments": instruments_count,
            "unique_tokens": unique_tokens,
            "db_size_mb": round(db_size / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.warning(f"Error computing cache stats: {e}")
        return {
            "status": "ok",
            "ohlcv_candles": 0,
            "instruments": 0,
            "unique_tokens": 0,
            "db_size_mb": 0.0
        }
    finally:
        conn.close()


def clear_ohlcv_cache(db_path: str = None) -> dict:
    """Clear OHLCV table cache."""
    target_path = db_path or DB_PATH
    conn = get_db(target_path)
    try:
        conn.execute("DELETE FROM ohlcv")
        conn.commit()
        return {"status": "ok", "message": "OHLCV cache cleared successfully"}
    finally:
        conn.close()

