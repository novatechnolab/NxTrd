"""
TradeSignal NextGen — Router: screener
Rule: Reuses BoardAgent, FNOTrapAgent, and PredictionAgent.
No duplicate agent created.
Ported from reference: server.py L3200-3500
"""
from typing import Optional
from fastapi import APIRouter, Request

router = APIRouter()


def _get_agent(request: Request, name: str, fallback_cls):
    """Retrieve agent from app state or fallback."""
    app_obj = getattr(request, "app", None)
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent(name)
            if agent:
                return agent
        agent = getattr(app_obj.state, name, None)
        if agent:
            return agent

    from core.event_bus import EventBus
    return fallback_cls(EventBus())


@router.get("/screener/equity")
async def screener_equity(
    request: Request,
    cap: str = "large",
    period: int = 60
):
    """Screen equity stocks using Traction & momentum analytics (reuses BoardAgent)."""
    from agents.board_agent import BoardAgent
    agent = _get_agent(request, "board_agent", BoardAgent)
    return await agent.get_traction_board(cap=cap, period=period)


@router.get("/screener/fno")
async def screener_fno(request: Request):
    """Screen F&O stocks using futures buildup & volume surges (reuses BoardAgent)."""
    from agents.board_agent import BoardAgent
    agent = _get_agent(request, "board_agent", BoardAgent)
    return await agent.get_fut_buildup()


@router.get("/screener/trap")
async def screener_trap(
    request: Request,
    symbol: Optional[str] = None
):
    """Screen F&O trap conditions (delegates to FNOTrapAgent)."""
    from agents.fno_trap_agent import FNOTrapAgent
    agent = _get_agent(request, "fno_trap_agent", FNOTrapAgent)
    return await agent.get_trap_cards(symbol=symbol)


@router.get("/screener/confluence")
async def screener_confluence(
    request: Request,
    symbol: Optional[str] = None
):
    """Screen high-conviction multi-scanner confluence setups (delegates to PredictionAgent)."""
    from agents.prediction_agent import PredictionAgent
    agent = _get_agent(request, "prediction_agent", PredictionAgent)
    return await agent.get_predictions(symbol=symbol)
