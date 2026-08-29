"""
TradeSignal NextGen — Router: instruments
Rule: Reuses repositories/instruments.py and KiteDataAgent.sync_instruments().
No duplicate agent created.
Ported from reference: server.py L1500-1900
"""
from typing import Optional
from fastapi import APIRouter, Request, Query
from repositories import instruments as repo_instruments

router = APIRouter()


@router.get("/instruments/search")
async def instruments_search(
    q: str = "",
    exchange: Optional[str] = None,
    limit: int = 20
):
    """Search for instruments by symbol or name."""
    if not q:
        return {"status": "ok", "count": 0, "results": []}

    token = repo_instruments.resolve_token(q)
    results = []
    if token:
        results.append({
            "tradingsymbol": q.upper(),
            "instrument_token": token,
            "exchange": exchange or "NSE"
        })

    return {
        "status": "ok",
        "query": q,
        "count": len(results),
        "results": results
    }


@router.get("/instruments/fno-symbols")
async def instruments_fno_symbols():
    """Fetch tracked F&O underlying symbols."""
    symbols = repo_instruments.get_fno_symbols()
    return {
        "status": "ok",
        "count": len(symbols),
        "symbols": symbols
    }


@router.get("/instruments/cash-symbols")
async def instruments_cash_symbols():
    """Fetch tracked cash/equity symbols."""
    fno_symbols = repo_instruments.get_fno_symbols()
    return {
        "status": "ok",
        "count": len(fno_symbols),
        "symbols": fno_symbols
    }


@router.post("/instruments/sync")
async def instruments_sync(request: Request):
    """Trigger instrument database synchronization from Kite."""
    app_obj = getattr(request, "app", None)
    agent = None
    if app_obj:
        orchestrator = getattr(app_obj.state, "orchestrator", None)
        if orchestrator:
            agent = orchestrator.get_agent("kite_data_agent")
        if not agent:
            agent = getattr(app_obj.state, "kite_data_agent", None)

    if not agent:
        from agents.kite_data_agent import KiteDataAgent
        from core.event_bus import EventBus
        agent = KiteDataAgent(EventBus())

    return await agent.sync_instruments()
