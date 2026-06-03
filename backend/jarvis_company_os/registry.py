"""jarvis_company_os.registry — Spec 04 company/team/agent/edge CRUD + seed.

Implements Boss D-C: seed_default_company() runs from startup, idempotent.
Source profiles: ~/.hermes/profiles/jarvis*/config.yaml
"""
import sqlite3
import json
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

log = logging.getLogger("jarvis_company_os.registry")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")
HERMES_HOME = Path("/home/ubuntu/.hermes")

# Council hierarchy: child -> parent (per Boss D-D verification #2)
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
    "jarvis": "jarvis-boss",
    "quant-boss": "jarvis-boss",
    "researcher": "jarvis-docs-lead",
    "poopmaster": "jarvis",
}

# Horizontal collaborations (collaborates_with edges)
COLLABORATIONS = [
    ("jarvis-engineering-lead", "jarvis-qa-lead"),
    ("jarvis-engineering-lead", "jarvis-security-lead"),
    ("jarvis-engineering-lead", "jarvis-docs-lead"),
    ("jarvis-engineering-lead", "jarvis-product-lead"),
    ("jarvis-qa-lead", "jarvis-security-lead"),
    ("jarvis-manager", "jarvis-secretary"),
    ("jarvis-boss", "jarvis-council"),
]

# Map profile -> team
TEAM_MAP = {
    "jarvis-boss": "leadership",
    "jarvis-manager": "leadership",
    "jarvis-council": "leadership",
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
}


def _profile_path(slug: str) -> Optional[Path]:
    p = HERMES_HOME / "profiles" / slug / "config.yaml"
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
    """
    if not KANBAN_DB_PATH.exists():
        return {"status": "skipped", "reason": f"kanban.db not found at {KANBAN_DB_PATH}"}

    conn = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    try:
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

        # 4. Discover profiles
        profile_dir = HERMES_HOME / "profiles"
        detected = sorted(
            p.name for p in profile_dir.iterdir()
            if p.is_dir() and (p / "config.yaml").exists()
        )

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
                    str(HERMES_HOME / "profiles" / slug / "SOUL.md"),
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
    conn = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
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
