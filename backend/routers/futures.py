"""
TradeSignal NextGen — Router: futures
Rule: Delegate to BoardAgent only. No direct calculations or DB queries here.
Ported from reference: server.py L12133-12250
"""
from fastapi import APIRouter, Request

router = APIRouter()


def _get_board_agent(request: Request):
    """Retrieve BoardAgent from app state."""
    app_obj = getattr(request, "app", None)
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent("board_agent")
            if agent:
                return agent
        agent = getattr(app_obj.state, "board_agent", None)
        if agent:
            return agent

    from agents.board_agent import BoardAgent
    from core.event_bus import EventBus
    return BoardAgent(EventBus())


@router.get("/futures-buildup")
async def futures_buildup(request: Request):
    """Fetch near-month futures buildup across all tracked F&O symbols."""
    agent = _get_board_agent(request)
    return await agent.get_fut_buildup()
