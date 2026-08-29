"""
TradeSignal NextGen — Week 3 Test Suite
Tests BaseAgent FSM, AgentOrchestrator, KiteDataAgent, and routers/kite.py async endpoint handlers.
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
from core.session_utils import clear_kite_session, save_kite_session
from agents.base_agent import BaseAgent, AgentState
from agents.orchestrator import AgentOrchestrator
from agents.kite_data_agent import KiteDataAgent
from repositories import instruments as repo_instruments, ohlcv as repo_ohlcv
from routers.kite import (
    kite_auth, kite_auth_session, kite_auth_status, kite_auth_logout,
    kite_historical, kite_quote, kite_ltp, kite_instruments,
    kite_ws_start, kite_ws_stop, kite_ws_snapshot,
    AuthRequest, WsStartRequest
)
from server import app


class DummyTestAgent(BaseAgent):
    name = "dummy_agent"
    category = "test"

    async def run(self):
        self.transition(AgentState.MONITORING)
        self.record_cycle()
        await self.publish("TEST_EVENT", {"msg": "hello"})


class TestWeek3KiteAndAgents(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = core.db.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test_w3.db")
        os.close(self.temp_db_fd)
        core.db.DB_PATH = self.temp_db_path
        init_db(db_path=self.temp_db_path)
        self.db = get_db(db_path=self.temp_db_path)
        clear_kite_session()

        # Seed sample instrument and candle
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
                "instrument_token": 256265,
                "exchange": "NSE",
                "tradingsymbol": "NIFTY 50",
                "name": "NIFTY 50",
                "segment": "INDICES",
                "lot_size": 50,
                "instrument_type": "EQ",
                "strike": 0,
                "expiry": ""
            }
        ], db=self.db)
        repo_ohlcv.store_ohlcv(738561, [
            {"date": "2026-08-28T09:15:00", "open": 2500, "high": 2510, "low": 2490, "close": 2505, "volume": 10000}
        ], interval="5minute", db=self.db)

        self.bus = EventBus()
        self.mock_request = MagicMock()
        self.mock_request.app = app
        self.mock_request.headers = {}

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
        core.db.DB_PATH = self.orig_db_path
        clear_kite_session()

    def test_base_agent_fsm_and_metrics(self):
        """Verify BaseAgent states, transitions, time in state, and status dict."""
        agent = DummyTestAgent(self.bus)
        self.assertEqual(agent.state, AgentState.IDLE)
        self.assertEqual(agent.name, "dummy_agent")

        agent.transition(AgentState.MONITORING)
        self.assertEqual(agent.state, AgentState.MONITORING)
        self.assertGreaterEqual(agent.time_in_state(), 0.0)

        agent.record_cycle()
        agent.record_error("Test exception")
        self.assertEqual(agent.state, AgentState.ERROR)

        status = agent.get_status()
        self.assertEqual(status["state"], "ERROR")
        self.assertEqual(status["error_count"], 1)
        self.assertEqual(status["cycles_completed"], 1)
        self.assertEqual(status["last_error"], "Test exception")

    def test_agent_orchestrator_lifecycle(self):
        """Verify orchestrator registers, starts, collects health, and stops agents."""
        async def run_orchestrator():
            orch = AgentOrchestrator(self.bus)
            agent = DummyTestAgent(self.bus)
            orch.register(agent)
            self.assertIsNotNone(orch.get_agent("dummy_agent"))

            await orch.start()
            health = orch.get_health_status()
            self.assertTrue(health["orchestrator_running"])
            self.assertEqual(health["total_agents"], 1)
            self.assertIn("dummy_agent", health["agents"])

            await orch.stop()
            self.assertFalse(orch._running)

        asyncio.run(run_orchestrator())

    def test_kite_data_agent_methods_and_ticks(self):
        """Verify KiteDataAgent initialization, offline handling, and tick ingestion."""
        async def run_kite_agent():
            agent = KiteDataAgent(self.bus)
            self.assertFalse(agent.is_authenticated())

            # Offline historical query with fallback to SQLite cache
            res = await agent.get_historical(symbol="RELIANCE", token=738561, interval="5minute")
            self.assertEqual(res["status"], "ok")

            # Tick processing
            sample_ticks = [
                {"instrument_token": 738561, "last_price": 2515.5, "volume": 12000}
            ]
            agent.handle_ticks(sample_ticks)
            snapshot = agent.get_tick_snapshot()
            self.assertEqual(snapshot["count"], 1)
            self.assertEqual(snapshot["ticks"][738561]["ltp"], 2515.5)

            # Ticker control
            start_res = agent.start_ws([738561])
            self.assertEqual(start_res["status"], "ok")
            stop_res = agent.stop_ws()
            self.assertEqual(stop_res["status"], "ok")

        asyncio.run(run_kite_agent())

    def test_kite_router_endpoints_direct(self):
        """Verify /kite/* async handler functions directly."""
        async def run_router_tests():
            # 1. Status without session
            status_resp = await kite_auth_status(self.mock_request)
            self.assertIn(status_resp["status"], ("no_token", "ok"))

            # 2. Auth login
            auth_payload = AuthRequest(api_key="my_api_key", access_token="my_access_token")
            auth_resp = await kite_auth(auth_payload, self.mock_request)
            self.assertEqual(auth_resp["status"], "ok")

            # 3. Session hydration
            session_resp = await kite_auth_session()
            self.assertEqual(session_resp["api_key"], "my_api_key")

            # 4. Status with session
            status_resp2 = await kite_auth_status(self.mock_request)
            self.assertEqual(status_resp2["status"], "ok")

            # 5. Search instruments
            inst_resp = await kite_instruments(search="RELIANCE")
            self.assertEqual(inst_resp["status"], "ok")
            self.assertGreaterEqual(len(inst_resp["instruments"]), 1)

            # 6. Historical candles endpoint (falls back gracefully to SQLite cache)
            hist_resp = await kite_historical(self.mock_request, symbol="RELIANCE", interval="5")
            self.assertEqual(hist_resp["status"], "ok")

            # 7. WebSocket controls
            ws_start_resp = await kite_ws_start(self.mock_request, WsStartRequest(tokens=[738561]))
            self.assertEqual(ws_start_resp["status"], "ok")
            ws_snap_resp = await kite_ws_snapshot(self.mock_request)
            self.assertEqual(ws_snap_resp["status"], "ok")
            ws_stop_resp = await kite_ws_stop(self.mock_request)
            self.assertEqual(ws_stop_resp["status"], "ok")

            # 8. Logout
            logout_resp = await kite_auth_logout(self.mock_request)
            self.assertEqual(logout_resp["status"], "ok")

        asyncio.run(run_router_tests())


if __name__ == "__main__":
    unittest.main()
