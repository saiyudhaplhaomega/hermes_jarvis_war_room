"""FastAPI entry point — Jarvis War Room Dashboard Plugin v1.1.0."""
import sys, asyncio, threading, json, logging, os, uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("jarvis-dashboard")

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, APIRouter, WebSocket, Depends, Response, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import API_HOST, API_PORT, AGGREGATE_INTERVAL, DASHBOARD_DATA
from core.data_aggregator import DataAggregator
from core.websocket import manager
from core.operating_ledger import OperatingLedger
from core.kpi_dashboard import KPIDashboard
from core.handoff_queue import HandoffQueue
from core.permissions_matrix import PermissionsMatrix
from core.agent_os_primitives import AgentOS, Capability, Namespace
from core.human_gates import HumanGateRegistry, HumanGateState
from core.fact_store import FactStore
from core.policy_attestor import PolicyAttestor
from observability.audit_log import AuditLog

# Routers
from api.cache import router as cache_router
from api.kanban import router as kanban_router
from api.nl_router import router as nl_router
from api.sessions import router as sessions_router
from api.audit import router as audit_router
from api.discord_bridge import router as discord_router
from api.discord_gateway import router as discord_gateway_router, STATE_FILE as DISCORD_GATEWAY_STATE_FILE  # D-2026-06-09 (Phase 3)
from api.council import router as council_router, STATE_FILE as COUNCIL_STATE_FILE  # D-2026-06-09 (Phase 4)
from api.workspace import router as workspace_router
from api.mode_router import router as mode_router
from api.project_router import router as project_router
from api.roles import router as roles_router, ROLE_FILE
from api.agent_growth import (
    router as agent_growth_router,
    ASSIGNMENTS_FILE,
    CATALOG_FILE,
    PROPOSALS_FILE,
    REMOVED_AGENTS_FILE,
)
from api.agent_cron import router as agent_cron_router, JOBS_FILE as AGENT_CRON_JOBS_FILE
from api.mcp_catalog import router as mcp_catalog_router, CATALOG_FILE as MCP_CATALOG_FILE
from api.army import router as army_router
from jarvis_company_os.router import router as jarvis_company_os_router
from jarvis_company_os.migrations import apply_pending
from jarvis_company_os.registry import seed_default_company
from jarvis_company_os import gen_agent_files as gen_files_mod
from auth.dependencies import SESSION_COOKIE_NAME, get_current_user, get_current_user_cookie_only

aggregator = DataAggregator()
ledger = OperatingLedger()
dashboard = KPIDashboard(ledger)
queue = HandoffQueue(ledger)
permissions_matrix = PermissionsMatrix()
agent_os = AgentOS()
human_gates = HumanGateRegistry()
fact_store = FactStore()
policy_attestor = PolicyAttestor(
    permissions=permissions_matrix,
    agent_os=agent_os,
    gates=human_gates,
)


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
    allow_origins=["http://127.0.0.1:8503", "http://127.0.0.1:8513", "http://localhost:8503", "http://localhost:8513", "https://courage-bigger-monthly-corn.trycloudflare.com"],
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
    connected = await manager.connect(websocket)
    if not connected:
        return
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


@plugin.post("/auth/session")
def create_auth_session(response: Response, user: str = Depends(get_current_user)):
    """Bootstrap browser WebSocket auth with an HttpOnly cookie.

    The response intentionally returns only the user identity, never the token.
    """
    response.set_cookie(
        SESSION_COOKIE_NAME,
        os.environ.get("JARVIS_DASHBOARD_DEV_TOKEN", ""),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/api/plugins/jarvis-dashboard/v1",
    )
    return {"status": "ok", "user": user}


@plugin.post("/sse-session", status_code=204)
def create_sse_session(_response: Response, _user: str = Depends(get_current_user)):
    """Bootstrap browser EventSource auth with an HttpOnly cookie.

    EventSource cannot send Authorization headers. This endpoint intentionally
    returns no body and never echoes the token.
    """
    response = Response(status_code=204)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        os.environ.get("JARVIS_DASHBOARD_DEV_TOKEN", ""),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/api/plugins/jarvis-dashboard/v1",
    )
    return response


def _redacted_query_denial_log(request: Request, reason: str) -> None:
    log.warning(
        "%s path=%s client=%s query_keys=%s",
        reason,
        request.url.path,
        request.client.host if request.client else "unknown",
        sorted(request.query_params.keys()),
    )


@plugin.get("/events")
def events(request: Request):
    """Cookie-only SSE endpoint for War Room browser event plumbing."""
    if "token" in request.query_params:
        _redacted_query_denial_log(request, "sse_token_url_rejected")
        raise HTTPException(status_code=401, detail="Authentication required")
    get_current_user_cookie_only(request)

    def stream():
        yield 'event: ready\ndata: {"status":"ok"}\n\n'

    return StreamingResponse(stream(), media_type="text/event-stream")


@plugin.get("/ledger/{entity_type}/{entity_id}")
def get_ledger_entity(entity_type: str, entity_id: str, _user: str = Depends(get_current_user)):
    """r52: Query a single entity from the operating ledger."""
    data = ledger.query(entity_type, entity_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"entity '{entity_type}/{entity_id}' not found")
    return {"entity_type": entity_type, "entity_id": entity_id, "data": data}


@plugin.get("/kpi/dashboard")
def get_kpi_dashboard(_user: str = Depends(get_current_user)):
    """r53: 7 company KPIs."""
    return dashboard.get_kpis()


@plugin.post("/handoff")
def create_handoff(ticket_id: str, from_dept: str, to_dept: str, artifacts: list = [], _user: str = Depends(get_current_user)):
    """r54: Create a handoff between departments."""
    success = queue.create_handoff(ticket_id, from_dept, to_dept, artifacts)
    if not success:
        raise HTTPException(status_code=500, detail="failed to create handoff")
    return {"status": "ok", "ticket_id": ticket_id}


@plugin.post("/permissions/check")
def check_permission(dept: str, action: str, _user: str = Depends(get_current_user)):
    """r55: Check permission for a dept/action."""
    level = permissions_matrix.check_permission(dept, action)
    return {"dept": dept, "action": action, "permission": level.name}


@plugin.get("/ready")
def ready(_user: str = Depends(get_current_user)):
    state_paths = _check_json_state_paths()
    status = "ready" if all(item["writable"] for item in state_paths.values()) else "degraded"
    return {
        "status": status,
        "plugin": "jarvis-dashboard",
        "version": "1.1.0",
        "state_paths": state_paths,
    }


@plugin.post("/agent-os/capability")
def grant_capability(
    namespace: str,
    agent_id: str,
    capability: str,
    _user: str = Depends(get_current_user),
):
    """Grant an Agent OS capability to an agent in a namespace."""
    try:
        cap = Capability[capability.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="unknown capability")
    ok = agent_os.grant_capability(namespace, agent_id, cap)
    return {"ok": ok}


@plugin.get("/agent-os/capability")
def check_capability(namespace: str, agent_id: str, capability: str, _user: str = Depends(get_current_user)):
    try:
        cap = Capability[capability.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="unknown capability")
    return {"has": agent_os.has_capability(namespace, agent_id, cap)}


@plugin.post("/agent-os/namespace")
def create_namespace(name: str, department: str = "*", project: str = "*", _user: str = Depends(get_current_user)):
    ok = agent_os.create_namespace(name, department, project)
    return {"ok": ok}


@plugin.post("/human-gate")
def request_human_gate(
    dept: str,
    agent_id: str,
    action: str,
    justification: str = "",
    _user: str = Depends(get_current_user),
):
    gate = human_gates.request(dept, agent_id, action, justification)
    return {"id": gate.id, "state": gate.state.value}


@plugin.post("/human-gate/{gate_id}/approve")
def approve_human_gate(gate_id: str, human_id: str, reason: str = "", _user: str = Depends(get_current_user)):
    gate = human_gates.approve(gate_id, human_id, reason)
    return {"id": gate.id, "state": gate.state.value}


@plugin.get("/human-gate/pending")
def list_pending_gates(dept: Optional[str] = None, _user: str = Depends(get_current_user)):
    gates = human_gates.list_pending(dept)
    return [{"id": g.id, "dept": g.dept, "action": g.action, "state": g.state.value} for g in gates]


@plugin.post("/facts")
def add_fact(
    subject: str,
    predicate: str,
    obj: str,
    source: str,
    namespace: str = "default",
    initial_trust: float = 0.5,
    _user: str = Depends(get_current_user),
):
    fact = fact_store.add_fact(subject, predicate, obj, source, namespace, initial_trust)
    return {
        "id": fact.id,
        "subject": fact.subject,
        "predicate": fact.predicate,
        "object": fact.object,
        "trust_score": fact.trust_score,
    }


@plugin.get("/facts")
def list_facts(subject: Optional[str] = None, predicate: Optional[str] = None, namespace: Optional[str] = None, _user: str = Depends(get_current_user)):
    facts = fact_store.find_fact(subject, predicate, namespace)
    return [{"id": f.id, "subject": f.subject, "predicate": f.predicate, "object": f.object, "trust_score": f.trust_score} for f in facts]


@plugin.get("/facts/search")
def search_facts(q: str, namespace: Optional[str] = None, min_trust: float = 0.0, _user: str = Depends(get_current_user)):
    facts = fact_store.search_facts(q, namespace, min_trust)
    return [{"id": f.id, "subject": f.subject, "predicate": f.predicate, "object": f.object, "trust_score": f.trust_score} for f in facts]


@plugin.post("/policy/attest")
def policy_attest(
    agent_id: str,
    action: str,
    namespace: str,
    purpose: str = "",
    delegator: str = "self",
    _user: str = Depends(get_current_user),
):
    allowed, reason, att = policy_attestor.can_execute(agent_id, action, namespace, purpose, delegator)
    if not allowed or att is None:
        raise HTTPException(status_code=403, detail=reason)
    return {
        "allowed": allowed,
        "action_id": att.action_id,
        "taint_level": att.taint_level,
        "approval_id": att.approval_id,
        "input_hash": att.input_hash,
        "signature": att.signature,
    }


def _check_json_state_paths() -> dict:
    paths = {
        "gateway": DISCORD_GATEWAY_STATE_FILE,
        "council": COUNCIL_STATE_FILE,
        "agent_growth_assignments": ASSIGNMENTS_FILE,
        "catalog": CATALOG_FILE,
        "proposals": PROPOSALS_FILE,
        "removed_agents": REMOVED_AGENTS_FILE,
        "role_mappings": ROLE_FILE,
        "agent_cron_jobs": AGENT_CRON_JOBS_FILE,
        "mcp_catalog": MCP_CATALOG_FILE,
        "ledger": Path("kanban.db"),  # r52
    }
    return {name: _probe_json_state_path(name, path) for name, path in paths.items()}


def _probe_json_state_path(name: str, path: Path) -> dict:
    probe = path.parent / f".{path.name}.ready-probe-{uuid.uuid4().hex}.json"
    payload = {"probe": "ready", "state_path": name}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text(json.dumps(payload, sort_keys=True))
        observed = json.loads(probe.read_text())
        if observed != payload:
            raise ValueError("probe_mismatch")
        return {"writable": True}
    except Exception as exc:
        log.warning("ready_state_path_probe_failed name=%s error_type=%s", name, exc.__class__.__name__)
        return {"writable": False, "error": exc.__class__.__name__}
    finally:
        try:
            if probe.exists():
                probe.unlink()
        except Exception:
            log.warning("ready_state_path_probe_cleanup_failed name=%s", name)

plugin.include_router(cache_router, prefix="/dashboard")
plugin.include_router(kanban_router)
plugin.include_router(nl_router)
plugin.include_router(sessions_router)
plugin.include_router(audit_router)
plugin.include_router(discord_router)
plugin.include_router(discord_gateway_router)  # D-2026-06-09 (Phase 3)
plugin.include_router(council_router)  # D-2026-06-09 (Phase 4)
plugin.include_router(workspace_router)
plugin.include_router(mode_router)
plugin.include_router(project_router)
plugin.include_router(roles_router)
plugin.include_router(agent_growth_router)
plugin.include_router(agent_cron_router)  # D-2026-06-14 (Agent Cron Jobs)
plugin.include_router(mcp_catalog_router)  # D-2026-06-15 (MCP Catalog + chat install)
plugin.include_router(army_router)
plugin.include_router(jarvis_company_os_router)  # JARVIS-SPEC-PACKAGE-INTEGRATION Phase 1
app.include_router(plugin)

# Health
@app.get("/api/plugins/jarvis-dashboard/health")
def health():
    return {"status": "ok", "plugin": "jarvis-dashboard", "version": "1.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info", access_log=False)
