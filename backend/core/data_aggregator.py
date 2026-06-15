"""
Dashboard Data Aggregator.
Scans filesystem + SQLite sources into a single cache.json snapshot.
Runs every AGGREGATE_INTERVAL seconds.
"""
from __future__ import annotations
import json, os, re, sqlite3, yaml, glob, hashlib, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import *  # noqa

# Project root (one level above the backend package, set by config)
try:
    PROJECT_ROOT
except NameError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class DataAggregator:
    def __init__(self):
        self.cache = {}
        DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)

    def run(self) -> dict[str, Any]:
        self.cache = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agents": self._scan_agents(),
            "tasks": self._scan_tasks(),
            "kanban_by_project": self._scan_kanban(),
            "decisions": self._scan_decisions(),
            "memory": self._scan_memory(),
            "metrics": self._scan_metrics(),
            "gateway": self._scan_gateway(),
            "projects": self._scan_projects(),
            "sessions": self._scan_sessions(),
            "research": self._scan_research(),
            "departments": self._scan_departments(),
            "topology": self._scan_topology(),
            "human_gates": self._scan_human_gates(),
            "fact_store": self._scan_fact_store(),
        }
        self.write_cache()
        return self.cache

    # ───────────────────────────────────────────────
    def _scan_agents(self):
        agents = []
        profiles_root = PROFILE
        if not profiles_root.exists():
            return agents
        try:
            ps_out = subprocess.check_output(["ps", "-ef"], text=True, timeout=2)
        except Exception:
            ps_out = ""
        for profile_dir in sorted(profiles_root.glob("jarvis*")):
            if not profile_dir.is_dir():
                continue
            p = profile_dir / "config.yaml"
            if not p.exists():
                continue
            try:
                data = yaml.safe_load(p.read_text())
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            # D-2026-06-14: support BOTH the nested profile/model schema and
            # the flat schema that the actual profiles on disk use
            # (name: ..., model: codex, role: boss, provider: anthropic, ...).
            profile_section = data.get("profile") or {}
            if not isinstance(profile_section, dict):
                profile_section = {}
            # The flat schema has these as top-level keys
            name = (
                profile_section.get("name")
                or data.get("name")
                or profile_dir.name
            )
            role = (
                profile_section.get("role")
                or data.get("role")
                or ""
            )
            description = (
                profile_section.get("description")
                or data.get("description")
                or ""
            )
            status = data.get("status") or ""
            # model: can be either a string ("codex") or a dict
            # ({"default": "...", "provider": "..."})
            model_cfg = data.get("model")
            if isinstance(model_cfg, str):
                model_name = model_cfg
                model_provider = data.get("provider", "") or ""
            elif isinstance(model_cfg, dict):
                model_name = (
                    model_cfg.get("default")
                    or model_cfg.get("model")
                    or ""
                )
                model_provider = (
                    model_cfg.get("provider")
                    or data.get("provider")
                    or ""
                )
            else:
                model_name = ""
                model_provider = data.get("provider", "") or ""
            running = (f"--profile {name} gateway" in ps_out) or (name == "jarvis" and "hermes_cli.main gateway run" in ps_out)
            agents.append({
                "name": name,
                "tier": 3 if name in ("jarvis-boss", "jarvis-council") else 2 if name != "jarvis" else 1,
                "status": "running" if running else (status or "configured"),
                "last_seen": datetime.now(timezone.utc).isoformat() if running else None,
                "model": model_name,
                "provider": model_provider,
                "role": role,
                "description": description,
                "project": "",
                "source": str(p),
            })
        return agents

    def _scan_tasks(self):
        tasks = []
        for p in sorted((DASHBOARD_DATA / "tasks").glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(data, list):
                tasks.extend(data)
            elif isinstance(data, dict):
                tasks.append(data)
        return tasks

    def _scan_kanban(self):
        """Read kanban.db tasks grouped by project."""
        if not KANBAN_DB.exists():
            return {}
        try:
            conn = sqlite3.connect(str(KANBAN_DB), timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT t.id, t.title, t.status, t.assignee, t.priority, t.project,
                       t.last_heartbeat_at, t.body, t.created_at, t.updated_at,
                       (SELECT GROUP_CONCAT(parent_id) FROM task_deps WHERE child_id = 't_' || t.id) as parents
                FROM tasks t
                WHERE t.status NOT IN ('archived','cancelled')
                ORDER BY t.project, t.priority DESC
            """)
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["id"] = f"t_{r['id']}"
                # Resolve blocked_by_parents
                if r.get("parents"):
                    parent_ids = r["parents"].split(",")
                    placeholders = ",".join(["?"] * len(parent_ids))
                    cur.execute(f"SELECT status FROM tasks WHERE 't_' || id IN ({placeholders})", parent_ids)
                    parent_statuses = [s[0] for s in cur.fetchall()]
                    r["blocked_by_parents"] = any(s != "done" for s in parent_statuses)
                else:
                    r["blocked_by_parents"] = False
                # Comment count
                cur.execute("SELECT COUNT(*) FROM task_comments WHERE task_id = ?", (r["id"],))
                r["comment_count"] = cur.fetchone()[0]
                # Run count
                cur.execute("SELECT COUNT(*) FROM task_runs WHERE task_id = ?", (r["id"],))
                r["run_count"] = cur.fetchone()[0]
            conn.close()

            by_project = {}
            for r in rows:
                proj = r.get("project") or "default"
                by_project.setdefault(proj, []).append(r)
            return by_project
        except Exception:
            return {}

    def _first_heading(self, path: Path) -> str:
        try:
            for line in path.read_text(errors="ignore").splitlines()[:40]:
                line = line.strip()
                if line.startswith("#"):
                    return line.lstrip("#").strip() or path.stem
        except Exception:
            pass
        return path.stem.replace("-", " ").replace("_", " ").title()

    def _file_timestamp(self, path: Path) -> str:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        except Exception:
            return ""

    def _scan_decisions(self):
        decisions = []
        roots = [
            DASHBOARD_DATA / "decisions",
            HOME / "Obsidian" / "Vault" / "08 Decisions",
        ]
        seen = set()
        for root in roots:
            if not root.exists():
                continue
            for p in sorted(root.glob("*.md")):
                key = str(p.resolve())
                if key in seen:
                    continue
                seen.add(key)
                text = ""
                try:
                    text = p.read_text(errors="ignore")[:4000]
                except Exception:
                    pass
                project = ""
                for proj_dir in sorted((HOME / ".hermes" / "memory" / "projects").glob("*")):
                    if proj_dir.is_dir() and proj_dir.name in text:
                        project = proj_dir.name
                        break
                decisions.append({
                    "id": p.stem,
                    "title": self._first_heading(p),
                    "source": str(p),
                    "project": project,
                    "created_at": self._file_timestamp(p),
                    "tier": 0,
                })
        project_root = HOME / ".hermes" / "memory" / "projects"
        if project_root.exists():
            for proj_dir in sorted(project_root.iterdir()):
                if not proj_dir.is_dir():
                    continue
                p = proj_dir / "decisions.md"
                if not p.exists():
                    continue
                key = str(p.resolve())
                if key in seen:
                    continue
                seen.add(key)
                decisions.append({
                    "id": f"{proj_dir.name}-decisions",
                    "title": self._first_heading(p) or f"{proj_dir.name} decisions",
                    "source": str(p),
                    "project": proj_dir.name,
                    "created_at": self._file_timestamp(p),
                    "tier": 0,
                })
        return decisions

    def _scan_memory(self):
        memory = {}
        roots = [
            DASHBOARD_DATA / "memory",
            PROFILE / "jarvis" / "memories",
            HOME / "Obsidian" / "Vault" / "Memory",
            HOME / "Obsidian" / "Vault" / "00 Memory",
        ]
        project_names = []
        project_root = HOME / ".hermes" / "memory" / "projects"
        if project_root.exists():
            project_names = [p.name for p in project_root.iterdir() if p.is_dir()]
        for root in roots:
            if not root.exists():
                continue
            for p in sorted(root.glob("*.md")):
                key = p.stem
                if key in memory:
                    key = hashlib.sha1(str(p).encode()).hexdigest()[:10] + "-" + key
                text = ""
                try:
                    text = p.read_text(errors="ignore")[:4000]
                except Exception:
                    pass
                project = next((proj for proj in project_names if proj in text), "")
                memory[key] = {
                    "key": key,
                    "title": self._first_heading(p),
                    "source": str(p),
                    "project": project,
                    "kind": "profile-memory" if "memories" in p.parts else "obsidian-memory",
                    "updated_at": self._file_timestamp(p),
                }
        if project_root.exists():
            for proj_dir in sorted(project_root.iterdir()):
                if not proj_dir.is_dir():
                    continue
                for p, kind, title in [
                    (proj_dir / "context.json", "project-context", f"{proj_dir.name} context"),
                    (proj_dir / "decisions.md", "project-decisions", f"{proj_dir.name} decisions"),
                    (proj_dir / "memory.jsonl", "project-memory", f"{proj_dir.name} memory"),
                ]:
                    if not p.exists():
                        continue
                    key = f"{proj_dir.name}-{p.stem}"
                    memory[key] = {
                        "key": key,
                        "title": title if p.suffix != ".md" else self._first_heading(p),
                        "source": str(p),
                        "project": proj_dir.name,
                        "kind": kind,
                        "updated_at": self._file_timestamp(p),
                    }
                sessions = proj_dir / "sessions"
                if sessions.exists():
                    latest = sorted(sessions.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
                    for p in latest:
                        key = f"{proj_dir.name}-session-{p.stem}"
                        memory[key] = {
                            "key": key,
                            "title": f"{proj_dir.name} session {p.stem}",
                            "source": str(p),
                            "project": proj_dir.name,
                            "kind": "project-session",
                            "updated_at": self._file_timestamp(p),
                        }
        return memory

    def _scan_metrics(self):
        metrics = {}
        for p in sorted((DASHBOARD_DATA / "metrics").glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(data, dict):
                metrics.update(data)
        return metrics

    def _scan_gateway(self):
        gateway = {}
        for p in sorted((DASHBOARD_DATA / "gateway").glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(data, dict):
                gateway.update(data)
        return gateway

    def _scan_projects(self):
        projects = []
        vault_root = Path("~/.hermes/memory/projects").expanduser()
        if not vault_root.exists():
            return projects
        for p in sorted(vault_root.iterdir()):
            if p.is_dir():
                ctx_file = p / "context.json"
                if ctx_file.exists():
                    try:
                        ctx = json.loads(ctx_file.read_text())
                        projects.append({
                            "slug": p.name,
                            "name": ctx.get("name", p.name.replace("-", " ").title()),
                            "mode": ctx.get("mode", "standard"),
                            "source": str(ctx_file),
                        })
                    except Exception:
                        pass
                else:
                    # Vault dir exists but no context — still list it
                    projects.append({
                        "slug": p.name,
                        "name": p.name.replace("-", " ").title(),
                        "source": str(p),
                    })
        return projects

    def _scan_sessions(self):
        sessions = []
        sessions_dir = DASHBOARD_DATA / "sessions"
        if not sessions_dir.exists():
            return sessions
        for p in sorted(sessions_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(data, dict):
                sessions.append(data)
            elif isinstance(data, list):
                sessions.extend(data)
        return sessions

    def write_cache(self):
        try:
            CACHE_FILE.write_text(json.dumps(self.cache, indent=2, default=str))
        except Exception:
            pass

    # ───────────────────────────────────────────────
    # War Room v1.3+ scanners — surface the agents'
    # actual research, decisions, topology, and infra
    # state in the dashboard cache.
    # ───────────────────────────────────────────────

    def _scan_research(self):
        """Scan the project-root research directory for agent-produced docs.

        These are the artifacts the agents (jarvis-* leads, scouts, council)
        produced during previous sprints. Each becomes a 'memory' item the
        dashboard can surface.
        """
        research = []
        candidates = [
            PROJECT_ROOT / "docs" / "research",
            PROJECT_ROOT / "research",
            PROJECT_ROOT / "decisions",
        ]
        for root in candidates:
            if not root.exists():
                continue
            for p in sorted(root.glob("*.md")):
                # Skip prompt/input files, only include actual deliverables
                name = p.name
                if name.startswith("_") or "_input" in name or "_prompt" in name:
                    continue
                text = ""
                try:
                    text = p.read_text(errors="ignore")[:4000]
                except Exception:
                    pass
                # Project detection by substring
                project = ""
                proj_root = HOME / ".hermes" / "memory" / "projects"
                if proj_root.exists():
                    for proj_dir in proj_root.iterdir():
                        if proj_dir.is_dir() and proj_dir.name in text:
                            project = proj_dir.name
                            break
                # Round id from filename (e.g. r01-codebase-audit.md)
                round_id = ""
                m = re.match(r"^(r\d+|c\d+-r\d+|D-\d+-\d+-\d+)", name)
                if m:
                    round_id = m.group(1)
                research.append({
                    "id": name,
                    "round_id": round_id,
                    "title": self._first_heading(p) or name,
                    "source": str(p),
                    "project": project,
                    "kind": p.parent.name,
                    "created_at": self._file_timestamp(p),
                    "size_bytes": p.stat().st_size,
                })
        return research

    def _scan_departments(self):
        """Scan the per-department docs under docs/departments/<name>/.

        These contain agent operating notes per department (engineering,
        product, marketing, etc.) — the kind of context a council member
        needs to do tier-2/3 reviews.
        """
        departments = {}
        depts_root = PROJECT_ROOT / "docs" / "departments"
        if not depts_root.exists():
            return departments
        for dept_dir in sorted(depts_root.iterdir()):
            if not dept_dir.is_dir():
                continue
            files = []
            for p in sorted(dept_dir.glob("**/*.md")):
                rel = p.relative_to(dept_dir)
                text = ""
                try:
                    text = p.read_text(errors="ignore")[:3000]
                except Exception:
                    pass
                files.append({
                    "path": str(p.relative_to(PROJECT_ROOT)),
                    "name": p.name,
                    "title": self._first_heading(p) or p.stem,
                    "kind": rel.parent.as_posix() if rel.parent != Path(".") else "root",
                    "size_bytes": p.stat().st_size,
                    "updated_at": self._file_timestamp(p),
                    "excerpt": text[:400].replace("\n", " ").strip(),
                })
            if files:
                readme = dept_dir / "README.md"
                departments[dept_dir.name] = {
                    "name": dept_dir.name,
                    "title": self._first_heading(readme) if readme.exists() else dept_dir.name.title(),
                    "file_count": len(files),
                    "files": files,
                }
        return departments

    def _scan_topology(self):
        """Read kanban.db for the full company OS topology: companies, teams,
        agents, nodes, edges, budgets. Surfaces the org chart on the
        Agent Constellation panel.
        """
        if not KANBAN_DB.exists():
            return {}
        try:
            conn = sqlite3.connect(str(KANBAN_DB), timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            out: dict[str, Any] = {}
            for table in ("companies", "teams", "agents", "nodes", "edges", "budgets"):
                try:
                    cur.execute(f"SELECT * FROM {table}")
                    rows = [dict(r) for r in cur.fetchall()]
                except Exception:
                    rows = []
                out[table] = rows
            try:
                cur.execute("SELECT COUNT(*) FROM audit_log")
                out["audit_log_count"] = cur.fetchone()[0]
            except Exception:
                out["audit_log_count"] = 0
            conn.close()
            return out
        except Exception:
            return {}

    def _scan_human_gates(self):
        """Surface the human-in-the-loop gates DB so the Council Chamber
        panel can show pending approvals.
        """
        db = DASHBOARD_DATA / "human_gates.db"
        if not db.exists():
            return {"pending": [], "history": [], "audit_count": 0}
        try:
            conn = sqlite3.connect(str(db), timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='human_gates'")
            if not cur.fetchone():
                conn.close()
                return {"pending": [], "history": [], "audit_count": 0}
            cur.execute("SELECT * FROM human_gates ORDER BY created_at DESC LIMIT 50")
            rows = [dict(r) for r in cur.fetchall()]
            audit_count = 0
            try:
                cur.execute("SELECT COUNT(*) FROM audit_log")
                audit_count = cur.fetchone()[0]
            except Exception:
                pass
            conn.close()
            return {"pending": [g for g in rows if g.get("status") == "pending"], "history": rows, "audit_count": audit_count}
        except Exception:
            return {"pending": [], "history": [], "audit_count": 0}

    def _scan_fact_store(self):
        """Surface the FTS-backed fact store so the Memory Nexus panel can
        show agent-recorded facts.
        """
        db = DASHBOARD_DATA / "fact_store.db"
        if not db.exists():
            return {"facts": [], "count": 0}
        try:
            conn = sqlite3.connect(str(db), timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
            if not cur.fetchone():
                conn.close()
                return {"facts": [], "count": 0}
            cur.execute("SELECT rowid, source, content, created_at FROM facts ORDER BY rowid DESC LIMIT 100")
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM facts")
            total = cur.fetchone()[0]
            conn.close()
            return {"facts": rows, "count": total}
        except Exception:
            return {"facts": [], "count": 0}
