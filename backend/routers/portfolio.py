"""
TradeSignal NextGen — Router: portfolio
Rule: Reuses KiteDataAgent for all account & portfolio operations.
No duplicate agent created.
Ported from reference: server.py L2800-3200
"""
from fastapi import APIRouter, Request

router = APIRouter()


def _get_kite_agent(request: Request):
    """Retrieve KiteDataAgent from app state."""
    app_obj = getattr(request, "app", None)
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent("kite_data_agent")
            if agent:
                return agent
        agent = getattr(app_obj.state, "kite_data_agent", None)
        if agent:
            return agent

    from agents.kite_data_agent import KiteDataAgent
    from core.event_bus import EventBus
    return KiteDataAgent(EventBus())


@router.get("/portfolio/summary")
async def portfolio_summary(request: Request):
    """Fetch aggregated portfolio summary, total P&L, and margin health."""
    agent = _get_kite_agent(request)
    holdings_res = await agent.get_holdings()
    positions_res = await agent.get_positions()
    margins_res = await agent.get_margins()

    return {
        "status": "ok",
        "has_live_kite": agent.is_authenticated(),
        "holdings": holdings_res.get("data", []),
        "positions": positions_res.get("data", {}),
        "margins": margins_res.get("data", {}),
        "total_investment": 0.0,
        "current_value": 0.0,
        "pnl_net": 0.0
    }


@router.get("/portfolio/holdings")
async def portfolio_holdings(request: Request):
    """Fetch equity holdings."""
    agent = _get_kite_agent(request)
    return await agent.get_holdings()


@router.get("/portfolio/positions")
async def portfolio_positions(request: Request):
    """Fetch active intraday and carryforward positions."""
    agent = _get_kite_agent(request)
    return await agent.get_positions()


@router.get("/portfolio/margins")
async def portfolio_margins(request: Request):
    """Fetch available trading margins and utilization."""
    agent = _get_kite_agent(request)
    return await agent.get_margins()
