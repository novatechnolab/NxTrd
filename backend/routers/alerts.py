"""
TradeSignal NextGen — Router: alerts
Rule: Delegate to PremiumSpikeAgent only. No direct SQL or alert calculations here.
Ported from reference: server.py L5404-5470
"""
from typing import Optional
from fastapi import APIRouter, Request, Query

router = APIRouter()


def _get_spike_agent(request: Request):
    """Retrieve PremiumSpikeAgent from app state."""
    app_obj = getattr(request, "app", None)
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent("premium_spike_agent")
            if agent:
                return agent
        agent = getattr(app_obj.state, "premium_spike_agent", None)
        if agent:
            return agent

    from agents.premium_spike_agent import PremiumSpikeAgent
    from core.event_bus import EventBus
    return PremiumSpikeAgent(EventBus())


@router.get("/option-gainers-alerts")
async def option_gainers_alerts(
    request: Request,
    date: Optional[str] = Query(None),
    after: Optional[int] = Query(None)
):
    """Fetch live or historical option premium spike alerts."""
    agent = _get_spike_agent(request)
    alerts = await agent.get_recent_alerts(date_str=date, after=after)
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "trade_date": date
    }


@router.get("/option-gainers-alerts/status")
async def option_gainers_alerts_status(request: Request):
    """Diagnostic status for the option premium spike agent."""
    agent = _get_spike_agent(request)
    return await agent.get_alert_status()


@router.post("/option-gainers-alerts/clear")
async def option_gainers_alerts_clear(request: Request):
    """Clear active in-memory alerts."""
    agent = _get_spike_agent(request)
    ok = await agent.clear_alerts()
    return {"ok": ok}


@router.get("/eod-alert-summary")
async def eod_alert_summary(
    request: Request,
    date: Optional[str] = Query(None)
):
    """Return End-of-Day alert summary."""
    agent = _get_spike_agent(request)
    return await agent.get_eod_summary(date_str=date)
