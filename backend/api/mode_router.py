"""
Mode Router — multi-mode dispatch for Jarvis War Room chat.
Modes map to existing skills/workflows in the SOUL.md.
Project-aware: chat history saved to active project vault.

v1.2.1 — Intent-aware grill with 5 branches: Help, Proposal, Answering, Frustrated, Fallback.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.audit import log_action
from auth.dependencies import get_current_user
import json
import os
import random
import re
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path
import yaml

from core.config import KANBAN_DB
from api.project_vault import get_active_project, append_session, update_vault_context, get_sessions

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    mode: str = "standard"
    project: str = "default"
    workspace: str = ""
    agent: str = "jarvis"

# Mode definitions matching SOUL.md skills
MODES = {
    "standard":  {"name": "Standard",  "desc": "Tier-0..3 NL routing with cost gates", "tier_cap": 3, "exec": True},
    "grill":     {"name": "Grill Me",  "desc": "Founder grilling — challenge ideas before building", "tier_cap": 0, "exec": False, "style": "socratic"},
    "thinking":  {"name": "Thinking",  "desc": "Deep reasoning, no execution — think before building", "tier_cap": 0, "exec": False, "style": "analytical"},
    "spike":     {"name": "Spike",     "desc": "Throwaway experiments to validate ideas", "tier_cap": 1, "exec": True, "style": "experimental"},
    "plan":      {"name": "Plan",      "desc": "Write .hermes/plans/ only — no code execution", "tier_cap": 1, "exec": False, "style": "planning"},
    "tdd":       {"name": "TDD",       "desc": "RED-GREEN-REFACTOR — tests before code", "tier_cap": 2, "exec": True, "style": "test_first"},
    "council":   {"name": "Council",   "desc": "Boss+Manager+Scout parallel review", "tier_cap": 3, "exec": False, "style": "review"},
    "debug":     {"name": "Debug",     "desc": "4-phase root cause analysis", "tier_cap": 2, "exec": True, "style": "systematic"},
    "boss":      {"name": "Boss Review", "desc": "Claude Code --print architecture/security review", "tier_cap": 3, "exec": False, "style": "security"},
    "codex":     {"name": "Code",      "desc": "Codex CLI coding mode — implement, no planning", "tier_cap": 2, "exec": True, "style": "coding"},
}

# ─── Intent Analysis Helpers ──────────────────────────────

_KEYWORDS = {
    "greeting": ["hi", "hello", "hey", "hola", "good morning", "good evening", "yo", "sup"],
    "status":   ["status", "how is", "health", "alive", "running", "active", "fleet"],
    "build":    ["build", "create", "make", "add", "implement", "code", "write", "script"],
    "test":     ["test", "pytest", "assert", "verify", "check"],
    "fix":      ["fix", "repair", "broken", "bug", "error", "crash", "fail", "solve"],
    "deploy":   ["deploy", "serve", "public", "internet", "production", "live", "host", "domain"],
    "review":   ["review", "check", "audit", "security", "architecture", "risk", "validate"],
    "thinking": ["think", "reason", "analyze", "deep", "understand", "consider", "assess"],
    "plan":     ["plan", "strategy", "roadmap", "schedule", "steps", "tasks", "phase"],
    "debug":    ["debug", "trace", "root cause", "investigate", "error", "stack trace", "log"],
    "council":  ["council", "review", "boss", "judge", "verdict", "approve"],
    "grill":    ["grill", "challenge", "question", "challenge idea", "founder", "should we"],
    "spike":    ["spike", "experiment", "prototype", "validate", "throwaway", "quick test"],
    "ship":     ["ship", "release", "launch", "going live", "make public"],
}

_SENTIMENT = {
    "urgent":    ["urgent", "now", "quickly", "asap", "immediately", "emergency"],
    "frustrated": ["not working", "broken", "does not work", "wtf", "disaster", "why"],
    "doubtful":  ["but", "however", "not sure", "maybe", "perhaps", "what if", "worried"],
}

def _parse_intent(msg: str) -> dict:
    """Return detected intent attributes from a user message."""
    m = msg.lower()
    detected = set()
    for label, words in _KEYWORDS.items():
        if any(w in m for w in words):
            detected.add(label)
    sentiment = set()
    for label, words in _SENTIMENT.items():
        if any(w in m for w in words):
            sentiment.add(label)
    return {"labels": sorted(detected), "sentiment": sorted(sentiment), "length": len(msg), "has_question": "?" in msg}

def _smart_ack(msg: str, intent: dict, mode_name: str) -> str:
    """Build a personalized first sentence acknowledging the user's input."""
    labels = intent["labels"]
    sentim = intent["sentiment"]

    if "greeting" in labels:
        return random.choice([
            "Welcome back.", "Good to hear from you.", "Good to see you.",
            "Glad you're here.", "At your service.", "Listening.",
        ])
    if "status" in labels:
        return "Checking fleet and system health."
    if "build" in labels:
        return "Looks like you're starting with architecture." if "design" in labels or "architecture" in msg.lower() else "Got it — you're looking to build."
    if "fix" in labels or "debug" in labels:
        return "Let's get to the bottom of this." if "frustrated" in sentim or "urgent" in sentim else "I'll help you trace and fix this systematically."
    if "review" in labels or "council" in labels:
        return "Reviewing architecture and security posture."
    if "plan" in labels:
        return "Planning phase. I will break this down."
    if "spike" in labels:
        return "Quick validation run — low risk, high signal."
    if "deploy" in labels or "ship" in labels:
        return "Production readiness check before we go live."
    if "thinking" in labels:
        return "Let's reason through the implications."
    if intent["has_question"]:
        return "Good question."
    return "Noted."

# ─── LLM-backed conversation layer ─────────────────────────

def _env_value(key: str) -> str:
    if os.environ.get(key):
        return os.environ.get(key, "")
    env_path = os.path.expanduser("~/.hermes/profiles/jarvis/.env")
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k == key:
                    return v.strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""

def _safe_agent_slug(agent: str) -> str:
    slug = (agent or "jarvis").strip().lower()
    slug = re.sub(r"[^a-z0-9_-]", "", slug)
    return slug if slug.startswith("jarvis") else "jarvis"


def _load_agent_profile(agent: str) -> dict:
    slug = _safe_agent_slug(agent)
    profile_dir = Path("~/.hermes/profiles").expanduser() / slug
    cfg_path = profile_dir / "config.yaml"
    soul_path = profile_dir / "SOUL.md"
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
        except Exception:
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    profile = cfg.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    model_cfg = cfg.get("model") or {}
    if isinstance(model_cfg, str):
        model_cfg = {"default": model_cfg}
    elif not isinstance(model_cfg, dict):
        model_cfg = {}
    soul_excerpt = ""
    if soul_path.exists():
        try:
            soul_excerpt = soul_path.read_text(errors="ignore")[:3500]
        except Exception:
            soul_excerpt = ""
    return {
        "slug": slug,
        "name": profile.get("name") or slug,
        "description": profile.get("description") or "Jarvis Company OS agent",
        "model": model_cfg.get("default") or model_cfg.get("model") or "kimi-k2.6",
        "provider": model_cfg.get("provider") or "ollama-cloud",
        "base_url": model_cfg.get("base_url") or "",
        "api_key_env": model_cfg.get("api_key_env") or "",
        "soul_excerpt": soul_excerpt,
    }


def _agent_provider_candidates(agent_profile: dict) -> list:
    """Return a list of provider candidates in priority order.

    Each candidate is a tuple:
        ("http", base_url, api_key, model) — HTTP chat-completions endpoint
        ("cli",  cli_name, model)            — local CLI binary (codex, claude)

    The CLI candidates are added as a fallback when no HTTP provider has a
    valid API key. The user opts in via JARVIS_CLI_PROVIDER:
        auto  — use codex if on PATH, else claude (default)
        codex — only codex
        claude — only claude
        none  — never fall back to CLI
    """
    candidates: list = []
    provider = agent_profile.get("provider", "")
    model = agent_profile.get("model") or "kimi-k2.6"
    base_url = agent_profile.get("base_url") or ""
    api_key_env = agent_profile.get("api_key_env") or ""

    if provider in ("ollama-cloud", "ollama", ""):
        key = _env_value(api_key_env) if api_key_env else _env_value("OLLAMA_API_KEY")
        base = base_url or _env_value("OLLAMA_BASE_URL") or "https://ollama.com/v1"
        if key:
            candidates.append(("http", base, key, model))
    elif provider in ("openrouter", "openrouter.ai"):
        key = _env_value(api_key_env) if api_key_env else _env_value("OPENROUTER_API_KEY")
        base = base_url or "https://openrouter.ai/api/v1"
        if key:
            candidates.append(("http", base, key, model))

    ollama_key = _env_value("OLLAMA_API_KEY")
    ollama_base = _env_value("OLLAMA_BASE_URL") or "https://ollama.com/v1"
    if ollama_key and ("http", ollama_base, ollama_key, "kimi-k2.6") not in candidates:
        candidates.append(("http", ollama_base, ollama_key, "kimi-k2.6"))
    openrouter_key = _env_value("OPENROUTER_API_KEY")
    if openrouter_key:
        candidates.append(("http", "https://openrouter.ai/api/v1", openrouter_key, "anthropic/claude-sonnet-4"))
        candidates.append(("http", "https://openrouter.ai/api/v1", openrouter_key, "openai/gpt-4o"))

    # CLI fallback: only when the user opted in (default = auto)
    if not any(c[0] == "http" for c in candidates):
        cli_pref = (_env_value("JARVIS_CLI_PROVIDER") or "auto").strip().lower()
        if cli_pref not in ("none", "off", "0"):
            have_codex = _which("codex")
            have_claude = _which("claude")
            chosen: list[tuple[str, str]] = []
            if cli_pref == "codex" and have_codex:
                chosen.append(("codex", have_codex))
            elif cli_pref == "claude" and have_claude:
                chosen.append(("claude", have_claude))
            elif cli_pref == "auto":
                if have_codex:
                    chosen.append(("codex", have_codex))
                if have_claude:
                    chosen.append(("claude", have_claude))
            for cli_name, cli_path in chosen:
                candidates.append(("cli", cli_name, cli_path))
    return candidates


def _which(binary: str) -> str:
    """Return absolute path to `binary` if it exists on PATH, else ''.

    Uses shutil.which (stdlib, no shell), bounded, and Windows-safe.
    """
    import shutil
    found = shutil.which(binary)
    return found or ""


def _build_cli_prompt(messages: list) -> str:
    """Flatten an OpenAI-style messages array into a deterministic transcript.

    Sections are clearly delimited so the CLI agent (codex/claude) can parse
    them. System + project context go first, then history, then the user turn.
    """
    sys_msgs = [m["content"] for m in messages if m.get("role") == "system"]
    hist_msgs = [m for m in messages if m.get("role") in ("user", "assistant") and m is not messages[-1]]
    last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

    parts: list[str] = []
    if sys_msgs:
        parts.append("=== SYSTEM INSTRUCTIONS ===\n" + "\n\n".join(sys_msgs).strip())
    if hist_msgs:
        hist_lines = []
        for m in hist_msgs[-10:]:
            role = m.get("role", "user").upper()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            # Escape triple-backticks so the CLI doesn't get confused by code blocks
            content = content.replace("```", "ʼʼʼ")
            hist_lines.append(f"[{role}]\n{content[:1500]}")
        if hist_lines:
            parts.append("=== CHAT HISTORY (most recent last) ===\n" + "\n\n".join(hist_lines))
    if last_user:
        parts.append("=== USER REQUEST (respond to this) ===\n" + last_user.strip().replace("```", "ʼʼʼ"))
    parts.append("=== END ===\nRespond directly to the user. Be concise.")
    return "\n\n".join(parts)


def _cli_response(cli_name: str, cli_path: str, messages: list, timeout: int = 90) -> str | None:
    """Shell out to a local CLI (codex or claude) and return its text output.

    Uses subprocess.run with a hard timeout, captures stdout/stderr, no shell.
    Returns None on any error so the caller can fall through to templates.
    """
    import subprocess
    prompt = _build_cli_prompt(messages)
    if not prompt.strip():
        return None
    # Cap the prompt size to keep CLI invocation bounded.
    if len(prompt) > 30000:
        prompt = prompt[:30000] + "\n\n[prompt truncated to 30000 chars]"

    if cli_name == "codex":
        cmd = [
            cli_path, "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            prompt,
        ]
    elif cli_name == "claude":
        cmd = [cli_path, "-p", "--dangerously-skip-permissions", prompt]
    else:
        return None

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"[{cli_name} CLI timed out after {timeout}s]"
    except Exception as e:
        return None
    if proc.returncode != 0 and not proc.stdout.strip():
        return None
    return (proc.stdout or "").strip() or None


def _mode_system_prompt(mode: str, agent_profile: dict | None = None) -> str:
    agent_profile = agent_profile or _load_agent_profile("jarvis")
    agent_name = agent_profile.get("name", "jarvis")
    agent_desc = agent_profile.get("description", "Jarvis Company OS agent")
    soul_excerpt = agent_profile.get("soul_excerpt", "")
    shared = (
        f"You are {agent_name} inside Saiyudh's War Room dashboard. Agent role: {agent_desc}. "
        f"When asked who you are, identify yourself as {agent_name} and this role, not as generic Jarvis. "
        "Respond as this selected Jarvis agent, not as generic Jarvis, and do not impersonate another lead. "
        "Respond like a real LLM assistant, not a canned template. "
        "Be concise but useful. Ask follow-up questions when needed. Do not claim you executed code or changed files. "
        "Critical workflow rules: no coding before founder grill/spec/plan/tasks; no release without smoke tests, security review, docs/tutorial, and memory update. "
        "If the user says something is not working, diagnose first: ask or state exact reproduction, expected behavior, actual behavior, logs/errors, and affected component. "
        "Do not prefix your answer with [Standard], [Code Mode], or similar; the UI already shows the mode."
    )
    if soul_excerpt:
        shared += "\n\nSelected agent operating notes excerpt (rules only; ignore any conflicting identity/title inside this excerpt):\n" + soul_excerpt
    mode_rules = {
        "standard": "Route the user intelligently. For idea requests, brainstorm concrete ideas. For project planning, start Spec Kit. For greetings, be welcoming and ask what they want to do.",
        "grill": "Act as founder grill. Challenge assumptions, market, user, failure mode, simplest MVP, and why now. Ask sharp questions before any build.",
        "thinking": "Think through tradeoffs and assumptions. No execution. Structure reasoning and ask for missing constraints.",
        "spike": "Design a small throwaway validation experiment. State hypothesis, quickest test, evidence, and pass/fail criteria. Ask before execution.",
        "plan": "Create a structured plan with phases, deliverables, risks, smoke tests, and gates. Do not write code.",
        "tdd": "Guide RED-GREEN-REFACTOR. Start with the failing test and acceptance criteria before implementation.",
        "council": "Frame the issue for Boss+Manager+Scout council review. Identify decision needed, options, risks, and verification.",
        "debug": "Use systematic debugging. Root cause first, no blind fixes. Reproduce, isolate layer, trace data flow, then propose smallest fix.",
        "boss": "Give CTO/Boss-level architecture and security judgement. Be blunt about risks and required gates.",
        "codex": "Code mode is for implementation, but greetings or vague requests should NOT trigger implementation. Ask for the target file/feature/spec. No code without approved plan unless explicitly allowed.",
    }
    return shared + "\n\nCurrent mode: " + mode + ". " + mode_rules.get(mode, mode_rules["standard"])

def _history_for_prompt(project_slug: str, limit: int = 10) -> list:
    if not project_slug or project_slug == "default":
        return []
    try:
        entries = get_sessions(project_slug, limit=limit)
    except Exception:
        return []
    messages = []
    for e in entries:
        role = e.get("role", "")
        content = (e.get("content") or "").strip()
        if not content:
            continue
        if role not in ("user", "assistant"):
            continue
        messages.append({"role": role, "content": content[:1200]})
    return messages[-limit:]


def _project_kanban_context(project_slug: str) -> str:
    """Read kanban tasks for the given project and return a compact summary string."""
    if not project_slug or project_slug == 'default':
        return ''
    try:
        conn = sqlite3.connect(str(KANBAN_DB), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, title, status, assignee, priority, body FROM tasks WHERE project = ? AND status NOT IN ('archived','cancelled') ORDER BY priority DESC, updated_at DESC LIMIT 20", (project_slug,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        if not rows:
            return f"Project '{project_slug}': no active kanban tasks."
        lines = [f"Project '{project_slug}' kanban tasks:"]
        for r in rows:
            body = (r.get('body') or '').strip()
            body_suffix = f" | body={body[:140]}" if body else ''
            lines.append(f"  - id=t_{r['id']} | {r['title']} | status={r['status']} | assignee={r['assignee']} | priority={r['priority']}{body_suffix}")
        return '\n'.join(lines)
    except Exception:
        return ''


def _project_context_packet(project_slug: str) -> str:
    """Build a strong selected-project context packet for LLM prompts."""
    if not project_slug or project_slug == 'default':
        return ''
    lines = [
        "ACTIVE PROJECT CONTEXT — treat this as authoritative:",
        f"- Selected project slug: {project_slug}",
        "- This is an EXISTING selected project/repo unless the user explicitly says they are starting a different new project.",
        "- If the user proposes a feature or research direction, frame it as a scope change/module inside the selected project; do not ask whether it is greenfield.",
    ]
    try:
        ctx = get_vault_context(project_slug) or {}
    except Exception:
        ctx = {}
    if ctx:
        lines.append(f"- Project name: {ctx.get('name') or project_slug}")
        if ctx.get('repo_url'):
            lines.append(f"- Repo URL: {ctx.get('repo_url')}")
        if ctx.get('repo_path'):
            lines.append(f"- Repo path: {ctx.get('repo_path')}")
        if ctx.get('status'):
            lines.append(f"- Project status: {ctx.get('status')}")
        if ctx.get('mode'):
            lines.append(f"- Preferred mode: {ctx.get('mode')}")
    kanban = _project_kanban_context(project_slug)
    if kanban:
        lines.append(kanban)
    vault_dir = Path.home() / '.hermes' / 'memory' / 'projects' / project_slug
    decisions_path = vault_dir / 'decisions.md'
    if decisions_path.exists():
        try:
            decisions = decisions_path.read_text(errors='ignore').strip()
            useful = [ln for ln in decisions.splitlines() if ln.strip()]
            if len(useful) > 1:
                lines.append('Project decision log excerpt:')
                lines.append(decisions[:1800])
        except Exception:
            pass
    return '\n'.join(lines)
def _chat_completion_request(base_url: str, api_key: str, model: str, messages: list, timeout: int = 45) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 700,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
            "HTTP-Referer": "http://43.131.26.109:8503/war-room",
            "X-Title": "Jarvis War Room Dashboard",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()

def _llm_response(mode: str, msg: str, project_slug: str, agent: str = "jarvis") -> dict | None:
    """Return an LLM-backed chat response. Falls back to template handlers on any provider error."""
    agent_profile = _load_agent_profile(agent)
    system = _mode_system_prompt(mode, agent_profile)
    history = _history_for_prompt(project_slug, limit=10)
    ctx_str = _project_context_packet(project_slug)
    enriched_system = system
    if ctx_str:
        enriched_system += "\n\n" + ctx_str
    messages = [{"role": "system", "content": enriched_system}]
    messages.extend(history)
    if not history or history[-1].get("content") != msg:
        messages.append({"role": "user", "content": msg})

    providers = _agent_provider_candidates(agent_profile)

    for cand in providers:
        kind = cand[0]
        try:
            if kind == "http":
                _, base, key, model = cand
                text = _chat_completion_request(base, key, model, messages)
            elif kind == "cli":
                _, cli_name, cli_path = cand
                text = _cli_response(cli_name, cli_path, messages)
            else:
                continue
            if text:
                intent = _parse_intent(msg)
                tier = _infer_tier(msg, intent)
                if mode in ("grill", "thinking", "plan"):
                    tier = 0 if mode in ("grill", "thinking") else 1
                elif mode in ("council", "boss"):
                    tier = 3
                elif mode in ("debug", "tdd", "codex"):
                    tier = max(tier, 2)
                elif mode == "spike":
                    tier = max(tier, 1)
                provider_model = model if kind == "http" else f"{cli_name}-cli"
                return {
                    "mode": mode,
                    "tier": tier,
                    "response": text,
                    "cost": 0.0,
                    "confirmation_required": tier >= 2 and mode in ("spike", "tdd", "debug", "codex"),
                    "council_required": tier >= 3,
                    "can_exec": MODES.get(mode, MODES["standard"])["exec"],
                    "llm": True,
                    "provider_type": kind,
                    "provider_model": provider_model,
                    "agent": agent_profile.get("name", agent),
                }
        except Exception:
            continue
    return None

# ─── Standard / Tiered ────────────────────────────────────

def _standard_response(msg: str) -> dict:
    intent = _parse_intent(msg)
    ack = _smart_ack(msg, intent, "Standard")
    labels = set(intent["labels"])
    tier = _infer_tier(msg, intent)
    m = msg.lower().strip()

    planning_phrases = [
        "new project", "plan a project", "plan project", "start a project",
        "help me plan", "project idea", "new app", "new product",
    ]
    wants_project_planning = "plan" in labels and any(p in m for p in planning_phrases)

    if "greeting" in labels and len(m.split()) <= 3:
        body = (
            f"{ack} I can help you plan a project, debug a broken feature, run a founder grill, "
            "or inspect the dashboard. What are we working on?"
        )
    elif wants_project_planning:
        body = (
            "Project planning mode. Before we build anything, we follow Spec Kit: founder grill → spec.md → "
            "plan.md → tasks.md → smoke tests → security review → tutorial.\n\n"
            "Tell me three things:\n"
            "1. What is the project idea in one sentence?\n"
            "2. Who is the user and what pain are we solving?\n"
            "3. Is this a web app, bot, automation, ML project, or something else?\n\n"
            "If you want pressure-testing first, switch to Grill Mode. If you want the structured checklist, switch to Plan Mode."
        )
        tier = 0
    elif "fix" in labels or "debug" in labels or "frustrated" in intent["sentiment"]:
        body = (
            "I’ll debug it systematically — no blind fixes.\n\n"
            "First I need the exact symptom:\n"
            "1. What did you click/type?\n"
            "2. What did you expect?\n"
            "3. What actually happened?\n"
            "4. Is there an error message or console output?\n\n"
            "Once I can reproduce it, I’ll isolate frontend vs API vs data/state and then propose the smallest fix."
        )
        tier = max(tier, 2)
    elif "build" in labels:
        body = (
            "You’re asking to build something. I won’t jump straight to code.\n\n"
            "Jarvis workflow is: Founder Grill first, then spec, then plan, then tasks.\n"
            "Start by telling me: what are we building, who is it for, and what proves it worked?"
        )
        tier = max(tier, 1)
    elif "status" in labels:
        body = f"{ack} For live system state, switch to Dashboard view. The current chat project is scoped to the selected project."
    elif "plan" in labels:
        body = (
            "Planning phase. I can turn this into phases, risks, smoke tests, and release gates.\n\n"
            "Give me the target outcome, constraints, and deadline. If this is a new project, include the one-sentence idea and target user."
        )
        tier = 0
    else:
        body = (
            f"{ack} I’m listening. If this is about a project, give me the goal and I’ll route it into Grill, Plan, Debug, Council, or Code mode."
        )

    cost = round(random.uniform(0.1 * tier, 0.5 * tier + 0.5), 2) if tier > 0 else 0.0
    return {
        "mode": "standard",
        "tier": tier,
        "response": f"[Standard] {body}",
        "cost": cost,
        "confirmation_required": tier >= 2,
        "council_required": tier >= 3,
        "can_exec": True,
    }

# ─── Grill — 5 intent branches ─────────────────────────────
# Branch priority: A(help) > B(proposal) > C(answer) > D(frustrated) > E(status/greeting) > F(fallback)

def _grill_response(msg: str, user: str) -> dict:
    """
    Intent-aware founder grill — 5 branches, no session memory.
    Only the current message is used to determine intent.

    Branch A: Help/Exploration — user asking "what can I do"
    Branch B: Proposal — user mentioning build/create/make/etc + noun
    Branch C: User answering — short statement, no question, no build word
    Branch D: Frustrated/Stuck — user expressing confusion/stuck
    Branch E: Status/Greeting — status check or greeting
    Branch F: Fallback — rotating generic founder questions
    """
    m = msg.lower().strip()

    # ── Detect intent flags ──────────────────────────────────
    is_proposal   = any(w in m for w in ["build","create","make","add","implement","write","design","ship","launch"])
    is_question   = "?" in msg
    is_short      = len(msg.split()) <= 6
    is_frustrated = any(p in m for p in [
        "no idea", "dont know", "don't know", "whatever",
        "aaaa", "argh", "ugh", "stuck", "not working",
        "not sure what", "idk", "skip", "give up",
    ])
    is_help       = any(p in m for p in [
        "what can i do", "what should i", "what do i do",
        "what's possible", "what are my options", "suggest",
        "recommend", "name one thing", "give me an idea",
        "what now", "what next", "what else",
    ])
    is_status     = any(p in m for p in [
        "status", "how is", "how's", "progress", "where are we",
    ])
    is_greeting   = m in ("hi","hello","hey","yo","hola","good morning","sup","greetings")

    # Try to extract noun from proposal
    noun = None
    if is_proposal:
        for w in ["build","create","make","add","implement","write","design","ship","launch"]:
            match = re.search(rf'{w}\s+(?:a|an|the)?\s*"?\'?([^\"\'?.,:;]+)', msg, re.IGNORECASE)
            if match:
                noun = match.group(1).strip()
                break

    # ── Branch A: Help / Exploration ─────────────────────────
    if is_help and not is_proposal:
        response = (
            "[Grill Mode] Here's what you can do right now — pick one:\n\n"
            "  1. Propose a feature — I'll challenge it like a VC before you build.\n"
            "  2. Describe a problem — I'll reframe it and find the real question.\n"
            "  3. Run a 30-min spike — throwaway experiment, validate or kill the idea.\n"
            "  4. Switch to Thinking — reason through trade-offs before deciding.\n"
            "  5. Summon the Council — Boss + Manager review for high-stakes moves.\n\n"
            "What do you want to work on?"
        )
        return {
            "mode": "grill", "tier": 0, "response": response,
            "cost": 0.0, "confirmation_required": False,
            "council_required": False, "can_exec": False,
        }

    # ── Branch B: Proposal detected ──────────────────────────
    if is_proposal and noun:
        questions = [
            f"Who is the user for {noun}?",
            f"What makes {noun} better than status quo?",
            f"What's the simplest version of {noun}?",
            f"What does failure look like for {noun}?",
            f"Can you describe {noun} in one sentence?",
            f"Why build {noun} right now?",
            f"What are you assuming about {noun}?",
            f"How will you know {noun} is working?",
        ]
        pick = random.sample(questions, 3)
        return {
            "mode": "grill", "tier": 0, "response": (
                f"[Grill Mode] Before you build '{noun}':\n\n"
                + "\n".join(f"  {i+1}. {q}" for i, q in enumerate(pick))
                + f"\n\nWe'll revisit {noun} once you've answered."
            ),
            "cost": 0.0, "confirmation_required": False,
            "council_required": False, "can_exec": False,
            "questions": pick,
        }

    # ── Branch C: User answering ──────────────────────────────
    # Must come AFTER E check, but E is already checked above (is_greeting is exact match)
    if not is_question and not is_proposal and not is_frustrated and is_short and not is_greeting and not is_status:
        answers = [
            "Got it. Next question: what's the actual constraint here — time, money, or skill?",
            "Fair enough. Now ask yourself: would a user pay for this or just use it?",
            "Noted. If this fails in 2 weeks, what will you wish you'd done differently today?",
            "Understood. One word: do you have an existing competitor, or is this a new market?",
            "OK. How fast can you test this assumption? What's the fastest path to evidence?",
        ]
        response = random.choice(answers)
        return {
            "mode": "grill", "tier": 0, "response": f"[Grill Mode] {response}",
            "cost": 0.0, "confirmation_required": False,
            "council_required": False, "can_exec": False,
        }

    # ── Branch D: Frustrated / Stuck ─────────────────────────
    if is_frustrated:
        if "help" in m or "what can i do" in m:
            response = (
                "[Grill Mode] You're stuck — that's normal before a breakthrough.\n\n"
                "Here's what usually helps:\n"
                "  • Run a 30-min spike to validate one small piece\n"
                "  • Switch to Thinking mode and break it down\n"
                "  • Describe the problem out loud — the real problem often hides in the framing\n\n"
                "Which do you want to try?"
            )
        else:
            responses = [
                "[Grill Mode] OK, you sound stuck. Here's the move: pick the single most important next step — just one — and spend 30 minutes on it. Nothing else. What is that step?",
                "[Grill Mode] You've hit the hard part. The answer is usually to do less, not more. Can you name the one thing that matters most right now?",
                "[Grill Mode] Frustration means you're close. Go sideways — describe the problem to me as if I know nothing. The act of explaining often reveals the path.",
            ]
            response = random.choice(responses)
        return {
            "mode": "grill", "tier": 0, "response": response,
            "cost": 0.0, "confirmation_required": False,
            "council_required": False, "can_exec": False,
        }

    # ── Branch E: Status / Greeting ───────────────────────────
    if is_status:
        return {
            "mode": "grill", "tier": 0, "response": (
                "[Grill Mode] You're in founder grill mode — I challenge ideas before they're built.\n\n"
                "Tell me what you're working on and I'll ask the hard questions."
            ),
            "cost": 0.0, "confirmation_required": False,
            "council_required": False, "can_exec": False,
        }
    if is_greeting:
        return {
            "mode": "grill", "tier": 0, "response": (
                "[Grill Mode] Hey. What's the idea you want to pressure-test today?"
            ),
            "cost": 0.0, "confirmation_required": False,
            "council_required": False, "can_exec": False,
        }

    # ── Branch F: Fallback ────────────────────────────────────
    pool = [
        "What problem are you trying to solve?",
        "Who is the user? Be specific.",
        "What makes this better than status quo?",
        "What's the simplest version?",
        "What does failure look like?",
        "Can you describe this in one sentence?",
        "Why build this right now?",
        "What are you assuming?",
        "What's the smallest thing you could ship to test this?",
        "What would have to be true for this to work?",
        "Who loses if this succeeds?",
        "What's the second-order effect?",
        "Is this vision or feature? Which matters more right now?",
    ]
    pick = random.sample(pool, 3)
    topic = noun or "your idea"
    return {
        "mode": "grill", "tier": 0, "response": (
            "[Grill Mode] Before committing to " + topic + ":\n\n"
            + "\n".join(f"  {i+1}. {q}" for i, q in enumerate(pick))
            + "\n\nWe'll revisit " + topic + " once you've answered."
        ),
        "cost": 0.0, "confirmation_required": False,
        "council_required": False, "can_exec": False,
        "questions": pick,
    }

# ─── Thinking ─────────────────────────────────────────────

def _thinking_response(msg: str) -> dict:
    m = msg.lower()
    topic = msg[:60].rstrip(',.;')

    if "why" in m:
        response = (
            f"[Thinking Mode] Let's interrogate the reasoning behind '{topic}':\n\n"
            "1.  What's the underlying need that led to this?\n"
            "2.  What constraints are you operating under?\n"
            "3.  What assumptions are baked in that you haven't questioned?\n\n"
            "Once you articulate these, the solution space will open up."
        )
    elif "how" in m:
        response = (
            f"[Thinking Mode] You're asking how — that's the controller, not the model.\n\n"
            f"Before I answer for '{topic}', I want to understand:\n"
            "1.  What does success look like in concrete terms?\n"
            "2.  What resources do you actually have?\n"
            "3.  What's the constraint that matters most to you?\n\n"
            "Answer those and I'll map the path."
        )
    else:
        response = (
            f"[Thinking Mode] Let me reason through '{topic}':\n\n"
            "1.  Decompose the request into atomic concerns.\n"
            "2.  Identify constraints and invariants.\n"
            "3.  Surface hidden assumptions.\n"
            "4.  Map the trade-off space.\n\n"
            "Before any action, what is your definition of done for this?"
        )

    return {
        "mode": "thinking",
        "tier": 0,
        "response": response,
        "cost": 0.0,
        "confirmation_required": False,
        "council_required": False,
        "can_exec": False,
    }

# ─── Spike ────────────────────────────────────────────────

def _spike_response(msg: str) -> dict:
    intent = _parse_intent(msg)
    ack = _smart_ack(msg, intent, "Spike")
    topic = msg[:70].rstrip(',.;')

    response = (
        f"[Spike Mode] {ack}\n\n"
        f"I'll run a 30-min throwaway experiment to validate: '{topic}'\n\n"
        "Constraints:\n"
        "  • No production code changed.\n"
        "  • Output goes to ~/.hermes/state/spikes/<timestamp>/\n"
        "  • Result is a PASS/FAIL with evidence.\n\n"
        "Do you want to proceed?"
    )

    return {
        "mode": "spike",
        "tier": 1,
        "response": response,
        "cost": 0.5,
        "confirmation_required": True,
        "council_required": False,
        "can_exec": True,
        "output_dir": "~/.hermes/state/spikes/",
    }

# ─── Plan ─────────────────────────────────────────────────

def _plan_response(msg: str) -> dict:
    intent = _parse_intent(msg)
    ack = _smart_ack(msg, intent, "Plan")
    topic = msg[:70].rstrip(',.;')

    response = (
        f"[Plan Mode] {ack}\n\n"
        f"Plan target: '{topic}'\n\n"
        "Here is the scaffold I will fill out:\n"
        "  1. Phase breakdown with deliverables\n"
        "  2. Task checklist with owners\n"
        "  3. Risk analysis and mitigations\n"
        "  4. Smoke test criteria for each phase\n"
        "  5. Rollback triggers and checkpoint definition\n\n"
        "No code will execute until the plan is reviewed and approved.\n"
        "Output will be written to ~/.hermes/plans/<slug>.md"
    )

    return {
        "mode": "plan",
        "tier": 1,
        "response": response,
        "cost": 0.3,
        "confirmation_required": False,
        "council_required": False,
        "can_exec": False,
        "output_dir": ".hermes/plans/",
    }

# ─── TDD ─────────────────────────────────────────────────

def _tdd_response(msg: str) -> dict:
    intent = _parse_intent(msg)
    ack = _smart_ack(msg, intent, "TDD")
    topic = msg[:70].rstrip(',.;')

    response = (
        f"[TDD Mode] {ack}\n\n"
        f"Target: '{topic}'\n\n"
        "RED → GREEN → REFACTOR loop:\n"
        "  1. Write a failing test that describes the desired behavior.\n"
        "  2. Write the minimal code that makes the test pass.\n"
        "  3. Refactor with all tests green.\n"
        "  4. Repeat until the spec is fully covered.\n\n"
        "No code ships without a matching test.\n"
        "Confirm to begin the RED phase."
    )

    return {
        "mode": "tdd",
        "tier": 2,
        "response": response,
        "cost": 1.2,
        "confirmation_required": True,
        "council_required": False,
        "can_exec": True,
    }

# ─── Council ──────────────────────────────────────────────

def _council_response(msg: str) -> dict:
    m = msg.lower()
    topic = msg[:70].rstrip(',.;')

    if "security" in m or "audit" in m:
        focus = "Security + Architecture"
    elif "performance" in m or "scaling" in m or "latency" in m:
        focus = "Performance + Scalability"
    else:
        focus = "Architecture + Tooling + Go/No-Go"

    response = (
        f"[Council Mode] Summoning full council for: '{topic}'\n\n"
        "Review bench:\n"
        "  • Boss (Claude Sonnet 4.6)\n"
        "  • Manager (Codex GPT-5.5)\n"
        "  • Scout (DeepSeek / GLM)\n"
        "  • Security Lead (Agent-1)\n\n"
        f"Focus: {focus}\n"
        "Deliverables:\n"
        "  1. Architecture assessment with alternatives\n"
        "  2. Security analysis and threat model\n"
        "  3. Cost / risk / timeline estimate\n"
        "  4. Go/No-Go verdict with conditions\n\n"
        "This is a high-cost gate. Confirm to proceed."
    )

    return {
        "mode": "council",
        "tier": 3,
        "response": response,
        "cost": 2.5,
        "confirmation_required": True,
        "council_required": True,
        "can_exec": False,
    }

# ─── Debug ───────────────────────────────────────────────

def _debug_response(msg: str) -> dict:
    m = msg.lower()
    topic = msg[:70].rstrip(',.;')

    has_error = any(w in m for w in ["error", "exception", "traceback", "crash", "fail", "assertion", "timeout"])

    if has_error:
        phase_1 = "Phase 1: Isolate — reproduce and capture the exact error + stack trace."
    else:
        phase_1 = "Phase 1: Understand — reproduce the symptom in minimal form."

    response = (
        f"[Debug Mode] 4-phase root cause analysis for: '{topic}'\n\n"
        f"{phase_1}\n"
        "Phase 2: Hypothesize — list the 3 most likely root causes.\n"
        "Phase 3: Experiment — test the smallest hypothesis first.\n"
        "Phase 4: Fix + regression — apply fix, verify with new test.\n\n"
        "No blind fixes.\n"
    )

    if has_error:
        response += "\nPlease paste the full error message or stack trace so I can start Phase 1."

    return {
        "mode": "debug",
        "tier": 2,
        "response": response,
        "cost": 1.0,
        "confirmation_required": True,
        "council_required": False,
        "can_exec": True,
    }

# ─── Boss Review ──────────────────────────────────────────

def _boss_response(msg: str) -> dict:
    m = msg.lower()
    topic = msg[:70].rstrip(',.;')

    if "security" in m or "audit" in m or "vulnerability" in m:
        review_type = "Security Review"
    elif "architecture" in m or "refactor" in m or "design" in m:
        review_type = "Architecture Review"
    elif "performance" in m or "scaling" in m:
        review_type = "Performance + Architecture Review"
    else:
        review_type = "Comprehensive Security + Architecture Review"

    response = (
        f"[Boss Review] Claude Sonnet 4.6 will perform: {review_type}\n\n"
        f"Target: '{topic}'\n\n"
        "Review scope:\n"
        "  1. Data flow security — where does sensitive data live?\n"
        "  2. OWASP AI-agent risks — prompt injection, data exfiltration\n"
        "  3. Architecture soundness — coupling, boundaries, failure modes\n"
        "  4. Cost/risk assessment — token budget, blast radius, rollback plan\n\n"
        "No code executes until Boss signs off.\n"
        "Confirm to summon Boss."
    )

    return {
        "mode": "boss",
        "tier": 3,
        "response": response,
        "cost": 2.0,
        "confirmation_required": True,
        "council_required": True,
        "can_exec": False,
    }

# ─── Code Mode ────────────────────────────────────────────

def _codex_response(msg: str) -> dict:
    intent = _parse_intent(msg)
    ack = _smart_ack(msg, intent, "Code")
    topic = msg[:70].rstrip(',.;')

    response = (
        f"[Code Mode] {ack}\n\n"
        f"I will implement: '{topic}' via Codex GPT-5.5\n\n"
        "Rules:\n"
        "  • Planning is retroactive — code first, plan after if diff > 100 lines.\n"
        "  • Every commit must pass existing tests.\n"
        "  • If a file is touched, I must update the corresponding test.\n"
        "  • No file changes without logging to audit trail.\n\n"
        "Confirm to dispatch Codex."
    )

    return {
        "mode": "codex",
        "tier": 2,
        "response": response,
        "cost": 1.5,
        "confirmation_required": True,
        "council_required": False,
        "can_exec": True,
    }

# ─── Tier inference ───────────────────────────────────────

def _infer_tier(msg: str, intent: dict | None = None) -> int:
    m = msg.lower()
    labels = set(intent["labels"]) if intent else set()

    if any(w in m for w in ["show", "list", "status", "what", "who", "where"]):
        return 0
    if any(w in m for w in ["deploy", "serve", "internet", "public", "production", "live", "host"]):
        return 3
    if "council" in labels or "review" in labels:
        return 3
    if "boss" in labels:
        return 3
    if any(w in m for w in ["build", "create", "make", "add", "implement", "code", "test", "debug"]):
        return 2
    if "fix" in labels or "debug" in labels:
        return 2
    return 1


# ─── FastAPI routes ────────────────────────────────────────

@router.get("/modes")
def list_modes():
    return {
        "modes": [
            {"id": k, "name": v["name"], "desc": v["desc"], "exec": v["exec"], "tier_cap": v["tier_cap"], "style": v.get("style", "")}
            for k, v in MODES.items()
        ],
        "default": "standard"
    }

@router.post("/chat")
def chat_mode_dispatch(req: ChatRequest, user: str = Depends(get_current_user)):
    # ── Boss Item 4: Company OS ACL gate (Gap #3 closure) ─────────
    # Build a synthetic envelope, run through authorize_and_persist.
    # On deny: return the same {delivered:false, allowed:false, ...} shape
    # /messages uses, without dispatching to LLM.
    try:
        import sys as _sys
        from pathlib import Path as _P
        _co_pkg = _P(__file__).parent.parent / "jarvis_company_os"
        if str(_co_pkg.parent) not in _sys.path:
            _sys.path.insert(0, str(_co_pkg.parent))
        from jarvis_company_os import envelope as _env_mod
        from jarvis_company_os.acl import authorize_and_persist
        _agent_slug = _safe_agent_slug(req.agent)
        _env = _env_mod.make_envelope(
            from_uri=f"org.jarvis-war-room.ui.{user}",
            to_uri=f"org.jarvis-war-room.{_agent_slug or 'jarvis'}",
            type_="TASK_ASSIGN",
            payload={"title": "chat", "instructions": req.message.strip()[:200]},
            priority="normal",
        )
        _auth = authorize_and_persist(_env)
        if not _auth.allowed:
            return {
                "delivered": False,
                "allowed": False,
                "rule": _auth.rule,
                "reason": _auth.reason,
                "route_via_lead": _auth.route,
                "audit_id": _auth.audit_id,
                "note": "blocked by Company OS ACL (mode_router chat wrap)",
            }
    except ImportError:
        # Company OS module not yet loaded — allow through (warn-only)
        pass
    except Exception as _wrap_exc:
        # Wrap MUST NOT crash the chat route; log and allow through.
        import logging as _log
        _log.getLogger("jarvis-dashboard").warning(
            "chat authorize wrap failed: %s", _wrap_exc
        )

    mode = req.mode.lower().strip()
    if mode not in MODES:
        mode = "standard"
    msg = req.message.strip()
    agent_slug = _safe_agent_slug(req.agent)
    ap = get_active_project()
    project_slug = req.project.strip() if req.project.strip() else (ap.get("slug") if ap else "default")
    log_action(user, "chat", mode, {"msg": msg[:80], "project": project_slug, "workspace": req.workspace, "agent": agent_slug})
    if project_slug and project_slug != "default":
        try:
            append_session(project_slug, "user", msg, mode)
        except:
            pass

    result = _llm_response(mode, msg, project_slug, agent_slug)
    if result is not None:
        pass
    elif mode == "grill":
        result = _grill_response(msg, user)
    elif mode == "thinking":
        result = _thinking_response(msg)
    elif mode == "spike":
        result = _spike_response(msg)
    elif mode == "plan":
        result = _plan_response(msg)
    elif mode == "tdd":
        result = _tdd_response(msg)
    elif mode == "council":
        result = _council_response(msg)
    elif mode == "debug":
        result = _debug_response(msg)
    elif mode == "boss":
        result = _boss_response(msg)
    elif mode == "codex":
        result = _codex_response(msg)
    else:
        result = _standard_response(msg)

    if result is not None:
        result.setdefault("agent", _load_agent_profile(agent_slug).get("name", agent_slug))

    if project_slug and project_slug != "default" and result:
        try:
            resp_text = result.get("response", "") or result.get("questions", "") or str(result)[:500]
            append_session(project_slug, "assistant", resp_text, mode, {"tier": result.get("tier"), "cost": result.get("cost")})
        except:
            pass
    return result