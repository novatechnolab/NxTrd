"""
TradeSignal NextGen — Week 2 Test Suite
Tests Core Infrastructure and Repositories Layer.
"""
import os
import sys
import tempfile
import asyncio
import unittest

# Ensure backend root is on sys.path
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from core.db import get_db, init_db, INDEX_ALIASES
from core.session_utils import (
    save_kite_session, load_kite_session, clear_kite_session,
    get_kite_credentials, kite_session_debug
)
from core.event_bus import EventBus
from core.utils import now_ist, normalize_timestamp
from repositories import (
    instruments as repo_instruments,
    ohlcv as repo_ohlcv,
    alerts as repo_alerts,
    news as repo_news,
    journal as repo_journal
)


class TestWeek2CoreAndRepositories(unittest.TestCase):

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test.db")
        os.close(self.temp_db_fd)
        init_db(db_path=self.temp_db_path)
        self.db = get_db(db_path=self.temp_db_path)

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_database_initialization_and_wal(self):
        """Verify all tables and WAL mode are initialized."""
        tables = [
            r[0] for r in self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        self.assertIn("ohlcv", tables)
        self.assertIn("instruments", tables)
        self.assertIn("fno_alerts", tables)
        self.assertIn("notes", tables)
        self.assertIn("stored_news", tables)
        self.assertIn("fno_shareholding", tables)

        # Check WAL mode
        mode = self.db.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(mode.lower(), "wal")

    def test_instruments_repository_and_token_resolution(self):
        """Verify instrument storage, index aliases, and token resolution."""
        sample_instruments = [
            {
                "instrument_token": 738561,
                "exchange": "NSE",
                "tradingsymbol": "RELIANCE",
                "name": "RELIANCE",
                "segment": "NSE-EQ",
                "lot_size": 1,
                "instrument_type": "EQ",
                "strike": 0,
                "expiry": ""
            },
            {
                "instrument_token": 256265,
                "exchange": "NSE",
                "tradingsymbol": "NIFTY 50",
                "name": "NIFTY 50",
                "segment": "INDICES",
                "lot_size": 50,
                "instrument_type": "EQ",
                "strike": 0,
                "expiry": ""
            },
            {
                "instrument_token": 123456,
                "exchange": "NFO",
                "tradingsymbol": "NIFTY24AUGFUT",
                "name": "NIFTY",
                "segment": "NFO-FUT",
                "lot_size": 50,
                "instrument_type": "FUT",
                "strike": 0,
                "expiry": "2026-08-28"
            }
        ]
        repo_instruments.store_instruments(sample_instruments, db=self.db)

        # Standard token lookup
        token = repo_instruments.resolve_token("RELIANCE", db=self.db)
        self.assertEqual(token, 738561)

        # Alias resolution (NIFTY50 -> NIFTY 50)
        nifty_token = repo_instruments.resolve_token("NIFTY50", db=self.db)
        self.assertEqual(nifty_token, 256265)

        # Non-existent token returns None
        none_token = repo_instruments.resolve_token("UNKNOWN_SYM", db=self.db)
        self.assertIsNone(none_token)

        # F&O symbols list
        fno_syms = repo_instruments.get_fno_symbols(db=self.db)
        self.assertIn("NIFTY", fno_syms)

        # Freshness check
        self.assertTrue(repo_instruments.is_fresh(max_age_hours=1, db=self.db))

    def test_ohlcv_repository(self):
        """Verify storing and querying OHLCV candles."""
        candles = [
            {"date": "2026-08-27T09:15:00", "open": 2500, "high": 2510, "low": 2490, "close": 2505, "volume": 10000},
            {"date": "2026-08-28T09:15:00", "open": 2505, "high": 2520, "low": 2500, "close": 2515, "volume": 15000}
        ]
        repo_ohlcv.store_ohlcv(738561, candles, interval="day", db=self.db)

        rows = repo_ohlcv.get_ohlcv(738561, "2026-08-27", "2026-08-28", interval="day", db=self.db)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["close"], 2505)
        self.assertEqual(rows[1]["close"], 2515)

        latest_date = repo_ohlcv.get_latest_date(738561, interval="day", db=self.db)
        self.assertEqual(latest_date, "2026-08-28")

    def test_alerts_repository(self):
        """Verify storing and retrieving FNO alerts."""
        repo_alerts.store_fno_alert(
            run_id="run_001",
            universe="NIFTY50",
            mode="intraday",
            result={"symbol": "RELIANCE", "spike": 15.2},
            summary={"total_signals": 1},
            db=self.db
        )
        alerts = repo_alerts.get_recent_fno_alerts(limit=10, db=self.db)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["run_id"], "run_001")
        self.assertEqual(alerts[0]["result"]["symbol"], "RELIANCE")

    def test_journal_repository(self):
        """Verify notes CRUD operations in Journal repository."""
        note_id = repo_journal.add_note("Test Note", "Bullish setup on Reliance", symbol="RELIANCE", sentiment="BULLISH", db=self.db)
        self.assertGreater(note_id, 0)

        notes = repo_journal.get_all_notes(symbol="RELIANCE", db=self.db)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["title"], "Test Note")

        updated = repo_journal.update_note(note_id, "Updated Note", "Target achieved", symbol="RELIANCE", sentiment="BULLISH", db=self.db)
        self.assertTrue(updated)

        notes_updated = repo_journal.get_all_notes(symbol="RELIANCE", db=self.db)
        self.assertEqual(notes_updated[0]["title"], "Updated Note")

        deleted = repo_journal.delete_note(note_id, db=self.db)
        self.assertTrue(deleted)
        self.assertEqual(len(repo_journal.get_all_notes(symbol="RELIANCE", db=self.db)), 0)

    def test_news_repository(self):
        """Verify news items storage and query."""
        news = [{
            "title": "Reliance Q2 Results Announced",
            "summary": "Revenue up 12% YoY",
            "source": "Moneycontrol",
            "sentiment": "POSITIVE",
            "score": 0.85
        }]
        stored_count = repo_news.store_news_items(news, db=self.db)
        self.assertEqual(stored_count, 1)

        recent = repo_news.get_recent_news(limit=5, db=self.db)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["title"], "Reliance Q2 Results Announced")

    def test_session_utils(self):
        """Verify Kite session disk save, load, and clear."""
        clear_kite_session()
        self.assertTrue(save_kite_session("test_api_key_123", "test_access_token_456"))
        k, t = load_kite_session()
        self.assertEqual(k, "test_api_key_123")
        self.assertEqual(t, "test_access_token_456")

        cred_k, cred_t = get_kite_credentials(request=None)
        self.assertEqual(cred_k, "test_api_key_123")
        self.assertEqual(cred_t, "test_access_token_456")

        dbg = kite_session_debug(request=None)
        self.assertTrue(dbg["has_disk_api_key"])
        self.assertTrue(dbg["has_disk_access_token"])

        clear_kite_session()
        k_cleared, t_cleared = load_kite_session()
        self.assertIsNone(k_cleared)
        self.assertIsNone(t_cleared)

    def test_event_bus(self):
        """Verify EventBus async queue pub/sub."""
        async def run_bus_test():
            bus = EventBus()
            queue = bus.subscribe("TICK")
            await bus.put("TICK", {"sym": "RELIANCE", "ltp": 2510})
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            self.assertEqual(event["sym"], "RELIANCE")
            self.assertEqual(event["ltp"], 2510)

        asyncio.run(run_bus_test())

    def test_utils(self):
        """Verify IST timezone and formatting helpers."""
        t_ist = now_ist()
        self.assertIsNotNone(t_ist)
        norm = normalize_timestamp(t_ist)
        self.assertTrue(":" in norm)


if __name__ == "__main__":
    unittest.main()
