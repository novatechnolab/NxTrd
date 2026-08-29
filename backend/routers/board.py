"""
TradeSignal NextGen — Router: board
Rule: Delegate to BoardAgent only. No SQL, no raw calculations, no business logic here.
Ported from reference: server.py L4843-5403
"""
from typing import Optional, List
from fastapi import APIRouter, Request, Query, Body
from pydantic import BaseModel

router = APIRouter()


class TractionBoardRequest(BaseModel):
    symbols: Optional[List[str]] = []
    period: Optional[int] = 60
    cap: Optional[str] = "large"


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


@router.get("/option-gainers-board")
async def option_gainers_board(request: Request):
    """Fetch live Option Gainers Board."""
    agent = _get_board_agent(request)
    return await agent.get_gainers_board()


@router.get("/option-gainers/timeline")
async def option_gainers_timeline(
    request: Request,
    token: Optional[int] = None,
    symbol: Optional[str] = None,
    strike: Optional[float] = None,
    opt_type: Optional[str] = None,
    date: Optional[str] = None,
    step: float = 20.0
):
    """Compute cumulative incremental milestone timeline for an option contract."""
    agent = _get_board_agent(request)
    return await agent.get_contract_timeline(
        token=token,
        symbol=symbol,
        strike=strike,
        opt_type=opt_type,
        date_str=date,
        step_pct=step
    )


@router.get("/traction-board")
@router.post("/traction-board")
async def traction_board(
    request: Request,
    symbols: Optional[str] = None,
    period: int = 60,
    cap: str = "large",
    payload: Optional[TractionBoardRequest] = None
):
    """Fetch Traction Board 360° analytics."""
    agent = _get_board_agent(request)
    
    target_symbols = None
    target_period = period
    target_cap = cap

    if isinstance(payload, TractionBoardRequest):
        if payload.symbols:
            target_symbols = payload.symbols
        if payload.period:
            target_period = payload.period
        if payload.cap:
            target_cap = payload.cap
    elif symbols:
        target_symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    return await agent.get_traction_board(
        symbols=target_symbols,
        period=target_period,
        cap=target_cap
    )
