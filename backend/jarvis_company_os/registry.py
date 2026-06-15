"""jarvis_company_os.registry — Spec 04 company/team/agent/edge CRUD + seed.

Implements Boss D-C: seed_default_company() runs from startup, idempotent.
Source profiles: ~/.hermes/profiles/jarvis*/config.yaml
"""
import os
import sqlite3
import json
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

log = logging.getLogger("jarvis_company_os.registry")

# Resolve the SQLite path in this order (D-2026-06-08-topology-editor sub-phase 1):
#   1. JARVIS_COMPANY_OS_DB env var (used by tests + custom deploys)
#   2. core.config.KANBAN_DB (the rest of the dashboard)
#   3. Legacy hardcoded path (backwards compat for the original Ubuntu deploy)
# The env override is the only one tests can set; the others are read-only defaults.


def _resolve_paths() -> tuple[Path, Path]:
    """Return (KANBAN_DB_PATH, HERMES_HOME), respecting env overrides.

    This is a function (not module-level constants) so tests can monkeypatch
    the env var *after* the module is imported and still see the right path.
    The two module-level constants KANBAN_DB_PATH / HERMES_HOME are kept for
    backwards compatibility but are re-evaluated lazily inside registry
    functions.
    """
    home_env = os.environ.get("JARVIS_COMPANY_OS_HERMES_HOME")
    db_env = os.environ.get("JARVIS_COMPANY_OS_DB")
    if db_env:
        db_path = Path(db_env)
        if home_env:
            home = Path(home_env)
        else:
            # ~/.hermes/kanban.db -> ~/.hermes (the legacy layout)
            home = db_path.parent.parent
    else:
        from core import config as _core_config
        db_path = Path(_core_config.KANBAN_DB)
        home = _core_config.HERMES
    return db_path, home

# Council hierarchy: child -> parent (per Boss D-D verification #2)
# Updated 2026-06-09 (Agentic Army sprint, D-2026-06-09) to include the
# 14 new specialist profiles. See scripts/hermes_profiles.yaml for the
# canonical source. Profile == Agent for these new entries.
COUNCIL_HIERARCHY = {
    "jarvis-manager": "jarvis-boss",
    "jarvis-secretary": "jarvis-manager",
    "jarvis-engineering-lead": "jarvis-manager",
    "jarvis-qa-lead": "jarvis-engineering-lead",
    "jarvis-security-lead": "jarvis-engineering-lead",
    "jarvis-docs-lead": "jarvis-engineering-lead",
    "jarvis-product-lead": "jarvis-manager",
    "jarvis-scout": "jarvis-manager",
    "jarvis-council": "jarvis-boss",
    "jarvis-council-departments": "jarvis-boss",
    "jarvis": "jarvis-boss",
    "quant-boss": "jarvis-boss",
    "researcher": "jarvis-docs-lead",
    "poopmaster": "jarvis",
    # ── New specialist profiles (D-2026-06-09) ────────────────────────
    "jarvis-frontend": "jarvis-engineering-lead",
    "jarvis-ui_ux": "jarvis-product-lead",
    "jarvis-backend": "jarvis-engineering-lead",
    "jarvis-mobile": "jarvis-engineering-lead",
    "jarvis-data-ml": "jarvis-engineering-lead",
    "jarvis-devops": "jarvis-engineering-lead",
    "jarvis-marketing": "jarvis-product-lead",
    "jarvis-sales": "jarvis-product-lead",
    "jarvis-finance": "jarvis-boss",
    "jarvis-legal": "jarvis-boss",
    "jarvis-customer-success": "jarvis-product-lead",
    "jarvis-researcher": "jarvis-docs-lead",
}

# Horizontal collaborations (collaborates_with edges)
# Updated 2026-06-09 — derived from the YAML spec.
COLLABORATIONS = [
    ("jarvis-engineering-lead", "jarvis-qa-lead"),
    ("jarvis-engineering-lead", "jarvis-security-lead"),
    ("jarvis-engineering-lead", "jarvis-docs-lead"),
    ("jarvis-engineering-lead", "jarvis-product-lead"),
    ("jarvis-qa-lead", "jarvis-security-lead"),
    ("jarvis-manager", "jarvis-secretary"),
    ("jarvis-boss", "jarvis-council"),
    ("jarvis-boss", "jarvis-council-departments"),
    # ── New specialist collaborations (D-2026-06-09) ──────────────────
    ("jarvis-frontend", "jarvis-ui_ux"),
    ("jarvis-frontend", "jarvis-backend"),
    ("jarvis-frontend", "jarvis-qa-lead"),
    ("jarvis-ui_ux", "jarvis-product-lead"),
    ("jarvis-backend", "jarvis-data-ml"),
    ("jarvis-backend", "jarvis-devops"),
    ("jarvis-backend", "jarvis-qa-lead"),
    ("jarvis-backend", "jarvis-security-lead"),
    ("jarvis-mobile", "jarvis-frontend"),
    ("jarvis-mobile", "jarvis-ui_ux"),
    ("jarvis-mobile", "jarvis-backend"),
    ("jarvis-data-ml", "jarvis-devops"),
    ("jarvis-data-ml", "jarvis-researcher"),
    ("jarvis-devops", "jarvis-security-lead"),
    ("jarvis-marketing", "jarvis-sales"),
    ("jarvis-marketing", "jarvis-ui_ux"),
    ("jarvis-marketing", "jarvis-product-lead"),
    ("jarvis-sales", "jarvis-finance"),
    ("jarvis-sales", "jarvis-customer-success"),
    ("jarvis-finance", "jarvis-legal"),
    ("jarvis-legal", "jarvis-security-lead"),
    ("jarvis-legal", "jarvis-product-lead"),
    ("jarvis-customer-success", "jarvis-qa-lead"),
    ("jarvis-customer-success", "jarvis-product-lead"),
    ("jarvis-researcher", "jarvis-scout"),
    ("jarvis-researcher", "jarvis-product-lead"),
    ("jarvis-researcher", "jarvis-data-ml"),
    ("jarvis-council-departments", "jarvis-council"),
    ("jarvis-council-departments", "jarvis-manager"),
]

# Map profile -> team
TEAM_MAP = {
    "jarvis-boss": "leadership",
    "jarvis-manager": "leadership",
    "jarvis-council": "leadership",
    "jarvis-council-departments": "leadership",
    "jarvis-secretary": "operations",
    "jarvis-product-lead": "operations",
    "jarvis-engineering-lead": "engineering",
    "jarvis-qa-lead": "engineering",
    "jarvis-security-lead": "engineering",
    "jarvis-docs-lead": "engineering",
    "jarvis-scout": "research",
    "researcher": "research",
    "jarvis": "default",
    "quant-boss": "quant",
    "poopmaster": "default",
    # ── New specialist teams (D-2026-06-09) ───────────────────────────
    "jarvis-frontend": "engineering",
    "jarvis-ui_ux": "design",
    "jarvis-backend": "engineering",
    "jarvis-mobile": "engineering",
    "jarvis-data-ml": "engineering",
    "jarvis-devops": "engineering",
    "jarvis-marketing": "growth",
    "jarvis-sales": "growth",
    "jarvis-finance": "operations",
    "jarvis-legal": "operations",
    "jarvis-customer-success": "operations",
    "jarvis-researcher": "research",
}


# D-2026-06-09 (Phase 4, sub-task 4.0): single source of truth for the
# known-profile allowlist. Both `backend/api/discord_gateway.py`
# (Phase 3) and the Phase 4 Council of Departments must agree on
# which jarvis profiles exist. Derived from TEAM_MAP so adding a new
# profile to TEAM_MAP automatically updates the allowlist everywhere.
KNOWN_PROFILES = frozenset(TEAM_MAP.keys())


def _profile_path(slug: str) -> Optional[Path]:
    _db, home = _resolve_paths()
    p = home / "profiles" / slug / "config.yaml"
    return p if p.exists() else None


def _read_profile_meta(slug: str) -> Dict[str, Any]:
    """Lightweight profile read (no yaml dep). Returns name/role/model defaults."""
    p = _profile_path(slug)
    name = slug
    model = "unknown"
    role = slug.replace("jarvis-", "").replace("-", " ")
    if p:
        try:
            content = p.read_text()
            for line in content.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("model:") and ":" in line:
                    model = line.split(":", 1)[1].strip()
        except Exception as e:
            log.warning("profile read failed for %s: %s", slug, e)
    return {"name": name, "model": model, "role": role}


def _requests_limit_for(model: str) -> int:
    """Subscription-worker daily request cap by model tier."""
    if "opus" in model.lower() or "sonnet" in model.lower():
        return 200
    if "codex" in model.lower() or "gpt" in model.lower():
        return 500
    if "minimax" in model.lower() or "haiku" in model.lower():
        return 1000
    return 100


def seed_default_company() -> Dict[str, Any]:
    """Boss D-C: idempotent seed; skipped if companies count > 0.

    Creates the 'jarvis-war-room' company, single 'hermes-local-0' node,
    one team per unique TEAM_MAP value, agents for every detected profile,
    reports_to + collaborates_with edges per COUNCIL_HIERARCHY/COLLABORATIONS.

    D-2026-06-08-topology-editor (sub-phase 1): also bootstraps the schema
    if it doesn't exist. The original Ubuntu deploy ran migrations from
    /home/ubuntu/jarvis-war-room/migrations/*.sql (never committed); we now
    ship the equivalent CREATE TABLE IF NOT EXISTS inline so the company OS
    works on any host without a separate migrations step. Once we have a
    real migrations directory, this CREATE TABLE IF NOT EXISTS is a harmless
    no-op.
    """
    # Ensure parent dir + db file exist; sqlite3.connect creates the file
    # on first open, so this just guarantees the .hermes path is writable.
    db_path, _home = _resolve_paths()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        # Schema bootstrap (idempotent). Mirrors the original migrations/001..003.
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                mission TEXT,
                goal TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                budget_tokens INTEGER,
                budget_usd REAL,
                policy_json TEXT,
                require_board_approval INTEGER DEFAULT 0,
                max_headcount INTEGER,
                max_org_depth INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                address TEXT,
                backend TEXT,
                capacity_json TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                namespace TEXT,
                last_liveness_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                team_id TEXT,
                node_id TEXT,
                name TEXT NOT NULL,
                role TEXT,
                worker_type TEXT,
                status TEXT NOT NULL DEFAULT 'idle',
                worker_kind TEXT,
                model_binding TEXT,
                heartbeat_schedule TEXT,
                monthly_budget_json TEXT,
                hire_rate_json TEXT,
                soul_path TEXT,
                agent_card_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                type TEXT NOT NULL,
                from_agent TEXT,
                to_agent TEXT,
                meta_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id TEXT PRIMARY KEY,
                scope TEXT,
                scope_id TEXT,
                period TEXT,
                tokens_limit INTEGER,
                usd_limit REAL,
                requests_limit INTEGER,
                reset_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                ts TEXT DEFAULT (datetime('now')),
                actor TEXT,
                action TEXT,
                target TEXT,
                detail_json TEXT
            );
        """)
        conn.commit()

        # Idempotency check
        cur = conn.execute("SELECT COUNT(*) FROM companies")
        if cur.fetchone()[0] > 0:
            return {"status": "skipped", "reason": "companies already seeded"}

        # 1. Company
        company_id = "jarvis-war-room"
        conn.execute(
            """INSERT INTO companies
               (id, name, mission, goal, status, budget_tokens, budget_usd,
                policy_json, require_board_approval, max_headcount, max_org_depth)
               VALUES (?, ?, ?, ?, 'active', 10000000, 100.0, ?, 1, 50, 5)""",
            (
                company_id,
                "Jarvis War Room",
                "Self-hosted agent organization operating under board approval",
                "Ship minimal e2e slice (spec 04 §5) by Phase 3 done",
                json.dumps({"strict_cross_team": True, "intra_team_peer": True}),
            ),
        )

        # 2. Node (per Boss gap #4 namespace column)
        conn.execute(
            """INSERT INTO nodes
               (id, kind, address, backend, capacity_json, status, namespace)
               VALUES (?, 'control', 'local://hermes', 'local', ?, 'active', 'jarvis')""",
            ("hermes-local-0", json.dumps({"max_concurrent_tasks": 4}))  # cap 11+ agents
        )

        # 3. Teams (unique values)
        teams = sorted(set(TEAM_MAP.values()))
        for t in teams:
            conn.execute(
                "INSERT INTO teams (id, company_id, name) VALUES (?, ?, ?)",
                (t, company_id, t.title()),
            )

        # 4. Discover profiles (graceful if profiles dir doesn't exist yet —
        # this is a fresh environment and the seed shouldn't crash).
        _db, home = _resolve_paths()
        profile_dir = home / "profiles"
        log.info("seed_default_company: profile_dir=%s exists=%s", profile_dir, profile_dir.exists())
        if profile_dir.exists():
            detected = sorted(
                p.name for p in profile_dir.iterdir()
                if p.is_dir() and (p / "config.yaml").exists()
            )
        else:
            log.info("seed_default_company: no profiles dir at %s; seeding with 0 agents", profile_dir)
            detected = []

        # 5. Agents
        for slug in detected:
            meta = _read_profile_meta(slug)
            team = TEAM_MAP.get(slug, "default")
            requests_cap = _requests_limit_for(meta["model"])
            conn.execute(
                """INSERT INTO agents
                   (id, company_id, team_id, node_id, name, role, worker_type,
                    status, worker_kind, model_binding, monthly_budget_json,
                    hire_rate_json, soul_path)
                   VALUES (?, ?, ?, 'hermes-local-0', ?, ?, ?, 'idle',
                           'api', ?, ?, ?, ?)""",
                (
                    slug,
                    company_id,
                    team,
                    meta["name"],
                    meta["role"],
                    meta["model"],         # worker_type
                    meta["model"],         # model_binding
                    json.dumps({"tokens": 1_000_000, "usd": 5.0,
                                "requests_limit": requests_cap}),
                    json.dumps({"count": 0, "window": "24h", "reset_at": None}),
                    str(home / "profiles" / slug / "SOUL.md"),
                ),
            )
            # Per-agent budget row
            conn.execute(
                """INSERT INTO budgets
                   (id, scope, scope_id, period, tokens_limit, usd_limit,
                    requests_limit, reset_at)
                   VALUES (?, 'agent', ?, 'monthly', 1000000, 5.0, ?, ?)""",
                (
                    f"budget-{slug}",
                    slug,
                    requests_cap,
                    None,  # set on first reset cron
                ),
            )

        # 6. Edges — reports_to
        for child, parent in COUNCIL_HIERARCHY.items():
            if child in detected and parent in detected:
                conn.execute(
                    """INSERT INTO edges (id, company_id, type, from_agent, to_agent)
                       VALUES (?, ?, 'reports_to', ?, ?)""",
                    (str(uuid.uuid4()), company_id, child, parent),
                )

        # 7. Edges — collaborates_with
        for a, b in COLLABORATIONS:
            if a in detected and b in detected:
                conn.execute(
                    """INSERT INTO edges (id, company_id, type, from_agent, to_agent)
                       VALUES (?, ?, 'collaborates_with', ?, ?)""",
                    (str(uuid.uuid4()), company_id, a, b),
                )

        # 8. Audit (seed action)
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), 'jarvis-company-os', 'seed_default_company',
                       ?, ?)""",
            (str(uuid.uuid4()), company_id,
             json.dumps({"agents": len(detected), "teams": len(teams)})),
        )

        conn.commit()
        log.info("seed_default_company: %d agents, %d teams, %d hierarchy edges",
                 len(detected), len(teams), sum(1 for c, p in COUNCIL_HIERARCHY.items()
                                              if c in detected and p in detected))
        return {
            "status": "seeded",
            "company_id": company_id,
            "agents": len(detected),
            "teams": len(teams),
            "profiles": detected,
        }
    except Exception as e:
        conn.rollback()
        log.exception("seed_default_company failed")
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def get_topology(company_id: str) -> Dict[str, Any]:
    """Boss D4 (D-D acceptance): response shape {nodes, agents, edges}."""
    db_path, _home = _resolve_paths()
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        nodes = [dict(r) for r in conn.execute(
            "SELECT id, kind, address, backend, status, namespace, last_liveness_at, created_at "
            "FROM nodes WHERE 1=1"
        ).fetchall()]
        # serialize json cols
        for n in nodes:
            try:
                n["capacity_json"] = json.loads(n.get("capacity_json") or "null")
            except Exception:
                pass

        agents = [dict(r) for r in conn.execute(
            "SELECT id, company_id, team_id, node_id, name, role, worker_type, status, "
            "worker_kind, model_binding, heartbeat_schedule, monthly_budget_json, "
            "hire_rate_json, created_at FROM agents WHERE company_id = ?",
            (company_id,),
        ).fetchall()]
        for a in agents:
            for col in ("monthly_budget_json", "hire_rate_json", "agent_card_json"):
                v = a.get(col)
                if v and isinstance(v, str):
                    try:
                        a[col] = json.loads(v)
                    except Exception:
                        pass

        edges = [dict(r) for r in conn.execute(
            "SELECT id, type, from_agent, to_agent, meta_json FROM edges "
            "WHERE company_id = ?",
            (company_id,),
        ).fetchall()]
        for e in edges:
            v = e.get("meta_json")
            if v and isinstance(v, str):
                try:
                    e["meta_json"] = json.loads(v)
                except Exception:
                    pass

        return {"company_id": company_id, "nodes": nodes, "agents": agents, "edges": edges}
    finally:
        conn.close()
