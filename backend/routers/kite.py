"""
TradeSignal NextGen — Router: kite
Rule: Delegate to KiteDataAgent and core/session_utils only.
No direct SQL, no business logic, no synchronous Kite calls here.
Ported from reference: server.py L1873-2258
"""
from typing import Optional, List
from datetime import datetime as dt
from fastapi import APIRouter, Request, HTTPException, Body, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.session_utils import (
    save_kite_session, load_kite_session, clear_kite_session,
    get_kite_credentials, kite_session_debug
)
from repositories import instruments as repo_instruments

router = APIRouter()


class AuthRequest(BaseModel):
    api_key: str
    access_token: str


class WsStartRequest(BaseModel):
    tokens: Optional[List[int]] = []


def _get_data_agent(request: Request):
    """Retrieve KiteDataAgent from FastAPI app state."""
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


# ── Authentication Endpoints ─────────────────────────────────────────

@router.post("/auth")
async def kite_auth(payload: AuthRequest, request: Request):
    """Save Kite API credentials and reset cached client."""
    if not payload.api_key.strip() or not payload.access_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key and access_token required"
        )
    save_kite_session(payload.api_key.strip(), payload.access_token.strip())
    agent = _get_data_agent(request)
    agent.reset_session()
    return {"status": "ok", "message": "Credentials saved"}


@router.get("/auth/session")
async def kite_auth_session():
    """Return active Kite credentials for frontend/mobile hydration."""
    api_key, access_token = load_kite_session()
    if not api_key or not access_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session found")
    return {
        "status": "ok",
        "api_key": api_key,
        "access_token": access_token
    }


@router.get("/auth/status")
async def kite_auth_status(request: Request):
    """Local-only session check without hitting Zerodha rate limits."""
    agent = _get_data_agent(request)
    if not agent.is_authenticated():
        return {"status": "no_token", "message": "No access_token configured."}
    return {"status": "ok", "broker": "ZERODHA", "user": "", "user_id": ""}


@router.post("/auth/logout")
async def kite_auth_logout(request: Request):
    """Clear session credentials."""
    clear_kite_session()
    agent = _get_data_agent(request)
    agent.reset_session()
    return {"status": "ok", "message": "Logged out successfully"}


# ── Market Data Endpoints ─────────────────────────────────────────────

@router.get("/historical")
async def kite_historical(
    request: Request,
    symbol: str = "",
    instrument_token: Optional[int] = None,
    interval: str = "5",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    oi: str = "0"
):
    """Fetch historical candle data."""
    agent = _get_data_agent(request)
    
    from_dt = None
    to_dt = None
    if from_date:
        try:
            from_dt = dt.fromisoformat(from_date.replace("Z", "+00:00"))
        except Exception:
            pass
    if to_date:
        try:
            to_dt = dt.fromisoformat(to_date.replace("Z", "+00:00"))
        except Exception:
            pass

    include_oi = (str(oi) == "1")
    result = await agent.get_historical(
        symbol=symbol.upper() if symbol else "",
        token=instrument_token,
        interval=interval or "5",
        from_dt=from_dt,
        to_dt=to_dt,
        include_oi=include_oi
    )
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=result)
    return result


@router.get("/quote")
async def kite_quote(
    request: Request,
    symbols: str = "NIFTY50"
):
    """Fetch quotes for given symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    agent = _get_data_agent(request)
    result = await agent.get_quote(sym_list)
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


@router.get("/ltp")
async def kite_ltp(
    request: Request,
    symbols: str = "NIFTY50"
):
    """Fetch LTP map for given symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    agent = _get_data_agent(request)
    result = await agent.get_ltp(sym_list)
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


# ── Account & Portfolio Endpoints ────────────────────────────────────

@router.get("/profile")
async def kite_profile(request: Request):
    """Fetch user profile."""
    agent = _get_data_agent(request)
    result = await agent.get_profile()
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


@router.get("/holdings")
async def kite_holdings(request: Request):
    """Fetch account holdings."""
    agent = _get_data_agent(request)
    result = await agent.get_holdings()
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


@router.get("/positions")
async def kite_positions(request: Request):
    """Fetch account positions."""
    agent = _get_data_agent(request)
    result = await agent.get_positions()
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


@router.get("/margins")
async def kite_margins(request: Request):
    """Fetch margin balances."""
    agent = _get_data_agent(request)
    result = await agent.get_margins()
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


# ── Instrument Management ─────────────────────────────────────────────

@router.get("/instruments")
async def kite_instruments(
    search: str = "",
    exchange: str = "NSE"
):
    """Search instruments from SQLite repository."""
    search_term = (search or "").strip().upper()
    if not search_term:
        all_inst = repo_instruments.get_all()
        indices = [
            {"symbol": i["tradingsymbol"], "token": i["instrument_token"], "exchange": i["exchange"]}
            for i in all_inst if i.get("segment") == "INDICES"
        ][:100]
        return {"status": "ok", "instruments": indices}

    exch = (exchange or "NSE").strip().upper()
    if exch == "ALL":
        all_inst = repo_instruments.get_all()
    else:
        all_inst = repo_instruments.get_cached_instruments(exchange=exch)

    matches = [
        {
            "token": i["instrument_token"],
            "symbol": i["tradingsymbol"],
            "name": i.get("name", ""),
            "exchange": i.get("exchange", ""),
            "type": i.get("instrument_type", "")
        }
        for i in all_inst
        if search_term in i.get("tradingsymbol", "") or search_term in (i.get("name") or "").upper()
    ][:50]

    return {"status": "ok", "count": len(matches), "instruments": matches}


@router.post("/instruments/sync")
async def kite_instruments_sync(request: Request):
    """Trigger full sync of instruments from Kite to SQLite."""
    agent = _get_data_agent(request)
    result = await agent.sync_instruments()
    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=result)
    return result


# ── Live Ticker / WebSocket Controls ──────────────────────────────────

@router.post("/ws/start")
async def kite_ws_start(request: Request, payload: Optional[WsStartRequest] = Body(None)):
    """Start KiteTicker live data streaming."""
    agent = _get_data_agent(request)
    tokens = payload.tokens if payload and payload.tokens else []
    return agent.start_ws(tokens)


@router.post("/ws/stop")
async def kite_ws_stop(request: Request):
    """Stop KiteTicker."""
    agent = _get_data_agent(request)
    return agent.stop_ws()


@router.get("/ws/snapshot")
async def kite_ws_snapshot(request: Request):
    """Return memory tick snapshot."""
    agent = _get_data_agent(request)
    return agent.get_tick_snapshot()


@router.get("/global-quotes")
async def kite_global_quotes(request: Request):
    """360 CC: Return NIFTY, BANKNIFTY, VIX, USDINR index quotes."""
    agent = _get_data_agent(request)
    try:
        result = await agent.get_quote(["NIFTY 50", "NIFTY BANK", "INDIA VIX"])
        data = result.get("data", {}) if isinstance(result, dict) else {}
        def _extract(sym):
            entry = data.get(sym) or data.get(f"NSE:{sym}") or {}
            if isinstance(entry, dict):
                return {
                    "ltp": entry.get("last_price") or entry.get("ltp") or 0,
                    "change": entry.get("change") or entry.get("net_change") or 0,
                    "pct": entry.get("change_pct") or entry.get("change_percent") or 0
                }
            elif isinstance(entry, (int, float)):
                return {"ltp": float(entry), "change": 0, "pct": 0}
            return {"ltp": 0, "change": 0, "pct": 0}
        return {
            "status": "ok",
            "NIFTY": _extract("NIFTY 50"),
            "BANKNIFTY": _extract("NIFTY BANK"),
            "VIX": _extract("INDIA VIX"),
            "USDINR": {"ltp": 0, "change": 0, "pct": 0}
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "NIFTY": {"ltp": 0, "change": 0, "pct": 0},
            "BANKNIFTY": {"ltp": 0, "change": 0, "pct": 0},
            "VIX": {"ltp": 0, "change": 0, "pct": 0},
            "USDINR": {"ltp": 0, "change": 0, "pct": 0}
        }



