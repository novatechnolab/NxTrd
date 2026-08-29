"""
TradeSignal NextGen — Router: analytics
Rule: Delegate to EmaAgent, MaxPainAgent, and SynergyAgent only. No business logic here.
Ported from reference: server.py L3500-4500
"""
from typing import Optional, List
from fastapi import APIRouter, Request, Query

router = APIRouter()


def _get_agent(request: Request, agent_name: str, agent_cls):
    """Retrieve agent from app state or create fallback instance."""
    app_obj = getattr(request, "app", None)
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent(agent_name)
            if agent:
                return agent
        agent = getattr(app_obj.state, agent_name, None)
        if agent:
            return agent

    from core.event_bus import EventBus
    return agent_cls(EventBus())


@router.get("/ema-crossover")
async def ema_crossover(
    request: Request,
    timeframe: str = "5",
    symbols: Optional[str] = None
):
    """Fetch EMA 9/21 crossovers and multi-timeframe alignment."""
    from agents.ema_agent import EmaAgent
    agent = _get_agent(request, "ema_agent", EmaAgent)
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else None
    return await agent.get_ema_crossovers(timeframe=timeframe, symbols=sym_list)


@router.get("/max-pain")
async def max_pain(
    request: Request,
    symbol: str = "NIFTY"
):
    """Fetch Max Pain strike and deviation for a symbol."""
    from agents.max_pain_agent import MaxPainAgent
    agent = _get_agent(request, "max_pain_agent", MaxPainAgent)
    return await agent.get_max_pain(symbol=symbol)


@router.get("/max-pain/deviation")
@router.get("/maxpain/deviation")
async def max_pain_deviation_matrix(request: Request):
    """Fetch full F&O Max Pain deviation matrix."""
    from agents.max_pain_agent import MaxPainAgent
    agent = _get_agent(request, "max_pain_agent", MaxPainAgent)
    return await agent.get_max_pain_matrix()


@router.get("/synergy-matrix")
async def synergy_matrix(request: Request):
    """Fetch F&O Synergy BUY/SELL profile matrix."""
    from agents.synergy_agent import SynergyAgent
    agent = _get_agent(request, "synergy_agent", SynergyAgent)
    return await agent.get_synergy_matrix()


@router.get("/synergy")
async def multi_tf_synergy(
    request: Request,
    symbols: Optional[str] = None
):
    """Fetch Multi-Timeframe Alignment matrix."""
    from agents.synergy_agent import SynergyAgent
    agent = _get_agent(request, "synergy_agent", SynergyAgent)
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else None
    return await agent.get_synergy_matrix(symbols=sym_list)


@router.get("/conviction-score")
async def conviction_score(request: Request):
    """Fetch conviction score leaderboard."""
    from agents.synergy_agent import SynergyAgent
    agent = _get_agent(request, "synergy_agent", SynergyAgent)
    return await agent.get_conviction_scores()


@router.get("/ema-crossovers")
async def ema_crossovers_360(
    request: Request,
    timeframe: str = "5"
):
    """360 CC alias: reshape /ema-crossover output to {crossovers: {}} format."""
    from agents.ema_agent import EmaAgent
    agent = _get_agent(request, "ema_agent", EmaAgent)
    data = await agent.get_ema_crossovers(timeframe=timeframe)
    crossovers = data.get("crossovers", data.get("data", {}))
    if isinstance(crossovers, list):
        cross_map = {item.get("symbol", ""): item for item in crossovers if item.get("symbol")}
    else:
        cross_map = crossovers if isinstance(crossovers, dict) else {}
    return {"crossovers": cross_map, "bulls": data.get("bulls", []), "bears": data.get("bears", [])}


@router.get("/ema_convergence_watchlist")
async def ema_convergence_watchlist(request: Request):
    """360 CC: EMA 9/21 pre-cross convergence watchlist."""
    from agents.ema_agent import EmaAgent
    agent = _get_agent(request, "ema_agent", EmaAgent)
    if hasattr(agent, "get_convergence_watchlist"):
        return await agent.get_convergence_watchlist()
    return {"watchlist": [], "status": "ok", "count": 0}


@router.get("/live-breakouts")
async def live_breakouts(request: Request):
    """360 CC: Live EMA crossover breakout events."""
    from agents.ema_agent import EmaAgent
    agent = _get_agent(request, "ema_agent", EmaAgent)
    return await agent.get_live_breakouts()

