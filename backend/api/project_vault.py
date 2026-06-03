"""
Project Vault — per-project isolated memory on the Hermes host.
Canonical location: ~/.hermes/memory/projects/<slug>/
Structure:
  context.json   — active mode, agent selections, settings, last_updated
  sessions/      — chat history per project
  decisions.md   — decision log (append-only)
  plans/         — .hermes/plans/ equivalent
  agents/        — per-project agent overrides
  skills/        — project-specific skills
  memory.jsonl   — auto-extracted facts from sessions
"""
import json, os, re, time
from datetime import datetime
from pathlib import Path
from typing import Optional

VAULT_ROOT = Path.home() / ".hermes" / "memory" / "projects"
VAULT_ROOT.mkdir(parents=True, exist_ok=True)

def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "-", name.lower()).strip("-")[:64]

def get_vault_dir(slug: str) -> Path:
    p = (VAULT_ROOT / slug).resolve()
    if not str(p).startswith(str(VAULT_ROOT.resolve())):
        raise ValueError("Path traversal blocked")
    p.mkdir(parents=True, exist_ok=True)
    return p

def init_vault(slug: str, name: str = "", repo_url: str = "", repo_path: str = "") -> dict:
    vd = get_vault_dir(slug)
    (vd / "sessions").mkdir(exist_ok=True)
    (vd / "plans").mkdir(exist_ok=True)
    (vd / "agents").mkdir(exist_ok=True)
    (vd / "skills").mkdir(exist_ok=True)
    ctx_path = vd / "context.json"
    if not ctx_path.exists():
        ctx = {
            "slug": slug,
            "name": name or slug,
            "repo_url": repo_url,
            "repo_path": repo_path,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_active_at": datetime.utcnow().isoformat() + "Z",
            "mode": "standard",
            "active_agents": [],
            "settings": {"auto_exec_tier": 0, "voice_enabled": False, "cost_budget": 50.0},
            "status": "active",
            "version": 1,
        }
        ctx_path.write_text(json.dumps(ctx, indent=2))
    if not (vd / "decisions.md").exists():
        (vd / "decisions.md").write_text(f"# {name or slug} — Decision Log\n\n")
    return get_vault_context(slug)

def get_vault_context(slug: str) -> dict:
    vd = get_vault_dir(slug)
    p = vd / "context.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}

def update_vault_context(slug: str, patch: dict) -> dict:
    vd = get_vault_dir(slug)
    p = vd / "context.json"
    ctx = json.loads(p.read_text()) if p.exists() else {}
    ctx.update(patch)
    ctx["last_active_at"] = datetime.utcnow().isoformat() + "Z"
    p.write_text(json.dumps(ctx, indent=2))
    return ctx

def list_vaults() -> list:
    out = []
    for d in sorted(VAULT_ROOT.iterdir()):
        if d.is_dir() and (d / "context.json").exists():
            c = json.loads((d / "context.json").read_text())
            out.append({
                "slug": c.get("slug", d.name),
                "name": c.get("name", d.name),
                "status": c.get("status", "active"),
                "mode": c.get("mode", "standard"),
                "repo_url": c.get("repo_url", ""),
                "repo_path": c.get("repo_path", ""),
                "last_active_at": c.get("last_active_at", ""),
                "created_at": c.get("created_at", ""),
            })
    return out

def delete_vault(slug: str) -> bool:
    vd = get_vault_dir(slug)
    import shutil
    shutil.rmtree(vd)
    return True

def append_session(slug: str, role: str, content: str, mode: str = "", metadata: dict = None) -> dict:
    vd = get_vault_dir(slug)
    sess_dir = vd / "sessions"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    fpath = sess_dir / f"{today}.jsonl"
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "role": role,
        "content": content,
        "mode": mode,
        "metadata": metadata or {},
    }
    with open(fpath, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

def get_sessions(slug: str, limit: int = 50) -> list:
    vd = get_vault_dir(slug)
    sess_dir = vd / "sessions"
    if not sess_dir.exists():
        return []
    entries = []
    for f in sorted(sess_dir.iterdir(), reverse=True):
        if f.suffix == ".jsonl":
            for line in reversed(f.read_text().strip().split("\n")):
                if line.strip():
                    entries.append(json.loads(line))
                if len(entries) >= limit:
                    break
        if len(entries) >= limit:
            break
    return list(reversed(entries))

def append_decision(slug: str, decision: str, agent: str = "") -> str:
    vd = get_vault_dir(slug)
    p = vd / "decisions.md"
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    line = f"\n## [{ts}] {agent or 'system'}\n\n{decision}\n"
    with open(p, "a") as f:
        f.write(line)
    return line

def get_decisions(slug: str) -> str:
    vd = get_vault_dir(slug)
    p = vd / "decisions.md"
    return p.read_text() if p.exists() else ""

def get_active_project() -> Optional[dict]:
    ap_file = VAULT_ROOT / ".active"
    if ap_file.exists():
        slug = ap_file.read_text().strip()
        if slug:
            ctx = get_vault_context(slug)
            if ctx:
                return ctx
    return None

def set_active_project(slug: str) -> dict:
    ap_file = VAULT_ROOT / ".active"
    ctx = get_vault_context(slug)
    if not ctx:
        raise ValueError(f"Vault {slug} not found")
    ap_file.write_text(slug)
    update_vault_context(slug, {"last_active_at": datetime.utcnow().isoformat() + "Z"})
    return ctx
