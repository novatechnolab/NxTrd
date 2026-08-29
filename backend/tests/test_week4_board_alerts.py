"""
TradeSignal NextGen — Week 4 Test Suite
Tests BoardAgent, PremiumSpikeAgent, and routers/board.py, alerts.py, futures.py.
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
from agents.board_agent import BoardAgent
from agents.premium_spike_agent import PremiumSpikeAgent
from agents.base_agent import AgentState
from repositories import instruments as repo_instruments, alerts as repo_alerts
from routers.board import option_gainers_board, option_gainers_timeline, traction_board, TractionBoardRequest
from routers.alerts import (
    option_gainers_alerts, option_gainers_alerts_status,
    option_gainers_alerts_clear, eod_alert_summary
)
from routers.futures import futures_buildup
from server import app


class TestWeek4BoardAndAlerts(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = core.db.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test_w4.db")
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
            },
            {
                "instrument_token": 123456,
                "exchange": "NFO",
                "tradingsymbol": "RELIANCE24AUGFUT",
                "name": "RELIANCE",
                "segment": "NFO-FUT",
                "lot_size": 250,
                "instrument_type": "FUT",
                "strike": 0,
                "expiry": "2026-08-28"
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

    def test_board_agent_methods(self):
        """Verify BoardAgent methods for gainers, timeline, buildup, and traction."""
        async def run_board_tests():
            agent = BoardAgent(self.bus)

            # 1. Gainers board
            board_data = await agent.get_gainers_board()
            self.assertEqual(board_data["status"], "ok")
            self.assertIn("stocks", board_data)

            # 2. Contract timeline
            timeline = await agent.get_contract_timeline(symbol="RELIANCE", strike=2500, opt_type="CE")
            self.assertTrue(timeline["success"])
            self.assertEqual(timeline["symbol"], "RELIANCE")

            # 3. Futures buildup
            buildup = await agent.get_fut_buildup()
            self.assertEqual(buildup["status"], "ok")
            self.assertGreater(buildup["count"], 0)

            # 4. Traction board
            traction = await agent.get_traction_board(symbols=["RELIANCE"], period=60, cap="large")
            self.assertEqual(traction["status"], "ok")
            self.assertEqual(traction["total_stocks"], 1)

        asyncio.run(run_board_tests())

    def test_premium_spike_agent_methods(self):
        """Verify PremiumSpikeAgent alert recording, FSM transition, status, and clear."""
        async def run_spike_tests():
            agent = PremiumSpikeAgent(self.bus)
            self.assertEqual(agent.state, AgentState.IDLE)

            # Record spike alert
            agent.record_spike(symbol="RELIANCE", strike=2500.0, opt_type="CE", spike_pct=35.0, ltp=45.0)
            self.assertEqual(agent.state, AgentState.TRIGGERED)

            # Retrieve recent alerts
            alerts = await agent.get_recent_alerts()
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]["symbol"], "RELIANCE")
            self.assertEqual(alerts[0]["spike_pct"], 35.0)

            # Status check
            status = await agent.get_alert_status()
            self.assertEqual(status["total_alerts"], 1)

            # Clear alerts
            cleared = await agent.clear_alerts()
            self.assertTrue(cleared)
            alerts_after_clear = await agent.get_recent_alerts()
            self.assertEqual(len(alerts_after_clear), 0)

        asyncio.run(run_spike_tests())

    def test_routers_board_alerts_futures(self):
        """Verify router endpoint delegations for Board, Alerts, and Futures."""
        async def run_router_tests():
            # 1. Option Gainers Board endpoint
            g_resp = await option_gainers_board(self.mock_request)
            self.assertEqual(g_resp["status"], "ok")

            # 2. Timeline endpoint
            tl_resp = await option_gainers_timeline(self.mock_request, symbol="RELIANCE", strike=2500.0)
            self.assertTrue(tl_resp["success"])

            # 3. Traction Board endpoint
            tr_resp = await traction_board(self.mock_request, symbols="RELIANCE,TCS", period=60)
            self.assertEqual(tr_resp["status"], "ok")
            self.assertEqual(tr_resp["total_stocks"], 2)

            # 4. Alerts endpoints
            al_resp = await option_gainers_alerts(self.mock_request)
            self.assertIn("alerts", al_resp)
            st_resp = await option_gainers_alerts_status(self.mock_request)
            self.assertEqual(st_resp["status"], "ok")
            cl_resp = await option_gainers_alerts_clear(self.mock_request)
            self.assertTrue(cl_resp["ok"])
            eod_resp = await eod_alert_summary(self.mock_request)
            self.assertEqual(eod_resp["status"], "ok")

            # 5. Futures Buildup endpoint
            fut_resp = await futures_buildup(self.mock_request)
            self.assertEqual(fut_resp["status"], "ok")

        asyncio.run(run_router_tests())


if __name__ == "__main__":
    unittest.main()
