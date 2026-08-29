"""
TradeSignal NextGen — Event Bus
asyncio.Queue — works identically on laptop and Termux (no Redis needed).
Reference: Replaces message_bus.py in reference workspace.
"""
import asyncio
from typing import Any

class EventBus:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    async def put(self, event_type: str, data: Any):
        for q in self._subscribers.get(event_type, []):
            await q.put(data)

    def subscribe(self, event_type: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.setdefault(event_type, []).append(q)
        return q
