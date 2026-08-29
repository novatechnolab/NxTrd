"""
TradeSignal NextGen — Week 5 Test Suite
Tests MarketAgent, EmaAgent, MaxPainAgent, SynergyAgent, OiTransitionAgent,
and routers/market.py, analytics.py, options.py.
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
from agents.market_agent import MarketAgent
from agents.ema_agent import EmaAgent
from agents.max_pain_agent import MaxPainAgent
from agents.synergy_agent import SynergyAgent
from agents.oi_transition_agent import OiTransitionAgent
from repositories import instruments as repo_instruments

from routers.market import market_pulse, market_bias, indices_overview, sector_performance
from routers.analytics import ema_crossover, max_pain, max_pain_deviation_matrix, synergy_matrix, conviction_score
from routers.options import option_chain, oi_transition, pcr_summary
from server import app


class TestWeek5AnalyticsMarketOptions(unittest.TestCase):

    def setUp(self):
        self.orig_db_path = core.db.DB_PATH
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix="_test_w5.db")
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

        self.bus = EventBus()
        self.mock_request = MagicMock()
        self.mock_request.app = app

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
        core.db.DB_PATH = self.orig_db_path

    def test_market_agent_and_routes(self):
        """Verify MarketAgent and routers/market.py."""
        async def run_tests():
            agent = MarketAgent(self.bus)
            bias = await agent.get_market_bias()
            self.assertEqual(bias["status"], "ok")
            self.assertIn("zone", bias)

            pulse = await agent.get_market_pulse()
            self.assertEqual(pulse["status"], "ok")
            self.assertGreater(pulse["advances"], 0)

            # Test router handlers
            r_pulse = await market_pulse(self.mock_request)
            self.assertEqual(r_pulse["status"], "ok")
            r_bias = await market_bias(self.mock_request)
            self.assertEqual(r_bias["status"], "ok")
            r_ind = await indices_overview(self.mock_request)
            self.assertEqual(r_ind["status"], "ok")
            r_sec = await sector_performance(self.mock_request)
            self.assertEqual(r_sec["status"], "ok")

        asyncio.run(run_tests())

    def test_analytics_agents_and_routes(self):
        """Verify EmaAgent, MaxPainAgent, SynergyAgent and routers/analytics.py."""
        async def run_tests():
            # 1. EMA Agent
            ema_agent = EmaAgent(self.bus)
            ema_res = await ema_agent.get_ema_crossovers(timeframe="5", symbols=["RELIANCE"])
            self.assertEqual(ema_res["status"], "ok")
            self.assertEqual(len(ema_res["crossovers"]), 1)

            # 2. Max Pain Agent
            mp_agent = MaxPainAgent(self.bus)
            mp_res = await mp_agent.get_max_pain("NIFTY")
            self.assertEqual(mp_res["status"], "ok")
            self.assertEqual(mp_res["symbol"], "NIFTY")

            mp_matrix = await mp_agent.get_max_pain_matrix()
            self.assertEqual(mp_matrix["status"], "ok")

            # 3. Synergy Agent
            syn_agent = SynergyAgent(self.bus)
            syn_res = await syn_agent.get_synergy_matrix()
            self.assertEqual(syn_res["status"], "ok")
            conv_res = await syn_agent.get_conviction_scores()
            self.assertEqual(conv_res["status"], "ok")

            # 4. Analytics router handlers
            r_ema = await ema_crossover(self.mock_request, timeframe="5", symbols="RELIANCE")
            self.assertEqual(r_ema["status"], "ok")
            r_mp = await max_pain(self.mock_request, symbol="NIFTY")
            self.assertEqual(r_mp["status"], "ok")
            r_mp_mat = await max_pain_deviation_matrix(self.mock_request)
            self.assertEqual(r_mp_mat["status"], "ok")
            r_syn = await synergy_matrix(self.mock_request)
            self.assertEqual(r_syn["status"], "ok")
            r_conv = await conviction_score(self.mock_request)
            self.assertEqual(r_conv["status"], "ok")

        asyncio.run(run_tests())

    def test_options_agent_and_routes(self):
        """Verify OiTransitionAgent and routers/options.py."""
        async def run_tests():
            oi_agent = OiTransitionAgent(self.bus)
            chain = await oi_agent.get_option_chain("NIFTY")
            self.assertEqual(chain["status"], "ok")
            self.assertGreater(len(chain["strikes"]), 0)

            trans = await oi_agent.get_oi_transitions("NIFTY")
            self.assertEqual(trans["status"], "ok")

            # Router handlers
            r_chain = await option_chain(self.mock_request, symbol="NIFTY")
            self.assertEqual(r_chain["status"], "ok")
            r_trans = await oi_transition(self.mock_request, symbol="NIFTY")
            self.assertEqual(r_trans["status"], "ok")
            r_pcr = await pcr_summary(self.mock_request, symbol="NIFTY")
            self.assertEqual(r_pcr["status"], "ok")

        asyncio.run(run_tests())


if __name__ == "__main__":
    unittest.main()
