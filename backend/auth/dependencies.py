
"""Lightweight War Room auth helpers.

Batch A rules:
- normal REST auth uses Authorization: Bearer or the HttpOnly session cookie;
- URL query-token auth is disabled unless explicitly enabled for compatibility;
- WebSocket auth uses the session cookie because browser WebSockets cannot set
  arbitrary Authorization headers.
"""
import os
import secrets
from fastapi import Request, HTTPException, WebSocketException, status
from typing import Optional

SESSION_COOKIE_NAME = "jarvis-dashboard-token"


def _dev_token() -> str:
    return os.environ.get("JARVIS_DASHBOARD_DEV_TOKEN", "")


def _dev_user() -> str:
    return os.environ.get("JARVIS_DASHBOARD_DEV_USER", "saiyudh")


def _query_token_fallback() -> bool:
    return os.environ.get("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "0").lower() in {"1", "true", "yes", "on"}


def _is_dev_token(token: Optional[str]) -> bool:
    dev_token = _dev_token()
    return bool(token and dev_token and secrets.compare_digest(token, dev_token))


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _decode_subject(token: Optional[str]) -> Optional[str]:
    if _is_dev_token(token):
        return _dev_user()
    if not token:
        return None
    try:
        from auth.jwt_handler import decode_token
        payload = decode_token(token)
        return payload.get("sub", "anonymous")
    except Exception:
        return None


def get_current_user(request: Request) -> str:
    """Return authenticated user or raise 401.

    Query token fallback is intentionally off by default so tokens do not leak
    through browser history, reverse-proxy logs, or access logs.
    """
    candidates = [
        _bearer_token(request.headers.get("Authorization")),
        request.cookies.get(SESSION_COOKIE_NAME),
    ]
    if _query_token_fallback():
        candidates.append(request.query_params.get("token"))

    for token in candidates:
        subject = _decode_subject(token)
        if subject:
            return subject
    raise HTTPException(status_code=401, detail="Authentication required")


def get_current_user_cookie_only(request: Request) -> str:
    """Return authenticated user from the HttpOnly dashboard cookie only.

    SSE/EventSource cannot set Authorization headers. It must not accept URL
    tokens, even when the legacy query fallback is enabled for other surfaces.
    """
    subject = _decode_subject(request.cookies.get(SESSION_COOKIE_NAME))
    if subject:
        return subject
    raise HTTPException(status_code=401, detail="Authentication required")


def get_current_user_ws(
    *,
    cookie_token: Optional[str] = None,
    authorization: Optional[str] = None,
    query_token: Optional[str] = None,
) -> str:
    candidates = [
        _bearer_token(authorization),
        cookie_token,
    ]
    if _query_token_fallback():
        candidates.append(query_token)

    for token in candidates:
        subject = _decode_subject(token)
        if subject:
            return subject
    raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="auth required")
