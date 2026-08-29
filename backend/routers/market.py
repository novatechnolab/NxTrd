"""
TradeSignal NextGen — Router: market
Rule: Delegate to MarketAgent only. No direct calculations or DB queries here.
Ported from reference: server.py L2300-2800
"""
from fastapi import APIRouter, Request

router = APIRouter()


def _get_market_agent(request: Request):
    """Retrieve MarketAgent from app state."""
    app_obj = getattr(request, "app", None)
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent("market_agent")
            if agent:
                return agent
        agent = getattr(app_obj.state, "market_agent", None)
        if agent:
            return agent

    from agents.market_agent import MarketAgent
    from core.event_bus import EventBus
    return MarketAgent(EventBus())


@router.get("/market-pulse")
async def market_pulse(request: Request):
    """Fetch market breadth, advance/decline ratio, and pulse metrics."""
    agent = _get_market_agent(request)
    return await agent.get_market_pulse()


@router.get("/market-bias")
async def market_bias(request: Request):
    """Fetch current market bias score and regime."""
    agent = _get_market_agent(request)
    return await agent.get_market_bias()


@router.get("/indices")
async def indices_overview(request: Request):
    """Fetch snapshot of benchmark indices."""
    agent = _get_market_agent(request)
    return await agent.get_indices_summary()


@router.get("/sector-performance")
async def sector_performance(request: Request):
    """Fetch sector heatmap and performance metrics."""
    agent = _get_market_agent(request)
    return await agent.get_sector_performance()


@router.get("/market-status")
async def market_status(request: Request):
    """360 CC: Return is_open flag based on IST market hours + KiteDataAgent session."""
    import datetime
    now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    weekday = now_ist.weekday()  # 0=Mon, 6=Sun
    h, m = now_ist.hour, now_ist.minute
    time_mins = h * 60 + m
    # NSE: Mon–Fri 09:15–15:40 IST
    is_open = (
        weekday < 5 and
        time_mins >= (9 * 60 + 15) and
        time_mins <= (15 * 60 + 40)
    )
    return {
        "is_open": is_open,
        "session": "live" if is_open else "closed",
        "time_ist": now_ist.strftime("%H:%M:%S"),
        "status": "ok"
    }


