"""
TradeSignal NextGen — Base Agent (FSM)
All agents in NextGen inherit from this base class.
Provides:
- Formal Finite State Machine (IDLE, MONITORING, TRIGGERED, COOLDOWN, ERROR, STOPPED)
- Transition logging & timestamp tracking
- Non-blocking EventBus integration (publish / subscribe)
- Health metrics and diagnostics
"""
import asyncio
import logging
from typing import Optional, Any, Dict
from enum import Enum
from core.event_bus import EventBus
from core.utils import now_ist

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    IDLE = "IDLE"
    MONITORING = "MONITORING"
    TRIGGERED = "TRIGGERED"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class BaseAgent:
    """
    Finite State Machine base for all TradeSignal agents.
    States: IDLE → MONITORING → TRIGGERED → COOLDOWN → IDLE
    """
    name: str = "BaseAgent"
    category: str = "general"

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.state: AgentState = AgentState.IDLE
        self._state_entered_at: float = self._current_time()
        self._cycles_completed: int = 0
        self._error_count: int = 0
        self._last_error: Optional[str] = None
        self._last_active_at: str = now_ist().isoformat()
        self._running: bool = False
        self._subscriptions: list[asyncio.Queue] = []

    def _current_time(self) -> float:
        try:
            return asyncio.get_event_loop().time()
        except RuntimeError:
            return 0.0

    def transition(self, new_state: AgentState | str):
        if isinstance(new_state, str):
            try:
                new_state = AgentState(new_state)
            except ValueError:
                new_state = AgentState.IDLE
        if self.state != new_state:
            logger.info(f"[{self.name}] Transition: {self.state.value} → {new_state.value}")
            self.state = new_state
            self._state_entered_at = self._current_time()
            self._last_active_at = now_ist().isoformat()

    def time_in_state(self) -> float:
        """Seconds spent in current state."""
        return max(0.0, self._current_time() - self._state_entered_at)

    async def publish(self, event_type: str, data: Any):
        """Publish an event to the EventBus."""
        await self.bus.put(event_type, data)

    def subscribe(self, event_type: str) -> asyncio.Queue:
        """Subscribe to an EventBus event type."""
        q = self.bus.subscribe(event_type)
        self._subscriptions.append(q)
        return q

    def record_cycle(self):
        """Record successful execution cycle."""
        self._cycles_completed += 1
        self._last_active_at = now_ist().isoformat()

    def record_error(self, error_msg: str):
        """Record error occurrence."""
        self._error_count += 1
        self._last_error = error_msg
        self.transition(AgentState.ERROR)

    def get_status(self) -> Dict[str, Any]:
        """Return structured agent telemetry for diagnostics."""
        return {
            "name": self.name,
            "category": self.category,
            "state": self.state.value,
            "time_in_state_seconds": round(self.time_in_state(), 2),
            "cycles_completed": self._cycles_completed,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "last_active_at": self._last_active_at,
            "is_running": self._running
        }

    async def start(self):
        """Starts the agent runner."""
        self._running = True
        self.transition(AgentState.IDLE)
        await self.run()

    async def stop(self):
        """Signals the agent to stop."""
        self._running = False
        self.transition(AgentState.STOPPED)

    async def run(self):
        """Override in subclass. Main event/polling loop."""
        raise NotImplementedError(f"{self.name}.run() must be implemented in subclass")
