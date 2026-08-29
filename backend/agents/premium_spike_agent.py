"""
TradeSignal NextGen — Premium Spike Agent
Monitors option premium spikes and breakout alerts.
Ported from reference: server.py L5404-5470 & option_gainers_alerts.py
"""
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime as dt
from agents.base_agent import BaseAgent, AgentState
from core.event_bus import EventBus
from core.utils import now_ist
from repositories import alerts as repo_alerts

logger = logging.getLogger(__name__)


class PremiumSpikeAgent(BaseAgent):
    """
    Finite State Machine monitoring option premium surges and dispatching alerts.
    """
    name: str = "premium_spike_agent"
    category: str = "alerts"

    def __init__(self, bus: EventBus):
        super().__init__(bus)
        self._in_memory_alerts: List[Dict[str, Any]] = []
        self._alert_counter: int = 0
        self._threshold_spike_pct: float = 20.0

    async def get_recent_alerts(self, date_str: Optional[str] = None, after: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve recent premium spike alerts with optional date and ID filters."""
        if not self._in_memory_alerts:
            from repositories import board as repo_board
            eod_res = repo_board.get_eod_alerts(date_str)
            spikes = eod_res.get("prem_spikes", [])
            if spikes:
                return spikes

        if date_str:
            db_alerts = repo_alerts.get_recent_fno_alerts(limit=100)
            return [a for a in db_alerts if a.get("scanned_at", "").startswith(date_str)]

        if after is not None:
            return [a for a in self._in_memory_alerts if a.get("id", 0) > after]

        return list(self._in_memory_alerts)

    async def get_alert_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the premium spike scanner."""
        return {
            "status": "ok",
            "agent_state": self.state.value,
            "total_alerts": len(self._in_memory_alerts),
            "threshold_spike_pct": self._threshold_spike_pct,
            "last_active": self._last_active_at,
            "is_running": self._running
        }

    async def clear_alerts(self) -> bool:
        """Clear active in-memory alerts."""
        self._in_memory_alerts.clear()
        self.transition(AgentState.MONITORING)
        logger.info(f"[{self.name}] In-memory alerts cleared.")
        return True

    async def get_eod_summary(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Fetch End-of-Day alert summary."""
        from repositories import board as repo_board
        return repo_board.get_eod_alerts(date_str)



    def record_spike(self, symbol: str, strike: float, opt_type: str, spike_pct: float, ltp: float):
        """Record an alert occurrence and dispatch event."""
        self._alert_counter += 1
        now_str = now_ist().isoformat()
        alert = {
            "id": self._alert_counter,
            "symbol": symbol,
            "strike": strike,
            "opt_type": opt_type,
            "spike_pct": spike_pct,
            "ltp": ltp,
            "timestamp": now_str
        }
        self._in_memory_alerts.append(alert)
        if len(self._in_memory_alerts) > 500:
            self._in_memory_alerts.pop(0)

        # Transition to TRIGGERED state
        self.transition(AgentState.TRIGGERED)

        # Persist alert to repository
        repo_alerts.store_fno_alert(
            run_id=f"run_{self._alert_counter}",
            universe="NFO",
            mode="SPIKE",
            result=alert,
            summary={"spike_pct": spike_pct}
        )

        # Publish to event bus for WebSocket broadcast
        asyncio.create_task(self.publish("ALERT", alert))

    # ── Agent FSM Main Loop ─────────────────────────────────────────────

    async def run(self):
        """Main monitoring loop for PremiumSpikeAgent."""
        self.transition(AgentState.MONITORING)
        while self._running:
            try:
                # If recently triggered, transition to COOLDOWN before returning to MONITORING
                if self.state == AgentState.TRIGGERED and self.time_in_state() > 5.0:
                    self.transition(AgentState.COOLDOWN)
                elif self.state == AgentState.COOLDOWN and self.time_in_state() > 10.0:
                    self.transition(AgentState.MONITORING)

                self.record_cycle()
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.record_error(str(e))
                await asyncio.sleep(5.0)
