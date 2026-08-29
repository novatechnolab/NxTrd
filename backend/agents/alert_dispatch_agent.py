"""
TradeSignal NextGen — Alert Dispatch Agent
==========================================
Centralised outward alert router: Telegram, Discord, and WebSocket broadcast.
Enforces cross-scanner deduplication, symbol cooldowns (15-min default),
and high-conviction priority escalation (≥ 85% bypasses cooldown).

Ported from reference (asyncio-adapted):
  /Agent backup/.../app/backend/agents/alert_dispatch_agent.py
"""
import asyncio
import json
import logging
import ssl
import time
import urllib.request
from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent, AgentState
from core.event_bus import EventBus
from core.utils import is_market_hours

logger = logging.getLogger(__name__)


class AlertDispatchAgent(BaseAgent):
    """
    Autonomous asyncio agent handling alert deduplication, cooldowns,
    Telegram routing, Discord routing, and WebSocket dashboard broadcasts.

    Architecture note:
      - Subscribes to EventBus topic  "alerts/#"  on start.
      - All inbound alert events are consumed in the async run() loop.
      - Telegram and Discord sends use stdlib urllib (no requests dep).
    """

    name: str = "alert_dispatch_agent"

    def __init__(
        self,
        bus: EventBus,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        discord_webhook_url: Optional[str] = None,
        cooldown_seconds: float = 900.0,        # 15-minute symbol cooldown
        enforce_market_hours: bool = True,
    ):
        super().__init__(bus)
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        # Normalise legacy discordapp.com → discord.com
        raw_discord = (discord_webhook_url or "").replace("discordapp.com", "discord.com")
        self.discord_webhook_url: Optional[str] = raw_discord or None
        self.cooldown_seconds = cooldown_seconds
        self.enforce_market_hours = enforce_market_hours

        # State tracking
        self.symbol_last_alert: Dict[str, float] = {}   # symbol → last dispatch ts
        self.dispatched_alerts: Dict[str, Any] = {}     # key → alert record
        self.alerts_dispatched_count: int = 0
        self.alerts_suppressed_count: int = 0

        # Optional WebSocket broadcast callable (set externally)
        self._ws_broadcast = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def attach_ws_broadcast(self, broadcast_fn):
        """
        Attach an async callable(topic: str, payload: dict) for WebSocket broadcasts.
        Called from server.py after startup when ws.py ConnectionManager is ready.
        """
        self._ws_broadcast = broadcast_fn
        logger.info(f"[{self.name}] WebSocket broadcast function attached.")

    async def run(self):
        """
        Async FSM main loop. Subscribes to alerts/# and dispatches
        each event as it arrives via the EventBus inbox queue.
        """
        self.transition(AgentState.MONITORING)

        # Subscribe to all alert topics
        alert_queue = None
        if self.bus:
            alert_queue = self.bus.subscribe("alerts")
            logger.info(f"[{self.name}] Subscribed to 'alerts'.")

        while self._running:
            try:
                # Drain inbox & alert queue
                try:
                    msg = self._inbox.get_nowait()
                    await self._handle_message(msg)
                    self.record_cycle()
                except asyncio.QueueEmpty:
                    pass

                if alert_queue:
                    try:
                        msg = alert_queue.get_nowait()
                        await self._handle_message(msg)
                        self.record_cycle()
                    except asyncio.QueueEmpty:
                        pass

                await asyncio.sleep(0.05)   # 50ms poll — 4× tighter than default 200ms
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.record_error(str(e))
                await asyncio.sleep(1.0)

    # ── Message Handling ───────────────────────────────────────────────────

    async def _handle_message(self, message: Any):
        """Process one inbound alert event from EventBus."""
        if not hasattr(message, "topic"):
            return

        topic: str = message.topic
        payload: Dict[str, Any] = getattr(message, "payload", {}) or {}
        symbol: Optional[str] = payload.get("symbol")

        if not symbol:
            return

        # Market hours guard — suppress outward alerts when market is closed
        if self.enforce_market_hours and not is_market_hours():
            self.alerts_suppressed_count += 1
            logger.debug(f"[{self.name}] Market closed — suppressed outward alert for {symbol}")
            return

        # Conviction & priority check
        is_prediction = topic.startswith("alerts/prediction")
        conviction = int(payload.get("conviction_score", payload.get("conviction", 60)))

        # Cooldown deduplication
        now = time.time()
        last_time = self.symbol_last_alert.get(symbol, 0.0)
        elapsed = now - last_time
        bypass_cooldown = is_prediction and conviction >= 85

        if elapsed < self.cooldown_seconds and not bypass_cooldown:
            self.alerts_suppressed_count += 1
            logger.debug(
                f"[{self.name}] Suppressed duplicate alert for {symbol} "
                f"(cooldown: {int(elapsed)}s / {int(self.cooldown_seconds)}s)"
            )
            return

        # Record dispatch
        self.symbol_last_alert[symbol] = now
        self.alerts_dispatched_count += 1

        formatted = self._format_telegram_message(topic, payload)
        self.dispatched_alerts[f"{symbol}_{int(now)}"] = {
            "topic": topic,
            "payload": payload,
            "formatted_message": formatted,
            "timestamp": now,
        }

        # Outward dispatch — all non-blocking
        if self.telegram_token and self.telegram_chat_id:
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_telegram, formatted
            )

        if self.discord_webhook_url:
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_discord, formatted
            )

        if self._ws_broadcast:
            try:
                await self._ws_broadcast("alerts", payload)
            except Exception as e:
                logger.error(f"[{self.name}] WebSocket broadcast failed: {e}")

        logger.info(
            f"[{self.name}] DISPATCHED alert for {symbol} "
            f"(conviction={conviction}%, topic={topic})"
        )

    # ── Formatting ─────────────────────────────────────────────────────────

    def _format_telegram_message(self, topic: str, payload: Dict[str, Any]) -> str:
        """Build rich Markdown text for Telegram notification."""
        symbol = payload.get("symbol", "N/A")
        direction = payload.get("direction", "NEUTRAL")
        icon = (
            "🚀 BULLISH" if direction == "BULLISH"
            else "🔻 BEARISH" if direction == "BEARISH"
            else "⚠️ ALERT"
        )
        conviction = payload.get("conviction_score", payload.get("conviction", 0))
        ltp = float(payload.get("ltp") or 0.0)
        rationale = payload.get("rationale", payload.get("setup_type", "Signal Triggered"))
        agreeing = payload.get("agreeing_agents", [])
        strike = payload.get("strike")
        expiry = payload.get("expiry")
        target_1 = payload.get("target_1")
        target_2 = payload.get("target_2")
        stop_loss = payload.get("stop_loss")
        market_context = payload.get("market_context")

        lines = [
            f"⚡ *TRADESIGNAL AGENTIC ALERT* | {icon}",
            f"*Symbol:* `{symbol}` | *LTP:* `₹{ltp:.2f}`",
            f"*Conviction Score:* `{conviction}%`",
        ]

        if strike:
            strike_line = f"*Strike:* `{strike}`"
            if expiry:
                strike_line += f" | *Expiry:* `{expiry}`"
            lines.append(strike_line)

        if target_1 or target_2 or stop_loss:
            parts = []
            if target_1:
                parts.append(f"T1: `{target_1}`")
            if target_2:
                parts.append(f"T2: `{target_2}`")
            if stop_loss:
                parts.append(f"SL: `{stop_loss}`")
            lines.append(f"*Levels:* {' | '.join(parts)}")

        if agreeing:
            lines.append(f"*Confluence Agents:* `{', '.join(agreeing)}`")
        if market_context:
            lines.append(f"*Market Regime:* `{market_context}`")

        lines.append(f"*Rationale:* {rationale}")
        lines.append(f"*Time:* `{time.strftime('%H:%M:%S IST')}`")

        return "\n".join(lines)

    # ── Transport ──────────────────────────────────────────────────────────

    def _send_telegram(self, text: str) -> None:
        """POST alert text to Telegram Bot API (blocking — run in executor)."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status not in range(200, 300):
                    logger.error(f"[{self.name}] Telegram returned HTTP {resp.status}")
        except Exception as e:
            logger.error(f"[{self.name}] Telegram send failed: {e}")

    def _send_discord(self, text: str) -> None:
        """POST alert text to Discord webhook (blocking — run in executor)."""
        try:
            ctx = ssl.create_default_context()
            payload = json.dumps({
                "content": text[:2000],
                "username": "TradeSignal Agentic Alerts",
            }).encode("utf-8")
            req = urllib.request.Request(
                self.discord_webhook_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "TradeSignalAlerts/2.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                if resp.status not in range(200, 300):
                    logger.error(f"[{self.name}] Discord returned HTTP {resp.status}")
        except Exception as e:
            logger.error(f"[{self.name}] Discord send failed: {e}")

    # ── Status ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        base = super().get_status()
        base.update({
            "alerts_dispatched": self.alerts_dispatched_count,
            "alerts_suppressed": self.alerts_suppressed_count,
            "tracked_symbols": len(self.symbol_last_alert),
            "cooldown_seconds": self.cooldown_seconds,
            "telegram_configured": bool(self.telegram_token),
            "discord_configured": bool(self.discord_webhook_url),
        })
        return base
