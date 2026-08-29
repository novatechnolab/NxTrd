"""
TradeSignal NextGen — Session Utilities
Handles Kite authentication credentials persistence and recovery.
Works across FastAPI requests, background tasks, and survives server restarts (laptop & Termux).
Ported from reference: server.py L1170-1230
"""
import os
import json
import logging
from typing import Optional, Tuple
from fastapi import Request

logger = logging.getLogger(__name__)

_SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SESSION_FILE = os.path.join(_SESSION_DIR, ".kite_session.json")


def save_kite_session(api_key: str, access_token: str) -> bool:
    """Persist Kite credentials to disk so they survive server/Termux restarts."""
    try:
        with open(_SESSION_FILE, "w") as f:
            json.dump({"api_key": api_key, "access_token": access_token}, f)
        return True
    except Exception as e:
        logger.warning(f"[SESSION] Could not save session file: {e}")
        return False


def load_kite_session() -> Tuple[Optional[str], Optional[str]]:
    """Load persisted Kite credentials from disk (Termux/laptop restart recovery)."""
    try:
        if os.path.isfile(_SESSION_FILE):
            with open(_SESSION_FILE, "r") as f:
                data = json.load(f)
            api_key = data.get("api_key", "").strip()
            access_token = data.get("access_token", "").strip()
            if api_key and access_token:
                return api_key, access_token
    except Exception as e:
        logger.warning(f"[SESSION] Could not read session file: {e}")
    return None, None


def clear_kite_session() -> bool:
    """Delete persisted session file (called on explicit logout)."""
    try:
        if os.path.isfile(_SESSION_FILE):
            os.remove(_SESSION_FILE)
            return True
    except Exception as e:
        logger.warning(f"[SESSION] Could not remove session file: {e}")
    return False


def get_kite_credentials(request: Optional[Request] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve Kite credentials using standard priority:
    1. HTTP Request Headers (X-Kite-Api-Key, X-Kite-Access-Token)
    2. Persisted Disk Session (.kite_session.json)
    3. Environment Variables (KITE_API_KEY, KITE_ACCESS_TOKEN)
    """
    if request:
        header_key = (request.headers.get("X-Kite-Api-Key") or "").strip()
        header_token = (request.headers.get("X-Kite-Access-Token") or "").strip()
        if header_key and header_token:
            return header_key, header_token

    disk_key, disk_token = load_kite_session()
    if disk_key and disk_token:
        return disk_key, disk_token

    env_key = os.environ.get("KITE_API_KEY", "").strip()
    env_token = os.environ.get("KITE_ACCESS_TOKEN", "").strip()
    if env_key and env_token:
        return env_key, env_token

    return None, None


def kite_session_debug(request: Optional[Request] = None) -> dict:
    """Non-secret auth-source diagnostics for 401 responses / status endpoints."""
    header_key = request.headers.get("X-Kite-Api-Key") if request else None
    header_token = request.headers.get("X-Kite-Access-Token") if request else None
    disk_key, disk_token = load_kite_session()

    return {
        "has_header_api_key": bool(header_key),
        "has_header_access_token": bool(header_token),
        "has_disk_api_key": bool(disk_key),
        "has_disk_access_token": bool(disk_token),
        "has_env_api_key": bool(os.environ.get("KITE_API_KEY")),
        "has_env_access_token": bool(os.environ.get("KITE_ACCESS_TOKEN")),
    }
