"""
TradeSignal NextGen — Week 8 Test Suite
Tests WebSocket ConnectionManager, Delta Computation, and fno_backend Traction Quadrant Integration.
"""
import os
import sys
import tempfile
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

# Ensure backend root is on sys.path
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import core.db
from core.db import init_db, get_db
from core.event_bus import EventBus
from agents.board_agent import BoardAgent
from routers.ws import ConnectionManager, compute_delta


class TestWeek8WsDeltaFno(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = core.db.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test_w8.db")
        os.close(self.temp_db_fd)
        core.db.DB_PATH = self.temp_db_path
        init_db(db_path=self.temp_db_path)
        self.db = get_db(db_path=self.temp_db_path)

        self.bus = EventBus()

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
        core.db.DB_PATH = self.orig_db_path

    def test_compute_delta(self):
        """Verify incremental delta computation returns only modified rows."""
        prev = {
            "RELIANCE": {"ltp": 2500.0, "gain_pct": 2.5},
            "TCS": {"ltp": 3800.0, "gain_pct": 1.2}
        }
        curr = {
            "RELIANCE": {"ltp": 2510.0, "gain_pct": 2.9},  # modified
            "TCS": {"ltp": 3800.0, "gain_pct": 1.2},       # unchanged
            "INFY": {"ltp": 1600.0, "gain_pct": 0.8}       # new
        }

        delta = compute_delta(prev, curr)
        self.assertEqual(len(delta), 2)
        symbols_in_delta = {d["symbol"] for d in delta}
        self.assertIn("RELIANCE", symbols_in_delta)
        self.assertIn("INFY", symbols_in_delta)
        self.assertNotIn("TCS", symbols_in_delta)

    def test_connection_manager(self):
        """Verify WebSocket ConnectionManager connect, disconnect, and broadcast."""
        async def run_ws_tests():
            cm = ConnectionManager()
            mock_ws_1 = AsyncMock()
            mock_ws_2 = AsyncMock()

            # Connect clients
            await cm.connect(mock_ws_1, topics=["signals"])
            await cm.connect(mock_ws_2, topics=["alerts"])
            self.assertEqual(cm.total_clients, 2)

            # Broadcast to "signals" topic
            await cm.broadcast_json({"type": "signal_event", "symbol": "RELIANCE"}, topic="signals")
            mock_ws_1.send_json.assert_awaited_once()
            mock_ws_2.send_json.assert_not_awaited()

            # Disconnect client
            cm.disconnect(mock_ws_1)
            self.assertEqual(cm.total_clients, 1)

        asyncio.run(run_ws_tests())

    def test_fno_traction_quadrant_metrics(self):
        """Verify Traction Quadrant logic ported from fno_backend."""
        # 1. Confirm Up
        q_up = BoardAgent.compute_traction_quadrant("Uptrend", "ACCUMULATION", 1.5)
        self.assertEqual(q_up, "confirm-up")

        # 2. Confirm Down
        q_down = BoardAgent.compute_traction_quadrant("Downtrend", "DISTRIBUTION", 1.3)
        self.assertEqual(q_down, "confirm-down")

        # 3. Divergence Bull
        q_div_bull = BoardAgent.compute_traction_quadrant("Downtrend", "ACCUMULATION", 1.1)
        self.assertEqual(q_div_bull, "div-bull")

        # 4. Divergence Bear
        q_div_bear = BoardAgent.compute_traction_quadrant("Uptrend", "DISTRIBUTION", 1.0)
        self.assertEqual(q_div_bear, "div-bear")

    def test_traction_board_with_quadrants(self):
        """Verify BoardAgent.get_traction_board includes traction_quadrant."""
        async def run_board_test():
            agent = BoardAgent(self.bus)
            res = await agent.get_traction_board(symbols=["RELIANCE", "TCS"], period=60)
            self.assertEqual(res["status"], "ok")
            self.assertEqual(len(res["data"]), 2)
            for row in res["data"]:
                self.assertIn("traction_quadrant", row)
                self.assertIn("conviction_score", row)
                self.assertIn("delivery_conviction", row)

        asyncio.run(run_board_test())


if __name__ == "__main__":
    unittest.main()
