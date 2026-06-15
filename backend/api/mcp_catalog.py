"""MCP Catalog API (D-2026-06-15).

The dashboard now supports a registry of MCP (Model Context Protocol)
servers alongside agent skills. Each entry is a metadata record — it
describes the MCP and how to install it but does NOT actually install
it. The user's own MCP client (Claude CLI, Codex CLI, etc.) is what
runs the MCP at chat time.

Source types supported:
  - github_url   : a GitHub repo (e.g. https://github.com/microsoft/playwright-mcp)
  - webpage_url  : any other URL (e.g. https://modelcontextprotocol.io/...)
  - name         : bare slug (user will fill in install_command manually)

Data persisted at:
  C:\\Users\\saiyu\\AppData\\Local\\hermes\\state\\dashboard\\mcp_catalog.json
  (overridden by $MCP_CATALOG_FILE for tests)

Safety contract: this dashboard-local file does NOT mutate any
Hermes profile config, MCP client config (~/.claude.json,
~/.codex/config.toml), or any system state. It is a registry only.
The actual install command is shown to the user for them to run.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user
from core.config import DASHBOARD_DATA

router = APIRouter(prefix="/mcp", tags=["mcp"])

CATALOG_FILE = Path(
    os.environ.get(
        "MCP_CATALOG_FILE",
        str(DASHBOARD_DATA / "mcp_catalog.json"),
    )
).expanduser()


# ── Pydantic models ──────────────────────────────────────────────────

class MCPItem(BaseModel):
    """A registered MCP server in the dashboard-local catalog."""
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    summary: str = Field("", max_length=500)
    description: str = Field("", max_length=2000)
    icon: str = Field("🔌", max_length=8)  # emoji or short URL
    source_type: str = Field(..., pattern=r"^(github_url|webpage_url|name)$")
    source_url: str = Field("", max_length=500)
    source_repo: str = Field("", max_length=500)  # canonicalized GitHub repo slug
    install_command: str = Field("", max_length=500)
    transport: str = Field("stdio", pattern=r"^(stdio|http|sse|websocket)$")
    scope: str = Field("global-hermes", max_length=64)  # reuses project scope slugs
    departments: List[str] = Field(default_factory=list)
    assigned_agents: List[str] = Field(default_factory=list)
    trust_tier: str = Field("T3", pattern=r"^(T1|T2|T3)$")
    added_by: str = Field("user", max_length=64)
    added_at: str = Field("", max_length=64)
    notes: str = Field("", max_length=500)


class CatalogPayload(BaseModel):
    writes_profile_configs: bool = False
    storage: str
    count: int
    mcps: List[MCPItem]


class MCPAddRequest(BaseModel):
    """Request to add or update an MCP in the catalog."""
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    summary: str = Field("", max_length=500)
    description: str = Field("", max_length=2000)
    icon: str = Field("🔌", max_length=8)
    source_type: str = Field(..., pattern=r"^(github_url|webpage_url|name)$")
    source_url: str = Field("", max_length=500)
    source_repo: str = Field("", max_length=500)
    install_command: str = Field("", max_length=500)
    transport: str = Field("stdio", pattern=r"^(stdio|http|sse|websocket)$")
    scope: str = Field("global-hermes", max_length=64)
    departments: List[str] = Field(default_factory=list)
    trust_tier: str = Field("T3", pattern=r"^(T1|T2|T3)$")
    notes: str = Field("", max_length=500)


class ChatMCPInstallRequest(BaseModel):
    """Request from the chat: natural-language instruction or a URL.

    Examples:
        {"text": "add the playwright MCP"}
        {"text": "install https://github.com/microsoft/playwright-mcp"}
        {"text": "https://modelcontextprotocol.io/docs/servers/everything"}
        {"text": "playwright-mcp", "scope": "jarvis-war-room"}
    """
    text: str = Field(..., min_length=1, max_length=2000)
    scope: str = Field("global-hermes", max_length=64)
    assign_to: List[str] = Field(default_factory=list)


class ChatMCPInstallResponse(BaseModel):
    writes_profile_configs: bool = False
    detected_kind: str  # "github_url" | "webpage_url" | "name"
    detected_name: str
    detected_url: str
    catalog_size: int
    mcp: MCPItem
    confirmation: str  # human-readable text for the chat to echo back
    run_suggested_command: str  # the command the user can paste to actually install


class ChatIntentRequest(BaseModel):
    """Lightweight endpoint for the chat to ask: 'is this user message an
    MCP-install intent?' The frontend can call this before sending the
    chat to the LLM, so we can intercept obvious cases and not waste an
    LLM call."""
    text: str = Field(..., min_length=1, max_length=2000)


class ChatIntentResponse(BaseModel):
    is_mcp_intent: bool
    confidence: float
    reason: str
    extracted: Dict[str, Any] = Field(default_factory=dict)


# ── File I/O ────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_catalog() -> Dict[str, Any]:
    if not CATALOG_FILE.exists():
        return {"version": 1, "updated_at": "", "updated_by": "", "mcps": []}
    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "updated_at": "", "updated_by": "", "mcps": []}
    if not isinstance(data, dict):
        return {"version": 1, "updated_at": "", "updated_by": "", "mcps": []}
    if "mcps" not in data or not isinstance(data["mcps"], list):
        data["mcps"] = []
    return data


def _write_catalog(data: Dict[str, Any]) -> None:
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _catalog_payload() -> CatalogPayload:
    data = _read_catalog()
    items: List[MCPItem] = []
    for raw in data.get("mcps", []):
        try:
            items.append(MCPItem(**raw))
        except Exception:
            # skip malformed entries
            continue
    return CatalogPayload(
        storage=str(CATALOG_FILE),
        count=len(items),
        mcps=items,
    )


# ── URL detection / auto-fill helpers ───────────────────────────────

_GH_URL_RE = re.compile(
    r"^https?://github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$"
)


def detect_kind(text: str) -> tuple[str, str, str]:
    """Returns (kind, name, url). Pure function — no side effects.

    - GitHub repo URL  → ('github_url', '<owner>-<repo>', '<url>')
    - Any other URL    → ('webpage_url', derived from host+path, '<url>')
    - Bare slug/text   → ('name', cleaned text, '')
    """
    text = text.strip()
    # GitHub URL
    m = _GH_URL_RE.match(text)
    if m:
        owner, repo = m.group(1), m.group(2)
        name = f"{owner}-{repo}".lower()
        return ("github_url", name, text)
    # Other URL
    url_m = re.match(r"^https?://([^/]+)(/[^?#]*)?", text)
    if url_m:
        host = url_m.group(1).replace("www.", "")
        path = (url_m.group(2) or "").strip("/").replace("/", "-")
        # build a reasonable name: last path segment or host
        if path:
            slug = re.sub(r"[^a-zA-Z0-9_\-]", "", path.split("-")[-1].lower()) or host.split(".")[0]
        else:
            slug = host.split(".")[0]
        return ("webpage_url", slug[:48], text)
    # Bare name
    name = re.sub(r"[^a-zA-Z0-9_\-]", "-", text.lower()).strip("-")
    name = re.sub(r"-+", "-", name)[:64] or "unnamed-mcp"
    return ("name", name, "")


def auto_fill_from_url(kind: str, name: str, url: str) -> Dict[str, str]:
    """Best-effort fill of summary / install_command / transport from a URL."""
    fields: Dict[str, str] = {"summary": "", "install_command": "", "transport": "stdio"}
    if kind == "github_url":
        m = _GH_URL_RE.match(url or "")
        if m:
            owner, repo = m.group(1), m.group(2)
            fields["source_repo"] = f"{owner}/{repo}"
            # Common pattern: most MCPs are published to npm as @<owner>/<repo>-mcp
            # or <owner>/<repo>. Default to npx command.
            fields["install_command"] = (
                f"npx -y {owner}/{repo}"
            )
            fields["summary"] = f"GitHub MCP by {owner}"
    elif kind == "webpage_url":
        fields["summary"] = f"MCP documented at {url}"
        fields["install_command"] = ""  # user fills in manually for non-GH pages
    return fields


# ── Routes ──────────────────────────────────────────────────────────

@router.get("/catalog", response_model=CatalogPayload)
def list_mcps(user: str = Depends(get_current_user)) -> CatalogPayload:
    return _catalog_payload()


@router.get("/catalog/{name}", response_model=MCPItem)
def get_mcp(name: str, user: str = Depends(get_current_user)) -> MCPItem:
    data = _read_catalog()
    for raw in data.get("mcps", []):
        if raw.get("name") == name:
            return MCPItem(**raw)
    raise HTTPException(status_code=404, detail=f"mcp not found: {name}")


@router.post("/catalog/add", response_model=CatalogPayload)
def add_mcp(payload: MCPAddRequest, user: str = Depends(get_current_user)) -> CatalogPayload:
    data = _read_catalog()
    existing_names = {item.get("name") for item in data.get("mcps", [])}
    if payload.name in existing_names:
        raise HTTPException(status_code=409, detail=f"mcp already exists: {payload.name}")
    item = MCPItem(
        **payload.model_dump(),
        added_by=user,
        added_at=_now(),
    )
    data["mcps"].append(item.model_dump())
    data["updated_at"] = _now()
    data["updated_by"] = user
    _write_catalog(data)
    return _catalog_payload()


@router.delete("/catalog/{name}", response_model=CatalogPayload)
def remove_mcp(name: str, user: str = Depends(get_current_user)) -> CatalogPayload:
    data = _read_catalog()
    before = len(data.get("mcps", []))
    data["mcps"] = [m for m in data.get("mcps", []) if m.get("name") != name]
    if len(data["mcps"]) == before:
        raise HTTPException(status_code=404, detail=f"mcp not found: {name}")
    data["updated_at"] = _now()
    data["updated_by"] = user
    _write_catalog(data)
    return _catalog_payload()


@router.post("/catalog/refresh", response_model=CatalogPayload)
def refresh_catalog(user: str = Depends(get_current_user)) -> CatalogPayload:
    """Re-read the catalog file (no-op, but the SPA can call this after
    external edits). Also returns a writes_profile_configs=False flag so
    callers can confirm safety."""
    return _catalog_payload()


@router.post("/install-from-chat", response_model=ChatMCPInstallResponse)
def install_from_chat(req: ChatMCPInstallRequest, user: str = Depends(get_current_user)) -> ChatMCPInstallResponse:
    """Chat-driven MCP add.

    Accepts a free-form instruction ("add the playwright MCP"),
    a GitHub URL ("https://github.com/.../playwright-mcp"),
    a generic webpage URL, or a bare slug. Auto-detects kind and
    pre-fills the catalog entry. Returns a confirmation the chat
    can echo back to the user, plus the suggested install command.
    """
    kind, name, url = detect_kind(req.text)
    fills = auto_fill_from_url(kind, name, url)
    # Compose summary from text when auto-fill is empty
    summary = fills.get("summary") or (
        f"Added from chat by {user}: {req.text[:120]}"
    )
    install_command = fills.get("install_command", "")
    source_repo = fills.get("source_repo", "")
    data = _read_catalog()
    existing_names = {item.get("name") for item in data.get("mcps", [])}
    if name in existing_names:
        # idempotent: refresh the existing entry's metadata
        for m in data["mcps"]:
            if m.get("name") == name:
                if not m.get("install_command") and install_command:
                    m["install_command"] = install_command
                if not m.get("source_repo") and source_repo:
                    m["source_repo"] = source_repo
                break
    else:
        item = MCPItem(
            name=name,
            summary=summary,
            description=req.text[:500],
            icon="🔌",
            source_type=kind,
            source_url=url,
            source_repo=source_repo,
            install_command=install_command,
            transport="stdio",
            scope=req.scope,
            departments=[],
            assigned_agents=req.assign_to,
            trust_tier="T3",
            added_by=user,
            added_at=_now(),
            notes="added from chat",
        )
        data["mcps"].append(item.model_dump())
    data["updated_at"] = _now()
    data["updated_by"] = user
    _write_catalog(data)
    catalog = _catalog_payload()
    # Build the chat-friendly confirmation
    added = next(m for m in catalog.mcps if m.name == name)
    suggestion = (
        f"Added MCP **{added.name}** to the catalog (scope: {added.scope}).\n"
        f"- Source: {added.source_type} → {added.source_url or added.source_repo or '(no URL)'}\n"
        f"- Install command: `{added.install_command or '(fill in manually)'}`\n"
        f"- To actually install on your machine, run:\n"
        f"  ```\n  {added.install_command or '# no command — set install_command in the catalog'}\n  ```\n"
        f"- Catalog size: {catalog.count}"
    )
    return ChatMCPInstallResponse(
        detected_kind=kind,
        detected_name=name,
        detected_url=url,
        catalog_size=catalog.count,
        mcp=added,
        confirmation=suggestion,
        run_suggested_command=added.install_command,
    )


@router.post("/chat-intent", response_model=ChatIntentResponse)
def detect_chat_intent(req: ChatIntentRequest, user: str = Depends(get_current_user)) -> ChatIntentResponse:
    """Cheap rule-based intent detection so the SPA can short-circuit
    obvious MCP-add messages without spending an LLM call."""
    text = req.text.strip()
    lowered = text.lower()
    # 1. URL present?
    kind, name, url = detect_kind(text)
    if kind in ("github_url", "webpage_url"):
        return ChatIntentResponse(
            is_mcp_intent=True,
            confidence=0.95,
            reason=f"detected {kind} in message",
            extracted={"kind": kind, "name": name, "url": url},
        )
    # 2. Phrase-based detection
    triggers = [
        "add mcp", "add the mcp", "add this mcp",
        "install mcp", "install the mcp",
        "add an mcp", "register mcp",
        "i want the mcp", "i want the ",
        "add ", "install ", "register ",
    ]
    matched = [t for t in triggers if t in lowered]
    # Also detect if the message ends with "mcp" or "mcp server"
    ends_with_mcp = bool(re.search(r"\bmcp(\s+server)?\s*[\.\?!]?$", lowered))
    has_mcp_word = " mcp" in lowered or lowered.endswith("mcp") or " mcp server" in lowered
    if (matched and has_mcp_word) or ends_with_mcp:
        # Try to extract the name from common phrasings
        # Order matters: try the most-specific patterns first
        name = ""
        for pat in [
            r"add\s+the\s+(.+?)\s+mcp(?:\s+server)?\s*[\.\?!]?$",
            r"install\s+the\s+(.+?)\s+mcp(?:\s+server)?\s*[\.\?!]?$",
            r"register\s+(?:the\s+)?(.+?)\s+mcp(?:\s+server)?\s*[\.\?!]?$",
            r"i\s+want\s+(?:the\s+)?(.+?)\s+mcp(?:\s+server)?\s*[\.\?!]?$",
            r"add\s+an?\s+(.+?)\s+mcp(?:\s+server)?\s*[\.\?!]?$",
            r"(?:add|install|register)\s+(.+?)\s+mcp(?:\s+server)?\s*[\.\?!]?$",
        ]:
            mm = re.search(pat, lowered, flags=re.IGNORECASE)
            if mm:
                name = mm.group(1).strip()
                break
        if not name:
            # last resort: take the words before "mcp"
            name = re.sub(r"\s+mcp(\s+server)?\s*[\.\?!]?$", "", lowered).strip()
            # strip leading "add the / install the / register the / etc."
            name = re.sub(
                r"^(add|install|register|i\s+want)(?:\s+the|\s+an?)?\s+",
                "", name, flags=re.IGNORECASE,
            ).strip()
        # Clean to a slug
        name = re.sub(r"[^a-zA-Z0-9_\-]", "-", name).strip("-")
        name = re.sub(r"-+", "-", name)[:64]
        if not name:
            name = "unnamed-mcp"
        return ChatIntentResponse(
            is_mcp_intent=True,
            confidence=0.7,
            reason=f"matched trigger phrase(s): {', '.join(matched) or 'ends with mcp'}",
            extracted={"kind": "name", "name": name, "url": ""},
        )
    return ChatIntentResponse(
        is_mcp_intent=False,
        confidence=0.0,
        reason="no MCP-intent signals detected",
        extracted={},
    )
