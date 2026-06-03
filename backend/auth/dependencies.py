
"""Lightweight auth for Phase 1 (localhost)."""
import os
import secrets
from fastapi import Request, HTTPException, WebSocketException, status
from typing import Optional

DEV_TOKEN = os.environ.get("JARVIS_DASHBOARD_DEV_TOKEN", "")
DEV_USER = os.environ.get("JARVIS_DASHBOARD_DEV_USER", "saiyudh")


def _is_dev_token(token: Optional[str]) -> bool:
    return bool(token and DEV_TOKEN and secrets.compare_digest(token, DEV_TOKEN))


def get_current_user(request: Request) -> str:
    """
    Phase 1 auth: accept a configured dev token query param or a JWT cookie.
    No localhost fallthrough — auth is mandatory everywhere.
    """
    token = request.cookies.get("jarvis-dashboard-token")
    if not token:
        token = request.query_params.get("token")
    if _is_dev_token(token):
        return DEV_USER
    try:
        from auth.jwt_handler import decode_token
        payload = decode_token(token)
        return payload.get("sub", "anonymous")
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")


def get_current_user_ws(token: Optional[str] = None) -> str:
    if _is_dev_token(token):
        return DEV_USER
    try:
        from auth.jwt_handler import decode_token
        payload = decode_token(token)
        return payload.get("sub", "anonymous")
    except Exception:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="auth required")
