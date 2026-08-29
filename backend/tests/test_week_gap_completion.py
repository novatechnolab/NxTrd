"""
Test Suite — Week 0-8 Gap Completion
=====================================
Covers the 3 gaps identified in the Week 0-8 audit:
  1. AlertDispatchAgent — full asyncio port
  2. TractionBoardAgent — redirect stub
  3. routers/oi.py     — 10 OI routes
  4. OiTransitionAgent — 7 new methods
  5. server.py         — AlertDispatchAgent registered
"""
import asyncio
import sys
import os
import unittest

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAlertDispatchAgentGap(unittest.TestCase):
    """Gap 1 — AlertDispatchAgent full asyncio implementation."""

    def setUp(self):
        from agents.alert_dispatch_agent import AlertDispatchAgent
        from core.event_bus import EventBus
        self.bus = EventBus()
        self.agent = AlertDispatchAgent(
            self.bus,
            telegram_token=None,
            telegram_chat_id=None,
            cooldown_seconds=10.0,
            enforce_market_hours=False,   # disable for testing
        )

    def test_agent_attributes(self):
        """AlertDispatchAgent has all required attributes."""
        a = self.agent
        self.assertEqual(a.name, "alert_dispatch_agent")
        self.assertIsInstance(a.symbol_last_alert, dict)
        self.assertEqual(a.alerts_dispatched_count, 0)
        self.assertEqual(a.alerts_suppressed_count, 0)
        self.assertEqual(a.cooldown_seconds, 10.0)
        self.assertFalse(a.enforce_market_hours)

    def test_format_telegram_message(self):
        """_format_telegram_message returns non-empty Markdown string."""
        msg = self.agent._format_telegram_message(
            "alerts/prediction",
            {
                "symbol": "NIFTY",
                "direction": "BULLISH",
                "ltp": 24500.0,
                "conviction_score": 87,
                "target_1": 24600,
                "stop_loss": 24400,
                "rationale": "FNO trap signal",
                "agreeing_agents": ["EmaAgent", "SynergyAgent"],
            }
        )
        self.assertIn("NIFTY", msg)
        self.assertIn("BULLISH", msg)
        self.assertIn("87%", msg)
        self.assertIn("T1:", msg)
        self.assertIn("SL:", msg)

    def test_cooldown_suppression(self):
        """Duplicate alerts within cooldown are suppressed."""
        import time

        class FakeMsg:
            topic = "alerts/signal"
            payload = {"symbol": "RELIANCE", "ltp": 3000.0, "conviction_score": 70}

        loop = asyncio.new_event_loop()

        # First dispatch
        loop.run_until_complete(self.agent._handle_message(FakeMsg()))
        self.assertEqual(self.agent.alerts_dispatched_count, 1)

        # Immediate second dispatch → suppressed
        loop.run_until_complete(self.agent._handle_message(FakeMsg()))
        self.assertEqual(self.agent.alerts_dispatched_count, 1)
        self.assertEqual(self.agent.alerts_suppressed_count, 1)
        loop.close()

    def test_high_conviction_prediction_bypass(self):
        """≥85% prediction conviction bypasses cooldown."""
        class FakeMsg:
            topic = "alerts/prediction"
            payload = {"symbol": "INFY", "conviction_score": 90, "ltp": 1800.0}

        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.agent._handle_message(FakeMsg()))
        loop.run_until_complete(self.agent._handle_message(FakeMsg()))  # should bypass
        self.assertEqual(self.agent.alerts_dispatched_count, 2)
        loop.close()

    def test_get_status(self):
        """get_status returns enriched dict with alert counters."""
        s = self.agent.get_status()
        self.assertIn("alerts_dispatched", s)
        self.assertIn("alerts_suppressed", s)
        self.assertIn("cooldown_seconds", s)
        self.assertFalse(s["telegram_configured"])


class TestTractionBoardAgentGap(unittest.TestCase):
    """Gap 2 — TractionBoardAgent is a valid no-op stub."""

    def test_stub_is_importable(self):
        from agents.traction_board_agent import TractionBoardAgent
        from core.event_bus import EventBus
        bus = EventBus()
        agent = TractionBoardAgent(bus)
        self.assertEqual(agent.name, "traction_board_agent")

    def test_traction_in_board_agent(self):
        """Confirm traction logic lives in BoardAgent (not stub)."""
        from agents.board_agent import BoardAgent
        from core.event_bus import EventBus
        bus = EventBus()
        agent = BoardAgent(bus)
        self.assertTrue(hasattr(agent, "compute_traction_quadrant"))
        self.assertTrue(hasattr(agent, "get_traction_board"))


class TestOiRouterGap(unittest.TestCase):
    """Gap 3 — routers/oi.py has 10 routes registered."""

    def test_router_exists_and_has_routes(self):
        from routers.oi import router
        paths = [r.path for r in router.routes]
        # Check all 10 expected route paths are present
        expected = [
            "/oi/health",
            "/oi/tickers",
            "/oi/options-chain",
            "/oi/oi-analysis",
            "/oi/scan",
            "/oi/positions",
            "/oi/scanner",
            "/oi/scanner/reset",
            "/oi/spurt",
            "/oi/symbol/{symbol}",
        ]
        for path in expected:
            self.assertIn(path, paths, f"Missing OI route: {path}")

    def test_oi_transition_agent_new_methods(self):
        """OiTransitionAgent has all 7 methods required by the OI router."""
        from agents.oi_transition_agent import OiTransitionAgent
        from core.event_bus import EventBus
        agent = OiTransitionAgent(EventBus())
        required = [
            "get_tracked_symbols", "get_positions", "run_scan",
            "reset_baseline", "get_scanner_results", "get_oi_spurt",
            "get_symbol_detail",
        ]
        for method in required:
            self.assertTrue(
                hasattr(agent, method),
                f"OiTransitionAgent missing method: {method}"
            )

    def test_oi_new_methods_return_correct_structure(self):
        """New OiTransitionAgent methods return dicts with status=ok."""
        from agents.oi_transition_agent import OiTransitionAgent
        from core.event_bus import EventBus
        agent = OiTransitionAgent(EventBus())
        loop = asyncio.new_event_loop()

        results = {
            "tickers": loop.run_until_complete(agent.get_tracked_symbols()),
            "positions": loop.run_until_complete(agent.get_positions()),
            "scan": loop.run_until_complete(agent.run_scan({"symbols": ["NIFTY"]})),
            "reset": loop.run_until_complete(agent.reset_baseline()),
            "scanner": loop.run_until_complete(agent.get_scanner_results()),
            "spurt": loop.run_until_complete(agent.get_oi_spurt(5.0)),
            "detail": loop.run_until_complete(agent.get_symbol_detail("NIFTY")),
        }
        loop.close()

        for key, result in results.items():
            self.assertEqual(result.get("status"), "ok", f"{key} missing status=ok")


class TestServerWiringGap(unittest.TestCase):
    """Verify server.py correctly imports and wires AlertDispatchAgent."""

    def test_alert_dispatch_imported_in_server(self):
        """server.py imports AlertDispatchAgent."""
        import importlib, pathlib
        server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
        with open(server_path) as f:
            src = f.read()
        self.assertIn("AlertDispatchAgent", src)
        self.assertIn("_orchestrator.register(_alert_dispatch_agent)", src)
        self.assertIn("app.state.alert_dispatch_agent", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
