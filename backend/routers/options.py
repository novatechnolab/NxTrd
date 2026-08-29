"""
TradeSignal NextGen — Router: options
Rule: Delegate to OiTransitionAgent and MaxPainAgent only. No business logic here.
Ported from reference: server.py L4500-4840
"""
from typing import Optional
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


@router.get("/option-chain")
@router.get("/oi-chain")
async def option_chain(
    request: Request,
    symbol: str = "NIFTY"
):
    """Fetch live option chain with CE/PE OI and strike levels."""
    from agents.oi_transition_agent import OiTransitionAgent
    agent = _get_agent(request, "oi_transition_agent", OiTransitionAgent)
    return await agent.get_option_chain(symbol=symbol)


@router.get("/oi-transition")
async def oi_transition(
    request: Request,
    symbol: Optional[str] = None
):
    """Fetch live OI transition events (call unwinding, put writing surges)."""
    from agents.oi_transition_agent import OiTransitionAgent
    agent = _get_agent(request, "oi_transition_agent", OiTransitionAgent)
    return await agent.get_oi_transitions(symbol=symbol)


@router.get("/pcr")
async def pcr_summary(
    request: Request,
    symbol: str = "NIFTY"
):
    """Fetch Put-Call Ratio analytics."""
    from agents.max_pain_agent import MaxPainAgent
    agent = _get_agent(request, "max_pain_agent", MaxPainAgent)
    return await agent.get_pcr_summary(symbol=symbol)
