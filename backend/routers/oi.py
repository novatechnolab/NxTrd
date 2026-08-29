"""
TradeSignal NextGen — Router: OI (Open Interest)
==================================================
10 routes covering OI scanner, OI spurt, and symbol deep-dive.
Rule: Delegates to OiTransitionAgent only — zero business logic here.

Reference routes ported from:
  oi_scanner_routes.py  →  /health, /tickers, /options-chain,
                            /oi-analysis, /scan, /positions,
                            /scanner, /scanner/reset
  oi_spurt_routes.py    →  /spurt, /symbol/{symbol}
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_oi_agent(request: Request):
    """Retrieve OiTransitionAgent from app state."""
    agent = getattr(request.app.state, "oi_transition_agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="OiTransitionAgent not available")
    return agent


# ── Health ─────────────────────────────────────────────────────────────────

@router.get("/oi/health", tags=["OI"])
async def oi_health():
    """OI subsystem health check."""
    return {"status": "ok", "subsystem": "oi"}


# ── Tickers ────────────────────────────────────────────────────────────────

@router.get("/oi/tickers", tags=["OI"])
async def oi_tickers(request: Request) -> Dict[str, Any]:
    """
    List of symbols currently tracked by the OI scanner.
    Reference: oi_scanner_routes.py /tickers
    """
    agent = _get_oi_agent(request)
    return await agent.get_tracked_symbols()


# ── Options Chain ──────────────────────────────────────────────────────────

@router.get("/oi/options-chain", tags=["OI"])
async def options_chain(
    request: Request,
    symbol: str = "NIFTY",
) -> Dict[str, Any]:
    """
    Full option chain for an underlying symbol (strikes, OI, LTP, IV, PCR).
    Reference: oi_scanner_routes.py /options-chain
    """
    agent = _get_oi_agent(request)
    return await agent.get_option_chain(symbol)


# ── OI Analysis ────────────────────────────────────────────────────────────

@router.get("/oi/oi-analysis", tags=["OI"])
async def oi_analysis(
    request: Request,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Live OI transition events: call unwinding, put writing, trap signals.
    Reference: oi_scanner_routes.py /oi-analysis
    """
    agent = _get_oi_agent(request)
    return await agent.get_oi_transitions(symbol)


# ── Real-time Scan ─────────────────────────────────────────────────────────

@router.post("/oi/scan", tags=["OI"])
async def realtime_scan(
    request: Request,
    payload: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Trigger an on-demand OI scan for specified symbols.
    Reference: oi_scanner_routes.py /scan (POST)
    Body: { "symbols": ["NIFTY", "BANKNIFTY"], ... }
    """
    agent = _get_oi_agent(request)
    body = payload or {}
    return await agent.run_scan(body)


# ── Positions ──────────────────────────────────────────────────────────────

@router.get("/oi/positions", tags=["OI"])
async def oi_positions(request: Request) -> Dict[str, Any]:
    """
    OI-derived position summary (net OI, CE/PE buildup per symbol).
    Reference: oi_scanner_routes.py /positions
    """
    agent = _get_oi_agent(request)
    return await agent.get_positions()


# ── OI Spurt Scanner ───────────────────────────────────────────────────────

@router.get("/oi/scanner", tags=["OI"])
async def oi_scanner(request: Request) -> Dict[str, Any]:
    """
    Latest OI spurt scanner results (significant OI change events).
    Reference: oi_scanner_routes.py /scanner
    """
    agent = _get_oi_agent(request)
    return await agent.get_scanner_results()


@router.post("/oi/scanner/reset", tags=["OI"])
async def oi_scanner_reset(request: Request) -> Dict[str, Any]:
    """
    Reset OI baseline. Next scan cycle captures fresh OI deltas from now.
    Reference: oi_scanner_routes.py /scanner/reset (POST)
    """
    agent = _get_oi_agent(request)
    return await agent.reset_baseline()


# ── OI Spurt List ──────────────────────────────────────────────────────────

@router.get("/oi/spurt", tags=["OI"])
async def oi_spurt(
    request: Request,
    min_pct: float = 5.0,
) -> Dict[str, Any]:
    """
    Instruments with OI change >= min_pct since session open (enriched).
    Reference: oi_spurt_routes.py /spurt
    """
    agent = _get_oi_agent(request)
    return await agent.get_oi_spurt(min_pct)


# ── Symbol Deep-Dive ───────────────────────────────────────────────────────

@router.get("/oi/symbol/{symbol}", tags=["OI"])
async def oi_symbol_detail(
    symbol: str,
    request: Request,
) -> Dict[str, Any]:
    """
    Full symbol detail: pivots, PCR, max pain, ATM strikes, OI transitions.
    Reference: oi_spurt_routes.py /symbol/<symbol>
    """
    agent = _get_oi_agent(request)
    return await agent.get_symbol_detail(symbol)
