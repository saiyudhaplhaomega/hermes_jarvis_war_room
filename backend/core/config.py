"""Dashboard configuration."""
import os
from pathlib import Path

HOME = Path.home()
HERMES = HOME / ".hermes"
PROFILE = HERMES / "profiles"

# Data sources
AGENTS_DIR = PROFILE / "jarvis" / "agents"
TASKS_DIR = HERMES / "state/tasks"
KANBAN_DB = HERMES / "kanban.db"
MEMORY_DB = HERMES / "memory/memory.db"
DECISIONS_DB = HERMES / "state/rag/decisions.db"
SCORECARD = HERMES / "state/reputation/agent-scorecard.json"
GATEWAY_STATE = PROFILE / "gateway_state.json"
CHANNEL_DIR = PROFILE / "channel_directory.json"
OBSIDIAN = HOME / "Obsidian/Vault/08 Decisions/decision-log.md"

# Dashboard state
DASHBOARD_DATA = HERMES / "state/dashboard"
CACHE_FILE = DASHBOARD_DATA / "cache.json"
SECRET_KEY_FILE = DASHBOARD_DATA / "secret.key"
AUDIT_LOG = HERMES / "state/audit/audit.jsonl"

# Network
API_PORT = 8502
API_HOST = "127.0.0.1"
AGGREGATE_INTERVAL = 30  # seconds

# Auth
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 15
JWT_ABSOLUTE_HOURS = 4
TOTP_ISSUER = "Jarvis War Room"

# Aggregation
REDACTION_PATTERNS = [
    r"sk-[a-zA-Z0-9]{24,}",
    r"[a-zA-Z_]+_API_KEY",
    r"password",
]

# Model to color mapping
MODEL_COLOR = {
    "claude": "#3b82f6",      # blue
    "codex": "#22c55e",       # green
    "minimax": "#a855f7",     # purple
    "deepseek": "#06b6d4",    # cyan
    "qwen": "#f59e0b",        # amber
    "kimi": "#ef4444",         # red
    "default": "#6b7280",    # gray
}

def model_to_color(model_name: str):
    for key, color in MODEL_COLOR.items():
        if key in model_name.lower():
            return color
    return MODEL_COLOR["default"]
