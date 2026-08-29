"""
TradeSignal NextGen — Week 7 Test Suite
Tests Async Scanner Loops, Market Hours utilities, Orchestrator Pause/Resume, and EventBus broadcasts.
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
from core.utils import now_ist, is_weekend, is_premarket, is_market_hours
from core.event_bus import EventBus
from agents.orchestrator import AgentOrchestrator
from agents.board_agent import BoardAgent
from agents.ema_agent import EmaAgent
from agents.synergy_agent import SynergyAgent
from agents.oi_transition_agent import OiTransitionAgent
from agents.fno_trap_agent import FNOTrapAgent
from repositories import instruments as repo_instruments


class TestWeek7AsyncScanners(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = core.db.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test_w7.db")
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
        self.orchestrator = AgentOrchestrator(self.bus)

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
        core.db.DB_PATH = self.orig_db_path

    def test_market_hours_utilities(self):
        """Verify market hours and timezone calculations."""
        now = now_ist()
        self.assertIsNotNone(now)
        self.assertEqual(now.tzinfo.zone, "Asia/Kolkata")

        # Weekend / weekday checks return boolean
        self.assertIsInstance(is_weekend(), bool)
        self.assertIsInstance(is_premarket(), bool)
        self.assertIsInstance(is_market_hours(), bool)

    def test_orchestrator_pause_resume(self):
        """Verify pause/resume controls in AgentOrchestrator."""
        ema_agent = EmaAgent(self.bus)
        self.orchestrator.register(ema_agent)

        self.assertFalse(self.orchestrator.is_agent_paused("ema_agent"))
        self.assertTrue(self.orchestrator.pause_agent("ema_agent"))
        self.assertTrue(self.orchestrator.is_agent_paused("ema_agent"))

        health = self.orchestrator.get_health_status()
        self.assertTrue(health["agents"]["ema_agent"]["paused"])

        self.assertTrue(self.orchestrator.resume_agent("ema_agent"))
        self.assertFalse(self.orchestrator.is_agent_paused("ema_agent"))

    def test_async_scanner_execution_and_events(self):
        """Verify async scanner cycles and event publishing."""
        async def run_scanner_tests():
            ema_q = self.bus.subscribe("signals/ema")
            syn_q = self.bus.subscribe("signals/synergy")
            trap_q = self.bus.subscribe("signals/fno_trap")

            # 1. EMA scanner cycle
            ema_agent = EmaAgent(self.bus)
            ema_data = await ema_agent.get_ema_crossovers("5", ["RELIANCE"])
            self.assertEqual(ema_data["status"], "ok")
            await ema_agent.publish("signals/ema", ema_data)

            # 2. Synergy scanner cycle
            syn_agent = SynergyAgent(self.bus)
            syn_data = await syn_agent.get_synergy_matrix()
            self.assertEqual(syn_data["status"], "ok")
            await syn_agent.publish("signals/synergy", syn_data)

            # 3. FNO Trap scanner cycle
            trap_agent = FNOTrapAgent(self.bus)
            trap_data = await trap_agent.get_trap_cards("RELIANCE")
            self.assertEqual(trap_data["status"], "ok")
            await trap_agent.publish("signals/fno_trap", trap_data)

            # Check queues received event payloads
            self.assertFalse(ema_q.empty())
            self.assertFalse(syn_q.empty())
            self.assertFalse(trap_q.empty())

            ev_ema = await ema_q.get()
            self.assertEqual(ev_ema["status"], "ok")
            ev_syn = await syn_q.get()
            self.assertEqual(ev_syn["status"], "ok")
            ev_trap = await trap_q.get()
            self.assertEqual(ev_trap["status"], "ok")

        asyncio.run(run_scanner_tests())


if __name__ == "__main__":
    unittest.main()
