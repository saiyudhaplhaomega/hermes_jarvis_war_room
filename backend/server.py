"""FastAPI entry point — Jarvis War Room Dashboard Plugin v1.1.0."""
import sys, asyncio, threading, json, logging
from pathlib import Path

log = logging.getLogger("jarvis-dashboard")

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, APIRouter, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import API_HOST, API_PORT, AGGREGATE_INTERVAL
from core.data_aggregator import DataAggregator
from core.websocket import manager

# Routers
from api.cache import router as cache_router
from api.kanban import router as kanban_router
from api.nl_router import router as nl_router
from api.sessions import router as sessions_router
from api.audit import router as audit_router
from api.discord_bridge import router as discord_router
from api.workspace import router as workspace_router
from api.mode_router import router as mode_router
from api.project_router import router as project_router
from api.roles import router as roles_router
from api.agent_growth import router as agent_growth_router
from api.army import router as army_router
from jarvis_company_os.router import router as jarvis_company_os_router
from jarvis_company_os.migrations import apply_pending
from jarvis_company_os.registry import seed_default_company
from jarvis_company_os import gen_agent_files as gen_files_mod

aggregator = DataAggregator()


def _aggregator_loop():
    while True:
        try:
            aggregator.run()
        except Exception as e:
            import traceback
            traceback.print_exc()
        import time
        time.sleep(AGGREGATE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1 spine: apply pending migrations + seed default company
    # Boss D-A (apply at startup), Boss D-C (idempotent seed).
    try:
        applied = apply_pending()
        if applied:
            log.info("jarvis_company_os lifespan: migrations=%s", applied)
    except Exception as e:
        log.exception("jarvis_company_os migration apply failed: %s", e)
    try:
        seed_result = seed_default_company()
        log.info("jarvis_company_os lifespan: seed=%s", seed_result.get("status"))
    except Exception as e:
        log.exception("jarvis_company_os seed failed: %s", e)
    # Phase 3: generate 4 files (idempotent — only writes if missing or changed)
    try:
        gen_result = gen_files_mod.generate_all()
        log.info("jarvis_company_os lifespan: agent_files=%s",
                 f"{gen_result.get('files_written', 0)} files for "
                 f"{gen_result.get('agents', 0)} agents")
    except Exception as e:
        log.exception("jarvis_company_os gen_agent_files failed: %s", e)
    t = threading.Thread(target=_aggregator_loop, daemon=True)
    t.start()
    yield


app = FastAPI(
    title="Jarvis War Room Dashboard",
    version="1.1.0",
    docs_url="/api/plugins/jarvis-dashboard/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# ─── CORS ───────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8503","http://127.0.0.1:8513","http://43.131.26.109:8503","http://localhost:8503","http://localhost:8513"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Rate Limit Middleware ────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from collections import defaultdict
import time as time_mod

rate_window = defaultdict(list)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "0.0.0.0"
        now = time_mod.time()
        rate_window[client] = [ts for ts in rate_window[client] if now - ts < 60]
        if len(rate_window[client]) > 120:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        rate_window[client].append(now)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# ─── WebSocket endpoint ─────────────────────────────
@app.websocket("/api/plugins/jarvis-dashboard/v1/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await manager.send(websocket, {"error": "Invalid JSON"})
                continue
            if msg.get("subscribe") is not None:
                manager.subscribe(websocket, msg.get("subscribe", []))
                await manager.send(websocket, {"type": "subscribed", "channels": list(manager.subscriptions.get(websocket, []))})
            elif msg.get("request") == "snapshot":
                from core.websocket import LIVE_CACHE
                await manager.send(websocket, {"type": "snapshot", "payload": dict(LIVE_CACHE)})
            else:
                await manager.send(websocket, {"type": "pong"})
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)

# ─── Plugin router ──────────────────────────────────
plugin = APIRouter(prefix="/api/plugins/jarvis-dashboard/v1")
plugin.include_router(cache_router, prefix="/dashboard")
plugin.include_router(kanban_router)
plugin.include_router(nl_router)
plugin.include_router(sessions_router)
plugin.include_router(audit_router)
plugin.include_router(discord_router)
plugin.include_router(workspace_router)
plugin.include_router(mode_router)
plugin.include_router(project_router)
plugin.include_router(roles_router)
plugin.include_router(agent_growth_router)
plugin.include_router(army_router)
plugin.include_router(jarvis_company_os_router)  # JARVIS-SPEC-PACKAGE-INTEGRATION Phase 1
app.include_router(plugin)

# Health
@app.get("/api/plugins/jarvis-dashboard/health")
def health():
    return {"status": "ok", "plugin": "jarvis-dashboard", "version": "1.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
