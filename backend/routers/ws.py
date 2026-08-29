"""
TradeSignal NextGen — WebSocket Router
Provides real-time event streaming and delta broadcast to reduce bandwidth to 2-5KB per patch.
Ported from reference: server.py WebSocket handlers & fno_backend streaming
"""
import asyncio
import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.event_bus import EventBus
from core.utils import now_ist

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages active WebSocket client connections, heartbeat ping/pong, and topic subscriptions.
    """
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._topic_subscriptions: Dict[str, Set[WebSocket]] = {}

    @property
    def total_clients(self) -> int:
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket, topics: Optional[List[str]] = None):
        await websocket.accept()
        self._active_connections.add(websocket)
        target_topics = topics or ["all"]
        for topic in target_topics:
            self._topic_subscriptions.setdefault(topic, set()).add(websocket)
        logger.info(f"[WS] Client connected. Total active: {len(self._active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self._active_connections.discard(websocket)
        for subs in self._topic_subscriptions.values():
            subs.discard(websocket)
        logger.info(f"[WS] Client disconnected. Total active: {len(self._active_connections)}")

    async def broadcast_json(self, message: Dict[str, Any], topic: str = "all"):
        """Broadcast JSON payload to clients subscribed to topic."""
        subscribers = self._topic_subscriptions.get(topic, set()) | self._topic_subscriptions.get("all", set())
        if not subscribers:
            return

        dead_connections = []
        for ws in subscribers:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(ws)


manager = ConnectionManager()


def compute_delta(prev_rows: Dict[str, Any], curr_rows: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compute delta between previous state and current state.
    Returns list of only modified or newly added symbol rows (2-5KB payload).
    """
    changes = []
    for sym, curr_data in curr_rows.items():
        prev_data = prev_rows.get(sym)
        if prev_data != curr_data:
            changes.append({"symbol": sym, **curr_data})
    return changes


@router.websocket("/ws")
@router.websocket("/ws/live")
async def unified_live_ws(websocket: WebSocket):
    """Unified WebSocket streaming signals, ticks, alerts, and market pulse."""
    await manager.connect(websocket, topics=["all", "signals", "alerts", "ticks"])
    try:
        await websocket.send_json({
            "type": "connection_ack",
            "message": "Connected to Nxtrd Live Stream",
            "timestamp": now_ist().isoformat()
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("sub:"):
                topic = data.split(":", 1)[1].strip()
                manager._topic_subscriptions.setdefault(topic, set()).add(websocket)
                await websocket.send_json({"type": "subscribed", "topic": topic})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"[WS] Exception in live stream: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/board")
async def board_delta_ws(websocket: WebSocket):
    """Stream incremental 20-30s delta patches for Gainers Board & Futures Buildup."""
    await manager.connect(websocket, topics=["board"])
    last_state = {}
    try:
        await websocket.send_json({
            "type": "board_ack",
            "timestamp": now_ist().isoformat()
        })
        while True:
            # Heartbeat check
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    """Stream live option premium spike and retail trap alerts."""
    await manager.connect(websocket, topics=["alerts"])
    try:
        await websocket.send_json({
            "type": "alerts_ack",
            "timestamp": now_ist().isoformat()
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
