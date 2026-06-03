"""Discord webhook receiver.
Accepts webhooks from Discord and stores them in a memory cache.
"""
import json, hmac, hashlib, os
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from typing import Any, Dict
from auth.dependencies import get_current_user

router = APIRouter(prefix="/discord")

# In-memory thread store (pushed to frontend via WS)
_threads_cache: list[dict] = []

DISCORD_WEBHOOK_SECRET = os.environ.get("JARVIS_DISCORD_WEBHOOK_SECRET", "")

@router.post("/webhook")
async def discord_webhook(request: Request, x_signature: str = Header(None, alias="X-Signature")):
    """Receive Discord webhook JSON with HMAC signature verification."""
    body = await request.body()
    if x_signature:
        if not DISCORD_WEBHOOK_SECRET:
            raise HTTPException(status_code=503, detail="Webhook secret not configured")
        expected = hmac.new(DISCORD_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    try:
        data = json.loads(body.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    event_type = data.get("type", "unknown")
    thread = {
        "event": event_type,
        "guild_id": str(data.get("guild_id", "")),
        "channel_id": str(data.get("channel_id", "")),
        "thread_id": str(data.get("thread_id", "")),
        "thread_name": data.get("thread_name", "Unnamed"),
        "participant_bots": data.get("participant_bots", []),
        "last_message_ts": data.get("last_message_ts"),
        "raw": data,
    }
    _threads_cache.insert(0, thread)
    if len(_threads_cache) > 500:
        _threads_cache.pop()
    return {"status": "stored", "thread_id": thread["thread_id"]}

@router.get("/threads")
def list_threads(limit: int = 50, user: str = Depends(get_current_user)):
    return {"threads": _threads_cache[:limit], "total": len(_threads_cache)}
