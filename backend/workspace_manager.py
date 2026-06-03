"""
Workspace Manager — isolated repo directories for agent work.
All agent file ops constrained to ~/projects/<repo-name>.
"""
import os, re, subprocess, json
from pathlib import Path

BASE_DIR = Path.home() / "projects"

def _validate_name(name: str) -> str:
    """Sanitize workspace name. Only alphanumerics, hyphens, underscores."""
    clean = re.sub(r'[^a-zA-Z0-9_-]', '', name)
    if not clean or len(clean) > 64:
        raise ValueError(f"Invalid workspace name: {name}")
    return clean

def _resolve_path(ws_name: str, rel_path: str = "") -> Path:
    """Resolve a path within workspace, rejecting escapes."""
    base = BASE_DIR / _validate_name(ws_name)
    if not base.exists():
        raise FileNotFoundError(f"Workspace not found: {ws_name}")
    target = (base / rel_path.lstrip('/')).resolve()
    # Security: realpath must be under base
    try:
        target.relative_to(base.resolve())
    except ValueError:
        raise PermissionError(f"Path traversal blocked: {rel_path}")
    return target

def list_workspaces() -> list[dict]:
    """Return all cloned workspaces with metadata."""
    if not BASE_DIR.exists():
        return []
    out = []
    for d in sorted(BASE_DIR.iterdir()):
        if not d.is_dir():
            continue
        git_dir = d / ".git"
        meta = {"name": d.name, "path": str(d), "has_git": git_dir.exists(), "size_mb": 0}
        # Git remote
        try:
            r = subprocess.run(
                ["git", "-C", str(d), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5
            )
            meta["origin"] = r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            meta["origin"] = None
        # Size
        try:
            r = subprocess.run(
                ["du", "-sm", str(d)],
                capture_output=True, text=True, timeout=5
            )
            meta["size_mb"] = int(r.stdout.split()[0]) if r.returncode == 0 else 0
        except Exception:
            pass
        # Branch
        try:
            r = subprocess.run(
                ["git", "-C", str(d), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            meta["branch"] = r.stdout.strip() if r.returncode == 0 else "unknown"
        except Exception:
            meta["branch"] = "unknown"
        out.append(meta)
    return out

def clone_workspace(repo_url: str, name: str | None = None) -> dict:
    """Clone a GitHub repo into ~/projects/<name>."""
    # Validate URL
    if not re.match(r'^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?$', repo_url):
        raise ValueError("Only github.com HTTPS URLs are supported")
    
    # Derive name from URL if not provided
    if not name:
        name = repo_url.split('/')[-1].replace('.git', '')
    name = _validate_name(name)
    
    target = BASE_DIR / name
    if target.exists():
        raise FileExistsError(f"Workspace already exists: {name}")
    
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clone
    env = os.environ.copy()
    ssh_key = Path.home() / ".ssh" / "id_rsa"
    if ssh_key.exists():
        env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    
    r = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(target)],
        capture_output=True, text=True, env=env, timeout=120
    )
    if r.returncode != 0:
        raise RuntimeError(f"Clone failed: {r.stderr}")
    
    return {"name": name, "path": str(target), "origin": repo_url}

def remove_workspace(name: str) -> dict:
    """Delete a workspace directory."""
    target = BASE_DIR / _validate_name(name)
    if not target.exists():
        raise FileNotFoundError(f"Workspace not found: {name}")
    subprocess.run(["rm", "-rf", str(target)], check=True)
    return {"removed": name}

def workspace_status(name: str) -> dict:
    """Git status for a workspace."""
    d = _resolve_path(name)
    r = subprocess.run(
        ["git", "-C", str(d), "status", "--short"],
        capture_output=True, text=True, timeout=10
    )
    return {
        "name": name,
        "clean": r.returncode == 0 and not r.stdout.strip(),
        "changes": r.stdout.strip().split('\n') if r.stdout.strip() else [],
        "path": str(d)
    }
