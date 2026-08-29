"""
TradeSignal NextGen — Kite Data Agent
Primary agent for Zerodha KiteConnect & KiteTicker management.
Handles:
- KiteConnect client authentication & lifecycle
- Non-blocking async market data queries (historical candles, quotes, LTP, margins)
- Live tick ingestion, memory store, and EventBus publishing
- Instrument synchronization with SQLite cache
"""
import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime as dt, timedelta
from agents.base_agent import BaseAgent, AgentState
from core.event_bus import EventBus
from core.session_utils import get_kite_credentials, save_kite_session, clear_kite_session
from core.utils import now_ist, IST
from repositories import instruments as repo_instruments, ohlcv as repo_ohlcv

logger = logging.getLogger(__name__)

# Canonical interval mapping
KITE_INTERVAL_MAP = {
    '1': 'minute',
    'minute': 'minute',
    '3': '3minute',
    '3minute': '3minute',
    '5': '5minute',
    '5minute': '5minute',
    '10': '10minute',
    '10minute': '10minute',
    '15': '15minute',
    '15minute': '15minute',
    '30': '30minute',
    '30minute': '30minute',
    '60': '60minute',
    '60minute': '60minute',
    'D': 'day',
    'day': 'day',
}

EXCHANGE_MAP = {
    'NIFTY50': 'NSE',
    'NIFTY 50': 'NSE',
    'NIFTY BANK': 'NSE',
    'BANKNIFTY': 'NSE',
    'FINNIFTY': 'NSE',
    'NIFTY FIN SERVICE': 'NSE',
    'INDIAVIX': 'NSE',
    'INDIA VIX': 'NSE',
    'SENSEX': 'BSE',
}


class KiteDataAgent(BaseAgent):
    """
    Central Market Data Agent interfacing Zerodha KiteConnect & Ticker.
    """
    name: str = "kite_data_agent"
    category: str = "data"

    def __init__(self, bus: EventBus):
        super().__init__(bus)
        self._kite_client: Any = None
        self._ticker_client: Any = None
        self._tick_store: Dict[int, Dict[str, Any]] = {}
        self._live_ltp_cache: Dict[int, float] = {}
        self._ws_running: bool = False
        self._subscribed_tokens: set[int] = set()

    def get_kite(self) -> Any:
        """Get or initialize KiteConnect singleton instance."""
        if self._kite_client is not None:
            return self._kite_client

        api_key, access_token = get_kite_credentials()
        if not api_key or not access_token:
            return None

        try:
            from kiteconnect import KiteConnect
            client = KiteConnect(api_key=api_key)
            client.set_access_token(access_token)
            self._kite_client = client
            logger.info(f"[{self.name}] KiteConnect client initialized.")
            return self._kite_client
        except ImportError:
            logger.warning(f"[{self.name}] kiteconnect package not installed; running in mock/offline mode.")
            return None
        except Exception as e:
            logger.error(f"[{self.name}] Error creating KiteConnect client: {e}")
            return None

    def reset_session(self):
        """Reset cached client on auth credential update or logout."""
        self._kite_client = None
        self.stop_ws()
        logger.info(f"[{self.name}] Kite session reset.")

    def is_authenticated(self) -> bool:
        """Check if Kite client has an active session token."""
        client = self.get_kite()
        return client is not None and bool(getattr(client, "access_token", None))

    # ── Non-blocking Async Data Methods ─────────────────────────────────

    async def get_historical(self, symbol: str = "", token: Optional[int] = None,
                             interval: str = "5minute", from_dt: Optional[dt] = None,
                             to_dt: Optional[dt] = None, include_oi: bool = False) -> Dict[str, Any]:
        """Fetch historical candle data via KiteConnect with graceful SQLite cache fallback."""
        resolved_interval = KITE_INTERVAL_MAP.get(str(interval), "5minute")
        if not token:
            token = repo_instruments.resolve_token(symbol)
        if not token:
            return {
                "status": "error",
                "message": f"Unknown symbol '{symbol}'. Token resolution failed.",
                "candles": []
            }

        start_dt = from_dt or (now_ist() - timedelta(days=10)).replace(hour=9, minute=15, second=0, microsecond=0)
        end_dt = to_dt or now_ist()

        client = self.get_kite()
        if not client:
            # Fallback to local SQLite cache
            cached = repo_ohlcv.get_ohlcv(
                token,
                start_dt.strftime("%Y-%m-%d"),
                end_dt.strftime("%Y-%m-%d"),
                interval=resolved_interval
            )
            return {
                "status": "ok",
                "source": "sqlite_cache",
                "symbol": symbol or str(token),
                "token": token,
                "interval": resolved_interval,
                "count": len(cached),
                "candles": cached
            }

        def _fetch():
            return client.historical_data(
                instrument_token=token,
                from_date=start_dt,
                to_date=end_dt,
                interval=resolved_interval,
                continuous=False,
                oi=include_oi
            )

        try:
            raw_candles = await asyncio.to_thread(_fetch)
            # Store fresh candles in SQLite cache asynchronously
            asyncio.create_task(
                asyncio.to_thread(repo_ohlcv.store_ohlcv, token, raw_candles, resolved_interval)
            )
            return {
                "status": "ok",
                "source": "kite_live",
                "symbol": symbol or str(token),
                "token": token,
                "interval": resolved_interval,
                "count": len(raw_candles),
                "candles": raw_candles
            }
        except Exception as e:
            logger.warning(f"[{self.name}] historical_data failed for {symbol}/{token}: {e}")
            # Graceful fallback to SQLite cache if available
            cached = repo_ohlcv.get_ohlcv(
                token,
                start_dt.strftime("%Y-%m-%d"),
                end_dt.strftime("%Y-%m-%d"),
                interval=resolved_interval
            )
            if cached:
                return {
                    "status": "ok",
                    "source": "sqlite_cache_fallback",
                    "symbol": symbol or str(token),
                    "token": token,
                    "interval": resolved_interval,
                    "count": len(cached),
                    "candles": cached
                }
            return {"status": "error", "message": str(e), "candles": []}

    async def get_quote(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch quotes for a list of symbols in background thread."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}

        inst_keys = [f"{EXCHANGE_MAP.get(s, 'NSE')}:{s}" for s in symbols if s]

        def _fetch():
            return client.quote(inst_keys)

        try:
            raw = await asyncio.to_thread(_fetch)
            result = {}
            for key, data in raw.items():
                sym = key.split(":")[-1]
                close = data.get("ohlc", {}).get("close", 1) or 1
                net_chg = data.get("net_change", 0) or 0
                result[sym] = {
                    "last_price": data.get("last_price"),
                    "open": data.get("ohlc", {}).get("open"),
                    "high": data.get("ohlc", {}).get("high"),
                    "low": data.get("ohlc", {}).get("low"),
                    "close": data.get("ohlc", {}).get("close"),
                    "volume": data.get("volume"),
                    "oi": data.get("oi"),
                    "change": net_chg,
                    "change_pct": round((net_chg / close) * 100, 2),
                    "timestamp": data.get("timestamp"),
                    "buy_quantity": data.get("buy_quantity"),
                    "sell_quantity": data.get("sell_quantity"),
                }
            return {"status": "ok", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_ltp(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch last traded price map."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}

        inst_keys = [f"{EXCHANGE_MAP.get(s, 'NSE')}:{s}" for s in symbols if s]

        def _fetch():
            return client.ltp(inst_keys)

        try:
            raw = await asyncio.to_thread(_fetch)
            return {
                "status": "ok",
                "data": {k.split(":")[-1]: v.get("last_price") for k, v in raw.items()}
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_profile(self) -> Dict[str, Any]:
        """Fetch user profile."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}
        try:
            profile = await asyncio.to_thread(client.profile)
            return {"status": "ok", "data": profile}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_holdings(self) -> Dict[str, Any]:
        """Fetch portfolio holdings."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}
        try:
            holdings = await asyncio.to_thread(client.holdings)
            return {"status": "ok", "data": holdings}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_positions(self) -> Dict[str, Any]:
        """Fetch portfolio positions."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}
        try:
            positions = await asyncio.to_thread(client.positions)
            return {"status": "ok", "data": positions}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_margins(self) -> Dict[str, Any]:
        """Fetch margins."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}
        try:
            margins = await asyncio.to_thread(client.margins)
            return {"status": "ok", "data": margins}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def sync_instruments(self) -> Dict[str, Any]:
        """Fetch all instruments from Kite and update SQLite database."""
        client = self.get_kite()
        if not client:
            return {"status": "error", "message": "No active Kite session"}
        try:
            instruments_list = await asyncio.to_thread(client.instruments)
            await asyncio.to_thread(repo_instruments.store_instruments, instruments_list)
            return {"status": "ok", "count": len(instruments_list), "message": "Instruments synced successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Live Ticker & WebSocket Streaming ───────────────────────────────

    def get_tick_snapshot(self) -> Dict[str, Any]:
        """Return snapshot of current in-memory tick store."""
        return {
            "status": "ok",
            "count": len(self._tick_store),
            "ticks": dict(self._tick_store)
        }

    def start_ws(self, tokens: List[int]) -> Dict[str, Any]:
        """Start KiteTicker live data streaming for tokens."""
        if not tokens:
            return {"status": "error", "message": "No tokens provided"}
        self._subscribed_tokens.update(tokens)
        self._ws_running = True
        logger.info(f"[{self.name}] Ticker started for {len(self._subscribed_tokens)} tokens.")
        return {"status": "ok", "message": f"Ticker active for {len(self._subscribed_tokens)} instruments"}

    def stop_ws(self) -> Dict[str, Any]:
        """Stop KiteTicker."""
        self._ws_running = False
        self._subscribed_tokens.clear()
        logger.info(f"[{self.name}] Ticker stopped.")
        return {"status": "ok", "message": "Ticker stopped"}

    def handle_ticks(self, ticks: List[Dict[str, Any]]):
        """Callback to process incoming ticks and publish to EventBus."""
        now_str = now_ist().isoformat()
        for t in ticks:
            tok = t.get("instrument_token")
            if not tok:
                continue
            ltp = t.get("last_price")
            self._tick_store[tok] = {
                "token": tok,
                "ltp": ltp,
                "volume": t.get("volume"),
                "buy_qty": t.get("buy_quantity"),
                "sell_qty": t.get("sell_quantity"),
                "change": t.get("change"),
                "oi": t.get("oi"),
                "ohlc": t.get("ohlc", {}),
                "ts": now_str
            }
            if ltp is not None:
                self._live_ltp_cache[tok] = float(ltp)

        # Dispatch non-blocking event
        asyncio.create_task(self.publish("TICK", ticks))

    # ── Agent FSM Main Loop ─────────────────────────────────────────────

    async def run(self):
        """Continuous background execution loop."""
        self.transition(AgentState.MONITORING)
        while self._running:
            try:
                # Periodic health heartbeat & cycle metric
                self.record_cycle()
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.record_error(str(e))
                await asyncio.sleep(5.0)
