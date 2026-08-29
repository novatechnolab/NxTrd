"""
TradeSignal NextGen — Router: core
Rule: Reuses AgentOrchestrator for system status & repositories/journal.py for notes CRUD.
No duplicate agent created.
Ported from reference: server.py L1000-1500
"""
from typing import Optional
from datetime import datetime as dt
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from repositories import journal as repo_journal
from core.utils import now_ist

router = APIRouter()


class NoteCreateRequest(BaseModel):
    title: str
    content: str
    symbol: Optional[str] = None
    sentiment: Optional[str] = "NEUTRAL"


@router.get("/health")
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "TradeSignal NextGen",
        "version": "2.0.0",
        "timestamp": now_ist().isoformat()
    }


@router.get("/system/status")
async def system_status(request: Request):
    """Return live status of orchestrator and all registered domain agents."""
    app_obj = getattr(request, "app", None)
    orchestrator = getattr(app_obj.state, "orchestrator", None) if app_obj else None
    if orchestrator:
        health_data = orchestrator.get_health_status()
    else:
        health_data = {
            "orchestrator_running": False,
            "total_agents": 0,
            "healthy_agents": 0,
            "agents": {}
        }

    return {
        "status": "ok",
        **health_data,
        "timestamp": now_ist().isoformat()
    }


@router.get("/notes")
async def list_notes(symbol: Optional[str] = None):
    """Fetch trading journal notes with optional symbol filter."""
    notes = repo_journal.get_all_notes(symbol=symbol)
    return {
        "status": "ok",
        "count": len(notes),
        "notes": notes
    }


@router.post("/notes")
async def create_note(payload: NoteCreateRequest):
    """Save a new trading journal note."""
    note_id = repo_journal.add_note(
        title=payload.title,
        content=payload.content,
        symbol=payload.symbol,
        sentiment=payload.sentiment or "NEUTRAL"
    )
    return {
        "status": "ok",
        "id": note_id,
        "message": "Note saved successfully"
    }


@router.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    """Delete a trading journal note by ID."""
    deleted = repo_journal.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {
        "status": "ok",
        "id": note_id,
        "message": "Note deleted successfully"
    }


# ── Configuration & Kite Login ───────────────────────────────────────

class LoginRequest(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    request_token: Optional[str] = None


@router.get("/config")
async def get_config():
    """Return runtime configuration and session state."""
    import os
    from core.session_utils import load_kite_session
    saved_key, saved_token = load_kite_session()
    env_key = os.environ.get("KITE_API_KEY", "")
    has_env_secret = bool(os.environ.get("KITE_API_SECRET", ""))

    active_key = saved_key or env_key
    masked_key = "••••••••••••••" if active_key else ""
    masked_token = "••••••••••••••••••••••••••••" if saved_token else ""

    return {
        "status": "ok",
        "api_key": active_key,
        "api_key_masked": masked_key,
        "access_token_masked": masked_token,
        "has_access_token": bool(saved_token),
        "has_env_secret": has_env_secret,
        "scoring_defaults": {
            "score_threshold": 70,
            "max_ivp": 50,
            "min_rr": 2.0,
            "min_oi": 5000,
            "pos_size_pct": 20
        }
    }


@router.post("/login")
async def kite_login(payload: LoginRequest, request: Request):
    """
    Exchange request_token for access_token using KiteConnect API.
    Saves session to disk for auto-reconnect on server restart.
    """
    import os
    import re
    from core.session_utils import save_kite_session

    env_key = os.environ.get("KITE_API_KEY", "")
    env_secret = os.environ.get("KITE_API_SECRET", "")

    api_key = re.sub(r"\s+", "", str(payload.api_key or env_key or "")).strip()
    api_secret = re.sub(r"\s+", "", str(payload.api_secret or env_secret or "")).strip()
    request_token = re.sub(r"\s+", "", str(payload.request_token or "")).strip()

    if not api_key:
        raise HTTPException(status_code=400, detail="Kite API Key is missing.")
    if not api_secret:
        raise HTTPException(status_code=400, detail="Kite API Secret is missing.")
    if not request_token:
        raise HTTPException(status_code=400, detail="Request Token is missing.")

    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        session_data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = session_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token from Kite API.")

        save_kite_session(api_key, access_token)

        # Reset KiteDataAgent session
        app_obj = getattr(request, "app", None)
        if app_obj and hasattr(app_obj.state, "kite_data_agent"):
            app_obj.state.kite_data_agent.reset_session()

        return {
            "status": "ok",
            "message": "Connected successfully",
            "access_token": access_token,
            "user_id": session_data.get("user_id", "")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kite login error: {str(e)}")


# ── Cache Management ──────────────────────────────────────────────────

@router.get("/cache/stats")
async def cache_statistics():
    """Return local SQLite OHLCV and instruments cache statistics."""
    from core.db import get_cache_stats
    return get_cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear OHLCV cache records."""
    from core.db import clear_ohlcv_cache
    return clear_ohlcv_cache()


def _get_kite_data_agent(request: Request):
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


@router.get("/historical")
async def api_historical(request: Request):
    """Fetch historical candles via KiteDataAgent with smart SQLite caching."""
    token_str = request.query_params.get("token") or request.query_params.get("instrument_token") or ""
    sym = request.query_params.get("symbol") or ""
    from_str = request.query_params.get("from") or request.query_params.get("from_date") or ""
    to_str = request.query_params.get("to") or request.query_params.get("to_date") or ""
    interval = request.query_params.get("interval") or "5minute"

    token = int(token_str) if token_str.isdigit() else None

    from_dt = None
    to_dt = None
    if from_str:
        try:
            from_dt = dt.strptime(from_str.split("T")[0], "%Y-%m-%d")
        except Exception:
            pass
    if to_str:
        try:
            to_dt = dt.strptime(to_str.split("T")[0], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except Exception:
            pass

    agent = _get_kite_data_agent(request)
    res = await agent.get_historical(
        symbol=sym.upper() if sym else "",
        token=token,
        interval=interval,
        from_dt=from_dt,
        to_dt=to_dt
    )
    return res


