"""Dashboard-local role/model mapping API.

This module deliberately writes only a dashboard overlay file. It never edits
Hermes profile configs, agent prompts, .env files, or gateway bindings.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from auth.dependencies import get_current_user
from core.config import DASHBOARD_DATA, PROFILE

router = APIRouter(tags=["roles"])

ROLE_FILE = Path(os.environ.get("JARVIS_DASHBOARD_ROLE_MAPPINGS", str(DASHBOARD_DATA / "role_mappings.json"))).expanduser()
SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")

DEFAULT_ROLES = [
    {"role_id": "orchestrator", "label": "Orchestrator", "assigned_agent": "jarvis", "provider": "openai-codex", "model": "gpt-5.5", "status": "active", "platform": "dashboard", "notes": "Top-level dashboard coordinator overlay."},
    {"role_id": "boss", "label": "Boss", "assigned_agent": "jarvis-boss", "provider": "anthropic", "model": "claude-sonnet-4-6", "status": "standby", "platform": "dashboard", "notes": "Architecture, security, and release approval overlay."},
    {"role_id": "manager", "label": "Manager", "assigned_agent": "jarvis-manager", "provider": "openai-codex", "model": "gpt-5.5", "status": "active", "platform": "dashboard", "notes": "Planning, synthesis, and implementation coordination overlay."},
    {"role_id": "secretary", "label": "Secretary", "assigned_agent": "jarvis-secretary", "provider": "ollama-cloud", "model": "qwen3.5:397b", "status": "standby", "platform": "dashboard", "notes": "Context summaries, approval packets, and decision logging overlay."},
    {"role_id": "scout", "label": "Scout", "assigned_agent": "jarvis-scout", "provider": "deepseek", "model": "deepseek-r1", "status": "standby", "platform": "dashboard", "notes": "Research and tooling landscape overlay."},
    {"role_id": "scribe", "label": "Scribe / Docs", "assigned_agent": "jarvis-secretary", "provider": "minimax", "model": "MiniMax-2.7", "status": "standby", "platform": "dashboard", "notes": "Tutorials, docs, and long-form handholding overlay."},
    {"role_id": "reach", "label": "Reach / Growth", "assigned_agent": "", "provider": "", "model": "", "status": "disabled", "platform": "dashboard", "notes": "Optional marketing/growth role; assign an existing profile when needed."},
    {"role_id": "dev", "label": "Dev / Builder", "assigned_agent": "jarvis-manager", "provider": "openai-codex", "model": "gpt-5.5", "status": "active", "platform": "dashboard", "notes": "Coding and technical implementation overlay."},
    {"role_id": "security", "label": "Security", "assigned_agent": "jarvis-boss", "provider": "anthropic", "model": "claude-sonnet-4-6", "status": "standby", "platform": "dashboard", "notes": "Security review and release gate overlay."},
    {"role_id": "qa", "label": "QA / Smoke Tester", "assigned_agent": "jarvis-manager", "provider": "openai-codex", "model": "gpt-5.5", "status": "standby", "platform": "dashboard", "notes": "Smoke tests, runtime checks, and release verification overlay."},
    {"role_id": "memory", "label": "Memory / Obsidian", "assigned_agent": "jarvis-secretary", "provider": "minimax", "model": "MiniMax-2.7", "status": "standby", "platform": "dashboard", "notes": "Obsidian and durable memory update overlay."},
]


class RoleMapping(BaseModel):
    role_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=80)
    assigned_agent: str = Field(default="", max_length=64)
    provider: str = Field(default="", max_length=80)
    model: str = Field(default="", max_length=120)
    status: Literal["active", "standby", "disabled"] = "standby"
    platform: str = Field(default="dashboard", max_length=80)
    notes: str = Field(default="", max_length=500)

    @field_validator("role_id", "assigned_agent")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        if not value:
            return value
        if "/" in value or "\\" in value or ".." in value or not SAFE_NAME.match(value):
            raise ValueError("must be a safe identifier, not a path")
        return value


class RolePayload(BaseModel):
    roles: list[RoleMapping]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile_dirs() -> list[Path]:
    if not PROFILE.exists():
        return []
    return [p for p in sorted(PROFILE.glob("jarvis*")) if p.is_dir() and (p / "config.yaml").exists()]


def _available_agents() -> list[dict]:
    agents = []
    for p in _profile_dirs():
        cfg = {}
        try:
            cfg = yaml.safe_load((p / "config.yaml").read_text()) or {}
        except Exception:
            cfg = {}
        profile = cfg.get("profile") or {}
        model = cfg.get("model") or {}
        name = profile.get("name") or p.name
        agents.append({
            "name": name,
            "description": profile.get("description", ""),
            "provider": model.get("provider", ""),
            "model": model.get("default") or model.get("model") or "",
            "source": str(p / "config.yaml"),
        })
    return agents


def _models() -> list[dict]:
    seen = set()
    models = []
    for agent in _available_agents():
        provider = agent.get("provider") or ""
        model = agent.get("model") or ""
        if not provider and not model:
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen.add(key)
        models.append({"provider": provider, "model": model, "source": agent.get("name", "profile")})
    for role in DEFAULT_ROLES:
        provider = role.get("provider", "")
        model = role.get("model", "")
        key = (provider, model)
        if (provider or model) and key not in seen:
            seen.add(key)
            models.append({"provider": provider, "model": model, "source": "default-role-template"})
    return models


def _ensure_file() -> None:
    if ROLE_FILE.exists():
        return
    ROLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _now(),
        "writes_profile_configs": False,
        "roles": DEFAULT_ROLES,
    }
    ROLE_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _read_payload() -> dict:
    _ensure_file()
    try:
        data = json.loads(ROLE_FILE.read_text())
    except Exception:
        data = {}
    roles = data.get("roles") if isinstance(data, dict) else None
    if not isinstance(roles, list):
        roles = DEFAULT_ROLES
    return {
        "version": data.get("version", 1) if isinstance(data, dict) else 1,
        "updated_at": data.get("updated_at", "") if isinstance(data, dict) else "",
        "writes_profile_configs": False,
        "storage": str(ROLE_FILE),
        "roles": roles,
        "available_agents": _available_agents(),
        "models": _models(),
    }


@router.get("/roles")
def get_roles(user: str = Depends(get_current_user)):
    return _read_payload()


@router.post("/roles")
def save_roles(payload: RolePayload, user: str = Depends(get_current_user)):
    ROLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "updated_at": _now(),
        "updated_by": user,
        "writes_profile_configs": False,
        "roles": [role.model_dump() for role in payload.roles],
    }
    tmp = ROLE_FILE.with_suffix(ROLE_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(ROLE_FILE)
    return _read_payload()


@router.get("/models")
def get_models(user: str = Depends(get_current_user)):
    return {"models": _models()}


@router.post("/roles/test")
def test_role(payload: RoleMapping, user: str = Depends(get_current_user)):
    available = {agent["name"] for agent in _available_agents()}
    agent_ok = not payload.assigned_agent or payload.assigned_agent in available
    model_ok = bool(payload.model or payload.provider)
    return {
        "ok": bool(agent_ok and model_ok),
        "agent_ok": agent_ok,
        "model_ok": model_ok,
        "message": "mapping is valid dashboard overlay" if agent_ok and model_ok else "mapping needs an existing agent and model/provider",
        "writes_profile_configs": False,
    }
