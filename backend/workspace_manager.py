"""
Workspace Manager — isolated repo directories for agent work.

D-2026-06-08-w (project directory fix):
  - BASE_DIR was hard-coded to Path.home() / "projects" which on
    Windows resolves to C:\\Users\\<user>\\projects\\ — not where
    saiyudh keeps his other work. The rest of the War Room lives
    under C:\\Users\\saiyu\\Desktop\\projects\\KI_projects\\, so we
    default to that layout and honor a HERMES_PROJECTS_DIR env var
    for explicit overrides.
  - `du -sm` (Unix-only) replaced with a cross-platform directory size
    walker using Path.stat().st_size
  - `rm -rf` (Unix-only) replaced with shutil.rmtree
  - GitHub URL validation tightened (reject http, ssh, gitlab, etc.)
  - Path-traversal protection preserved

All agent file ops are constrained to <BASE_DIR>/<repo-name>.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────
# Base directory resolution
# ─────────────────────────────────────────────

# Preferred default on this machine: the same parent as the other
# War Room / KI_projects repos. This matches where saiyudh already
# has hermes_jarvis_war_room, research_loop, etc.
_WINDOWS_DEFAULT = Path.home() / "Desktop" / "projects" / "KI_projects" / "hermes_projects"
_UNIX_DEFAULT = Path.home() / "projects"


def _default_base_dir() -> Path:
    """Pick the best default based on the platform."""
    if os.name == "nt":
        return _WINDOWS_DEFAULT
    return _UNIX_DEFAULT


def get_base_dir() -> Path:
    """Return the base directory for cloned workspaces.

    Order of precedence:
      1. HERMES_PROJECTS_DIR environment variable (always wins)
      2. Platform-specific default
    """
    env_val = os.environ.get("HERMES_PROJECTS_DIR", "").strip()
    if env_val:
        return Path(env_val)
    return _default_base_dir()


# Exposed for tests / introspection
BASE_DIR = get_base_dir()


def _validate_name(name: str) -> str:
    """Sanitize workspace name. Only alphanumerics, hyphens, underscores."""
    if not name:
        raise ValueError("Invalid workspace name: empty")
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    if not clean:
        raise ValueError(f"Invalid workspace name: {name!r}")
    if len(clean) > 64:
        raise ValueError(f"Workspace name too long: {name!r}")
    if clean != name:
        raise ValueError(
            f"Workspace name {name!r} contains invalid characters; "
            f"use only letters, digits, '-', '_'"
        )
    return clean


def _resolve_path(ws_name: str, rel_path: str = "") -> Path:
    """Resolve a path within workspace, rejecting escapes."""
    base = BASE_DIR / _validate_name(ws_name)
    if not base.exists():
        raise FileNotFoundError(f"Workspace not found: {ws_name}")
    target = (base / rel_path.lstrip("/")).resolve()
    # Security: realpath must be under base
    try:
        target.relative_to(base.resolve())
    except ValueError:
        raise PermissionError(f"Path traversal blocked: {rel_path}")
    return target


def _dir_size_mb(path: Path) -> float:
    """Cross-platform recursive directory size in MB.

    Replaces `du -sm <path>` (Unix-only) with a Python equivalent.
    Fast enough for repos up to ~10 GB on SSD.
    """
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file() and not f.is_symlink():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        return 0.0
    return round(total / (1024 * 1024), 1)


def list_workspaces() -> list[dict]:
    """Return all cloned workspaces with metadata."""
    if not BASE_DIR.exists():
        return []
    out = []
    for d in sorted(BASE_DIR.iterdir()):
        if not d.is_dir():
            continue
        git_dir = d / ".git"
        meta = {
            "name": d.name,
            "path": str(d),
            "has_git": git_dir.exists(),
            "size_mb": 0,
        }
        # Git remote
        try:
            r = subprocess.run(
                ["git", "-C", str(d), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5,
            )
            meta["origin"] = r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            meta["origin"] = None
        # Size (cross-platform)
        meta["size_mb"] = _dir_size_mb(d)
        # Branch
        try:
            r = subprocess.run(
                ["git", "-C", str(d), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            meta["branch"] = r.stdout.strip() if r.returncode == 0 else "unknown"
        except Exception:
            meta["branch"] = "unknown"
        out.append(meta)
    return out


def clone_workspace(repo_url: str, name: Optional[str] = None) -> dict:
    """Clone a GitHub repo into <BASE_DIR>/<name>.

    Raises:
        ValueError: if the URL is not a github.com HTTPS URL
        FileExistsError: if a workspace with the derived name already exists
        RuntimeError: if git clone itself fails
    """
    # Strict URL validation: only github.com HTTPS, owner/repo(.git)?
    if not re.match(r"^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?$", repo_url):
        raise ValueError(
            "Only https://github.com/<owner>/<repo> URLs are supported "
            f"(got: {repo_url!r})"
        )

    # Derive name from URL if not provided
    if not name:
        name = repo_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
    name = _validate_name(name)

    target = BASE_DIR / name
    if target.exists():
        raise FileExistsError(f"Workspace already exists: {name}")

    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Clone
    env = os.environ.copy()
    ssh_key = Path.home() / ".ssh" / "id_rsa"
    if ssh_key.exists():
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i {ssh_key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
        )

    r = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(target)],
        capture_output=True, text=True, env=env, timeout=120,
    )
    if r.returncode != 0:
        # Clean up partial clone if any
        if target.exists():
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception:
                pass
        raise RuntimeError(f"Clone failed: {r.stderr.strip()}")

    return {"name": name, "path": str(target), "origin": repo_url}


def remove_workspace(name: str) -> dict:
    """Delete a workspace directory (cross-platform)."""
    target = BASE_DIR / _validate_name(name)
    if not target.exists():
        raise FileNotFoundError(f"Workspace not found: {name}")
    shutil.rmtree(target)  # cross-platform; was `rm -rf` (Unix-only)
    return {"removed": name}


def workspace_status(name: str) -> dict:
    """Git status for a workspace."""
    d = _resolve_path(name)
    r = subprocess.run(
        ["git", "-C", str(d), "status", "--short"],
        capture_output=True, text=True, timeout=10,
    )
    return {
        "name": name,
        "clean": r.returncode == 0 and not r.stdout.strip(),
        "changes": r.stdout.strip().split("\n") if r.stdout.strip() else [],
        "path": str(d),
    }
