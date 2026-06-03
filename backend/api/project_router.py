"""
Project Context Router — per-project vault switcher.
- POST /project/clone — clone repo + init vault + set active
- GET  /project/list — list all vaults (cloned repos)
- POST /project/select — switch active project
- GET  /project/active — current active project context
- DELETE /project/:slug — delete vault + workspace
- GET  /project/:slug/sessions — chat history
- GET  /project/:slug/decisions — decision log
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.project_vault import (
    VAULT_ROOT, init_vault, list_vaults, get_vault_context, update_vault_context,
    set_active_project, get_active_project, delete_vault,
    append_session, get_sessions, append_decision, get_decisions,
)
from workspace_manager import BASE_DIR, clone_workspace, list_workspaces, remove_workspace
import subprocess, re

router = APIRouter(prefix="/project", tags=["project"])

class CloneBody(BaseModel):
    url: str
    alias: str = ""

class SelectBody(BaseModel):
    slug: str

class ChatBody(BaseModel):
    role: str
    content: str
    mode: str = ""

# ─── CLONE + INIT VAULT ──────────────────────────────
@router.post("/clone")
def project_clone(body: CloneBody):
    url = body.url.strip()
    if not re.match(r"^https://github\.com/[^\s]+", url):
        raise HTTPException(400, "Only https://github.com/ URLs")
    name = body.alias.strip() or url.rsplit("/", 1)[-1].replace(".git", "")
    slug = re.sub(r"[^a-z0-9_-]", "-", name.lower()).strip("-")[:64]
    try:
        result = clone_workspace(url, name)
    except Exception as e:
        raise HTTPException(500, str(e))
    repo_path = str(BASE_DIR / name)
    ctx = init_vault(slug, name=name, repo_url=url, repo_path=repo_path)
    set_active_project(slug)
    return {"slug": slug, "name": name, "repo_url": url, "repo_path": repo_path, "status": ctx["status"], "message": f"Cloned + vault initialized. Active project: {name}"}

# ─── LIST ALL PROJECTS ──────────────────────────────
@router.get("/list")
def project_list():
    # Auto-init vaults for existing workspaces
    from workspace_manager import list_workspaces as _list_ws
    try:
        for ws in _list_ws():
            slug = re.sub(r"[^a-z0-9_-]", "-", ws["name"].lower()).strip("-")[:64]
            vd = VAULT_ROOT / slug
            if not (vd / "context.json").exists():
                init_vault(slug, name=ws["name"], repo_url=ws.get("origin", ""), repo_path=ws["path"])
    except:
        pass
    return {"projects": list_vaults(), "active": get_active_project()}

# ─── SELECT ACTIVE ─────────────────────────────────
@router.post("/select")
def project_select(body: SelectBody):
    slug = body.slug.strip()
    try:
        ctx = set_active_project(slug)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"active": ctx, "message": f"Switched to project: {ctx.get('name', slug)}"}

# ─── GET ACTIVE ────────────────────────────────────
@router.get("/active")
def project_active():
    ap = get_active_project()
    if not ap:
        return {"active": None, "message": "No active project"}
    return {"active": ap}

# ─── DELETE PROJECT ────────────────────────────────
@router.delete("/{slug}")
def project_delete(slug: str):
    ctx = get_vault_context(slug)
    if not ctx:
        raise HTTPException(404, "Project not found")
    name = ctx.get("name", slug)
    repo_path = ctx.get("repo_path", "")
    # remove workspace
    if repo_path and (BASE_DIR / name).exists():
        try:
            remove_workspace(name)
        except:
            pass
    delete_vault(slug)
    # clear active if this was active
    from api.project_vault import VAULT_ROOT
    ap_file = VAULT_ROOT / ".active"
    if ap_file.exists() and ap_file.read_text().strip() == slug:
        ap_file.unlink(missing_ok=True)
    return {"deleted": slug, "name": name}

# ─── GET PROJECT CONTEXT ───────────────────────────
@router.get("/{slug}/context")
def project_context(slug: str):
    ctx = get_vault_context(slug)
    if not ctx:
        raise HTTPException(404, "Project not found")
    return ctx

# ─── UPDATE PROJECT CONTEXT ────────────────────────
@router.patch("/{slug}/context")
def project_context_update(slug: str, body: dict):
    ctx = get_vault_context(slug)
    if not ctx:
        raise HTTPException(404, "Project not found")
    # only allow certain keys
    allowed = {"mode", "active_agents", "settings", "status", "name"}
    patch = {k: v for k, v in body.items() if k in allowed}
    updated = update_vault_context(slug, patch)
    return updated

# ─── SESSIONS ──────────────────────────────────────
@router.post("/{slug}/session")
def project_session_append(slug: str, body: ChatBody):
    ctx = get_vault_context(slug)
    if not ctx:
        raise HTTPException(404, "Project not found")
    entry = append_session(slug, body.role, body.content, body.mode)
    return entry

@router.get("/{slug}/sessions")
def project_sessions(slug: str, limit: int = 50):
    return {"sessions": get_sessions(slug, limit)}

# ─── DECISIONS ─────────────────────────────────────
@router.post("/{slug}/decision")
def project_decision_append(slug: str, body: dict):
    ctx = get_vault_context(slug)
    if not ctx:
        raise HTTPException(404, "Project not found")
    decision = body.get("decision", "")
    agent = body.get("agent", "")
    line = append_decision(slug, decision, agent)
    return {"appended": True, "line": line}

@router.get("/{slug}/decisions")
def project_decisions(slug: str):
    return {"decisions": get_decisions(slug)}
