"""
TradeSignal NextGen — Week 6 Test Suite
Tests FNOTrapAgent, PredictionAgent, and routers/portfolio.py, screener.py, instruments.py, core.py.
"""
import os
import sys
import tempfile
import asyncio
import unittest
from unittest.mock import MagicMock

# Ensure backend root is on sys.path
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import core.db
from core.db import init_db, get_db
from core.event_bus import EventBus
from agents.fno_trap_agent import FNOTrapAgent
from agents.prediction_agent import PredictionAgent
from repositories import instruments as repo_instruments, journal as repo_journal

from routers.portfolio import portfolio_summary, portfolio_holdings, portfolio_positions, portfolio_margins
from routers.screener import screener_equity, screener_fno, screener_trap, screener_confluence
from routers.instruments import instruments_search, instruments_fno_symbols, instruments_cash_symbols, instruments_sync
from routers.core import health_check, system_status, list_notes, create_note, delete_note, NoteCreateRequest
from server import app


class TestWeek6PortfolioScreenerCore(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = core.db.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test_w6.db")
        os.close(self.temp_db_fd)
        core.db.DB_PATH = self.temp_db_path
        init_db(db_path=self.temp_db_path)
        self.db = get_db(db_path=self.temp_db_path)

        # Seed sample instruments
        repo_instruments.store_instruments([
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
            }
        ], db=self.db)

        self.bus = EventBus()
        self.mock_request = MagicMock()
        self.mock_request.app = app

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
        core.db.DB_PATH = self.orig_db_path

    def test_distinct_agents(self):
        """Verify FNOTrapAgent and PredictionAgent."""
        async def run_agent_tests():
            # 1. FNOTrapAgent
            trap_agent = FNOTrapAgent(self.bus)
            t_cards = await trap_agent.get_trap_cards("RELIANCE")
            self.assertEqual(t_cards["status"], "ok")
            self.assertEqual(t_cards["symbol"], "RELIANCE")

            t_sum = await trap_agent.get_trap_summary()
            self.assertEqual(t_sum["status"], "ok")

            # 2. PredictionAgent
            pred_agent = PredictionAgent(self.bus)
            pred_single = await pred_agent.get_predictions("RELIANCE")
            self.assertEqual(pred_single["status"], "ok")
            self.assertEqual(pred_single["prediction"]["direction"], "LONG")

            pred_all = await pred_agent.get_confluence_setups()
            self.assertEqual(pred_all["status"], "ok")
            self.assertGreater(pred_all["count"], 0)

        asyncio.run(run_agent_tests())

    def test_portfolio_router(self):
        """Verify routers/portfolio.py reusing KiteDataAgent."""
        async def run_port_tests():
            summary = await portfolio_summary(self.mock_request)
            self.assertEqual(summary["status"], "ok")
            self.assertIn("holdings", summary)

            holdings = await portfolio_holdings(self.mock_request)
            self.assertIn(holdings["status"], ("ok", "error"))

            positions = await portfolio_positions(self.mock_request)
            self.assertIn(positions["status"], ("ok", "error"))

            margins = await portfolio_margins(self.mock_request)
            self.assertIn(margins["status"], ("ok", "error"))

        asyncio.run(run_port_tests())

    def test_screener_and_instruments_router(self):
        """Verify routers/screener.py and routers/instruments.py."""
        async def run_screener_tests():
            # Screener endpoints
            eq = await screener_equity(self.mock_request)
            self.assertEqual(eq["status"], "ok")
            fno = await screener_fno(self.mock_request)
            self.assertEqual(fno["status"], "ok")
            tr = await screener_trap(self.mock_request, symbol="RELIANCE")
            self.assertEqual(tr["status"], "ok")
            conf = await screener_confluence(self.mock_request, symbol="RELIANCE")
            self.assertEqual(conf["status"], "ok")

            # Instruments endpoints
            s_res = await instruments_search(q="RELIANCE")
            self.assertEqual(s_res["status"], "ok")
            self.assertEqual(s_res["count"], 1)

            f_res = await instruments_fno_symbols()
            self.assertEqual(f_res["status"], "ok")
            c_res = await instruments_cash_symbols()
            self.assertEqual(c_res["status"], "ok")
            sync_res = await instruments_sync(self.mock_request)
            self.assertIn(sync_res["status"], ("ok", "error"))

        asyncio.run(run_screener_tests())

    def test_core_router_and_journal(self):
        """Verify routers/core.py health, system status, and notes CRUD."""
        async def run_core_tests():
            # Health
            h = await health_check()
            self.assertEqual(h["status"], "healthy")

            # Status
            st = await system_status(self.mock_request)
            self.assertEqual(st["status"], "ok")
            self.assertIn("total_agents", st)

            # Notes CRUD
            create_payload = NoteCreateRequest(
                title="Breakout Setup",
                content="Entered RELIANCE on 15m EMA golden cross",
                symbol="RELIANCE",
                sentiment="BULLISH"
            )
            c_resp = await create_note(create_payload)
            self.assertEqual(c_resp["status"], "ok")
            note_id = c_resp["id"]

            notes_resp = await list_notes(symbol="RELIANCE")
            self.assertEqual(notes_resp["status"], "ok")
            self.assertEqual(notes_resp["count"], 1)

            del_resp = await delete_note(note_id=note_id)
            self.assertEqual(del_resp["status"], "ok")

        asyncio.run(run_core_tests())


if __name__ == "__main__":
    unittest.main()
