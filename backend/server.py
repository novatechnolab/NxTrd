"""
Nxtrd — Entry Point
==========================================
Zero business logic. Mounts domain routers. Starts AgentOrchestrator.
"""
import os
from contextlib import asynccontextmanager

# ── Load .env configuration ───────────────────────────────────────────
def _load_env():
    for env_path in [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.abspath(".env")
    ]:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip()
                            if k and not os.environ.get(k):
                                os.environ[k] = v
                break
            except Exception:
                pass

_load_env()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.db import init_db
from agents.orchestrator import AgentOrchestrator
from agents.event_bus import EventBus
from agents.kite_data_agent import KiteDataAgent
from agents.board_agent import BoardAgent
from agents.premium_spike_agent import PremiumSpikeAgent
from agents.market_agent import MarketAgent
from agents.ema_agent import EmaAgent
from agents.max_pain_agent import MaxPainAgent
from agents.synergy_agent import SynergyAgent
from agents.oi_transition_agent import OiTransitionAgent
from agents.fno_trap_agent import FNOTrapAgent
from agents.prediction_agent import PredictionAgent
from agents.alert_dispatch_agent import AlertDispatchAgent

from routers import (
    core, kite, board, alerts, oi, market,
    options, analytics, instruments, portfolio,
    screener, futures, ws
)

# ── Agent Lifecycle & Orchestration ───────────────────────────────────
_bus = EventBus()
_orchestrator = AgentOrchestrator(_bus)

_kite_data_agent = KiteDataAgent(_bus)
_board_agent = BoardAgent(_bus)
_premium_spike_agent = PremiumSpikeAgent(_bus)
_market_agent = MarketAgent(_bus)
_ema_agent = EmaAgent(_bus)
_max_pain_agent = MaxPainAgent(_bus)
_synergy_agent = SynergyAgent(_bus)
_oi_transition_agent = OiTransitionAgent(_bus)
_fno_trap_agent = FNOTrapAgent(_bus)
_prediction_agent = PredictionAgent(_bus)
_alert_dispatch_agent = AlertDispatchAgent(
    _bus,
    telegram_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
    telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
    discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
)

_orchestrator.register(_kite_data_agent)
_orchestrator.register(_board_agent)
_orchestrator.register(_premium_spike_agent)
_orchestrator.register(_market_agent)
_orchestrator.register(_ema_agent)
_orchestrator.register(_max_pain_agent)
_orchestrator.register(_synergy_agent)
_orchestrator.register(_oi_transition_agent)
_orchestrator.register(_fno_trap_agent)
_orchestrator.register(_prediction_agent)
_orchestrator.register(_alert_dispatch_agent)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await _orchestrator.start()
    yield
    await _orchestrator.stop()

app = FastAPI(title="Nxtrd API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.state.bus = _bus
app.state.orchestrator = _orchestrator
app.state.kite_data_agent = _kite_data_agent
app.state.board_agent = _board_agent
app.state.premium_spike_agent = _premium_spike_agent
app.state.market_agent = _market_agent
app.state.ema_agent = _ema_agent
app.state.max_pain_agent = _max_pain_agent
app.state.synergy_agent = _synergy_agent
app.state.oi_transition_agent = _oi_transition_agent
app.state.fno_trap_agent = _fno_trap_agent
app.state.prediction_agent = _prediction_agent
app.state.alert_dispatch_agent = _alert_dispatch_agent

# ── Mount Routers ─────────────────────────────────────────────────────
for router, prefix in [
    (core.router,        "/api"),
    (kite.router,        "/kite"),
    (board.router,       "/api"),
    (alerts.router,      "/api"),
    (oi.router,          "/api"),
    (market.router,      "/api"),
    (options.router,     "/api"),
    (analytics.router,   "/api"),
    (instruments.router, "/api"),
    (portfolio.router,   "/api"),
    (screener.router,    "/api"),
    (futures.router,     "/api"),
    (ws.router,          ""),
]:
    app.include_router(router, prefix=prefix)

# ── Serve SvelteKit Frontend ──────────────────────────────────────────
DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/", StaticFiles(directory=DIST, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
