"""
TradeSignal NextGen — Auth Utilities
Reference: /home/rajk/Downloads/TradeSignal005/Agent backup/TradeSignal -Backup April24-Agentic/app/backend/server.py L525-560
"""
import os
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.environ.get("APP_USERNAME", "")
    correct_password = os.environ.get("APP_PASSWORD", "")
    if not correct_username:
        return True  # Auth disabled if no credentials set
    ok = (
        secrets.compare_digest(credentials.username, correct_username) and
        secrets.compare_digest(credentials.password, correct_password)
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True
