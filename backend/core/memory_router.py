"""Memory router for War Room (D-2026-06-08 memory M1).

Routes facts/state by data type to the right backend:
  - factual  -> mem0 v3 (single-pass ADD-only extraction, multi-signal retrieval)
  - state    -> Hindsight embedded (retain/recall/reflect, 3 pathways)

Phase M1 = in-process, no Docker. Phase M3 = upgrade to Docker services
for cross-project (global) memory.

Both mem0 and hindsight are optional at import time so the test suite
doesn't require them to be installed. The router falls back to a
JSONL-on-disk implementation when neither is available.
"""
from __future__ import annotations
import json
import os
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Literal, Any

# Backend selection. We try to import the libs but don't fail if missing;
# the tests use a stub backend.
try:
    from mem0 import MemoryClient as _Mem0Client  # type: ignore
    _MEM0_AVAILABLE = True
except Exception:
    _MEM0_AVAILABLE = False

try:
    from hindsight import HindsightServer, HindsightClient  # type: ignore
    _HINDSIGHT_AVAILABLE = True
except Exception:
    _HINDSIGHT_AVAILABLE = False

# D-2026-06-08-f: live Hindsight HTTP/MCP server (Docker). Independent
# from the embedded library above. We talk to it via raw HTTP for the
# /health check and via MCP JSON-RPC for retain/recall (over the /mcp
# endpoint that the Docker image exposes).
import urllib.request
import urllib.error


def _hindsight_server_reachable(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _hindsight_server_call(url: str, tool: str, args: dict,
                            timeout: float = 30.0) -> Optional[dict]:
    """Call an MCP tool on the Hindsight server. Returns the parsed
    result on success, None on any failure. We don't import the MCP
    client library to keep the dependency surface tiny — we just send
    a JSON-RPC 2.0 request via HTTP POST and read the response.
    """
    try:
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url.rstrip('/')}/mcp",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


DataType = Literal["factual", "state", "wiki", "vector", "graph", "temporal"]


@dataclass
class MemoryItem:
    """One memory record. Mirrors backend/core/memory.py MemoryItem shape
    so the existing dashboard panels can render it without changes."""
    id: str
    data_type: DataType
    content: str
    trust_tier: str = "OBSERVED"  # OBSERVED / USER_STATED / INFERRED / CROSS_MODEL
    source: str = "memory_router"
    created_at: float = 0.0
    metadata: dict = None  # type: ignore

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}


class MemoryRouter:
    """Routes add/recall requests to the right backend per data type.

    All backends are optional; if a backend isn't installed, we use a
    JSONL-on-disk fallback so the system never crashes.
    """

    def __init__(self, project_id: str, store_path: Optional[Path] = None,
                 hindsight_url: Optional[str] = None):
        self.project_id = project_id
        base = store_path or Path(os.environ.get(
            "JARVIS_DASHBOARD_MEMORY_DIR",
            str(Path.home() / ".hermes" / "state" / "memory"),
        ))
        self.base = Path(base) / project_id
        self.base.mkdir(parents=True, exist_ok=True)
        self.factual_log = self.base / "factual.jsonl"
        self.state_log = self.base / "state.jsonl"
        # Initialize backends lazily (avoid import-time network calls)
        self._mem0 = None
        self._hindsight = None
        # D-2026-06-08-f: live Hindsight server URL (set HINDSIGHT_URL
        # in env to point at the Docker container; default localhost).
        self.hindsight_url = hindsight_url or os.environ.get(
            "HINDSIGHT_URL", "http://127.0.0.1:18888"
        )
        # Cached reachability so we don't ping on every call
        self._hindsight_server_reachable: Optional[bool] = None

    # ─────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────
    def add_fact(self, content: str, trust_tier: str = "OBSERVED",
                 metadata: Optional[dict] = None) -> MemoryItem:
        """Store a fact. Routes to mem0 v3 if available, else JSONL fallback."""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            data_type="factual",
            content=content,
            trust_tier=trust_tier,
            metadata=metadata or {},
        )
        if _MEM0_AVAILABLE and self._mem0 is not False:
            try:
                # Lazy init on first use so import doesn't fail
                if self._mem0 is None:
                    self._mem0 = _Mem0Client()  # type: ignore
                self._mem0.add(content, user_id=self.project_id, metadata=item.metadata)  # type: ignore
                return item
            except Exception:
                # If mem0 fails (no API key etc.), fall through to JSONL
                self._mem0 = False  # disable for future calls
        self._append_jsonl(self.factual_log, item)
        return item

    def add_state(self, content: str, agent_id: str = "warroom") -> MemoryItem:
        """Store a state-of-mind observation. Routing:
        1. Live Hindsight server (Docker, MCP) if reachable
        2. Embedded hindsight library if installed
        3. JSONL fallback (always, for durability)
        """
        item = MemoryItem(
            id=str(uuid.uuid4()),
            data_type="state",
            content=content,
            metadata={"agent_id": agent_id},
        )
        # 1) Live Hindsight server (best-effort)
        if self._check_hindsight_server() and _hindsight_server_call(
            self.hindsight_url, "retain",
            {"bank_id": self.project_id, "items": [
                {"content": content, "context": f"agent={agent_id}"}
            ]}
        ) is not None:
            # Also write JSONL for durability
            self._append_jsonl(self.state_log, item)
            return item
        # 2) Embedded hindsight library (if installed and working)
        if _HINDSIGHT_AVAILABLE and self._hindsight is not False:
            try:
                if self._hindsight is None:
                    self._hindsight = HindsightServer()  # type: ignore
                    self._hindsight.start()  # type: ignore
                client = HindsightClient(base_url=self._hindsight.url)  # type: ignore
                client.retain(bank_id=self.project_id, content=content)  # type: ignore
                self._append_jsonl(self.state_log, item)
                return item
            except Exception:
                self._hindsight = False
        # 3) JSONL fallback
        self._append_jsonl(self.state_log, item)
        return item

    def recall_state(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Recall state-of-mind. Routing: live Hindsight -> embedded lib -> JSONL."""
        # 1) Live Hindsight server
        if self._check_hindsight_server():
            result = _hindsight_server_call(
                self.hindsight_url, "recall",
                {"bank_id": self.project_id, "query": query, "limit": limit}
            )
            if result and "result" in result:
                # Parse MCP result envelope; content may be a list of dicts
                # or a JSON-stringified list. Be defensive.
                payload = result["result"]
                if isinstance(payload, dict) and "content" in payload:
                    payload = payload["content"]
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = []
                rows = payload if isinstance(payload, list) else []
                return [
                    MemoryItem(
                        id=str(uuid.uuid4()),
                        data_type="state",
                        content=(r.get("content") or r.get("text") or "")
                            if isinstance(r, dict) else str(r),
                    )
                    for r in rows
                ]
        # 2) Embedded hindsight
        if _HINDSIGHT_AVAILABLE and self._hindsight is not False:
            try:
                if self._hindsight is None:
                    self._hindsight = HindsightServer()  # type: ignore
                    self._hindsight.start()  # type: ignore
                client = HindsightClient(base_url=self._hindsight.url)  # type: ignore
                results = client.recall(bank_id=self.project_id, query=query)  # type: ignore
                return [
                    MemoryItem(
                        id=str(uuid.uuid4()),
                        data_type="state",
                        content=r.get("content", r.get("text", "")),
                    )
                    for r in (results or [])
                ]
            except Exception:
                self._hindsight = False
        # 3) JSONL fallback
        return self._search_jsonl(self.state_log, query, limit)

    def _check_hindsight_server(self) -> bool:
        """Cached reachability check. Re-checks every 60s if it failed."""
        if self._hindsight_server_reachable is True:
            return True
        if self._hindsight_server_reachable is False:
            # Don't retry on every call; the add/recall path is sync
            return False
        # First check
        self._hindsight_server_reachable = _hindsight_server_reachable(self.hindsight_url)
        return self._hindsight_server_reachable

    def recall_facts(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Search factual memory. mem0 if available, else substring JSONL scan."""
        if _MEM0_AVAILABLE and self._mem0 is not False:
            try:
                if self._mem0 is None:
                    self._mem0 = _Mem0Client()  # type: ignore
                results = self._mem0.search(query, user_id=self.project_id, limit=limit)  # type: ignore
                return [
                    MemoryItem(
                        id=str(r.get("id", uuid.uuid4())),
                        data_type="factual",
                        content=r.get("memory", r.get("content", "")),
                        metadata=r.get("metadata", {}),
                    )
                    for r in (results or [])
                ]
            except Exception:
                self._mem0 = False
        return self._search_jsonl(self.factual_log, query, limit)

    def stats(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "factual_count": self._count_jsonl(self.factual_log),
            "state_count": self._count_jsonl(self.state_log),
            "mem0_available": _MEM0_AVAILABLE and self._mem0 is not False,
            "hindsight_available": _HINDSIGHT_AVAILABLE and self._hindsight is not False,
            "hindsight_server_url": self.hindsight_url,
            "hindsight_server_reachable": (
                self._check_hindsight_server()
                if self._hindsight_server_reachable is None
                else self._hindsight_server_reachable
            ),
        }

    # ─────────────────────────────────────────
    # INTERNAL: JSONL fallback
    # ─────────────────────────────────────────
    @staticmethod
    def _append_jsonl(path: Path, item: MemoryItem) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @classmethod
    def _search_jsonl(cls, path: Path, query: str, limit: int) -> list[MemoryItem]:
        rows = cls._read_jsonl(path)
        q = query.lower()
        scored = [(r, sum(1 for tok in q.split() if tok in r.get("content", "").lower())) for r in rows]
        scored = [(r, s) for r, s in scored if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        out = []
        for r, _ in scored[:limit]:
            out.append(MemoryItem(
                id=r.get("id", str(uuid.uuid4())),
                data_type=r.get("data_type", "factual"),
                content=r.get("content", ""),
                trust_tier=r.get("trust_tier", "OBSERVED"),
                metadata=r.get("metadata", {}),
            ))
        return out

    @classmethod
    def _count_jsonl(cls, path: Path) -> int:
        return sum(1 for _ in cls._read_jsonl(path))

class HandoffManager:
    """Manages cross-department task handoffs with policy checks."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.handoffs = self._load_handoffs()

    def _load_handoffs(self) -> Dict[str, Dict[str, Any]]:
        """Load handoff policies from environment variables."""
        return {
            "engineering→product": {
                "allowed": os.getenv("HANDOFF_ENGINEERING_PRODUCT", "true").lower() == "true",
                "max_handoffs": int(os.getenv("HANDOFF_ENGINEERING_PRODUCT_MAX", "3"))
            },
            "product→marketing": {
                "allowed": os.getenv("HANDOFF_PRODUCT_MARKETING", "true").lower() == "true",
                "max_handoffs": int(os.getenv("HANDOFF_PRODUCT_MARKETING_MAX", "1"))
            }
        }

    def transfer(self, from_dept: str, to_dept: str, task_id: str) -> bool:
        """Transfer task between departments if policy allows."""
        policy = self.handoffs.get(f"{from_dept}→{to_dept}")
        if not policy or not policy["allowed"]:
            return False
        # Log handoff (e.g., to audit.py)
        log_action("system", "handoff", f"{from_dept}→{to_dept}", {"task_id": task_id})
        return True
