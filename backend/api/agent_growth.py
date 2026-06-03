"""Agent Growth Studio API.

The default write path is dashboard-local only. Skill assignments and new-agent
proposals are stored under the dashboard state directory and do not mutate Hermes
profiles. Real profile provisioning is represented as an explicit proposal flow
for a later human-gated operation.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth.dependencies import get_current_user
from core.config import DASHBOARD_DATA, HERMES, PROFILE

router = APIRouter(tags=["agent-growth"])

SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
ASSIGNMENTS_FILE = Path(os.environ.get(
    "JARVIS_DASHBOARD_AGENT_SKILLS",
    str(DASHBOARD_DATA / "agent_skill_assignments.json"),
)).expanduser()
PROPOSALS_FILE = Path(os.environ.get(
    "JARVIS_DASHBOARD_AGENT_PROPOSALS",
    str(DASHBOARD_DATA / "agent_proposals.json"),
)).expanduser()
REMOVED_AGENTS_FILE = Path(os.environ.get(
    "JARVIS_DASHBOARD_REMOVED_AGENTS",
    str(DASHBOARD_DATA / "removed_agents.json"),
)).expanduser()
RETENTION_DAYS = 7


class SkillItem(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    source: str


class AgentSkillAssignment(BaseModel):
    agent: str = Field(min_length=1, max_length=64)
    skills: list[str] = Field(default_factory=list, max_length=80)
    notes: str = Field(default="", max_length=500)

    @field_validator("agent")
    @classmethod
    def safe_agent(cls, value: str) -> str:
        return _safe_identifier(value, "agent")

    @field_validator("skills")
    @classmethod
    def safe_skills(cls, values: list[str]) -> list[str]:
        clean = []
        seen = set()
        for value in values:
            item = _safe_skill_name(value)
            if item not in seen:
                clean.append(item)
                seen.add(item)
        return clean


class AgentSkillPayload(BaseModel):
    assignments: list[AgentSkillAssignment]


class AgentProposalRequest(BaseModel):
    agent_name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=500)
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    clone_from: str = Field(default="jarvis", max_length=64)
    skills: list[str] = Field(default_factory=list, max_length=80)
    notes: str = Field(default="", max_length=500)

    @field_validator("agent_name", "clone_from")
    @classmethod
    def safe_names(cls, value: str) -> str:
        return _safe_identifier(value, "profile name")

    @field_validator("skills")
    @classmethod
    def safe_skill_list(cls, values: list[str]) -> list[str]:
        return [_safe_skill_name(value) for value in values]


class AgentProposal(BaseModel):
    proposal_id: str
    status: Literal["proposed", "approved", "provisioned", "rejected"] = "proposed"
    created_at: str
    created_by: str
    request: AgentProposalRequest
    draft_config: dict
    writes_profile_configs: bool = False
    safety_note: str


class RemoveAgentRequest(BaseModel):
    agent_name: str = Field(min_length=1, max_length=64)
    reason: str = Field(default="", max_length=500)

    @field_validator("agent_name")
    @classmethod
    def safe_agent_name(cls, value: str) -> str:
        return _safe_identifier(value, "agent name")


class RestoreAgentRequest(BaseModel):
    removed_id: str = Field(min_length=1, max_length=32)

    @field_validator("removed_id")
    @classmethod
    def safe_removed_id(cls, value: str) -> str:
        return _safe_identifier(value, "removed id")


class PermanentDeleteRequest(BaseModel):
    removed_id: str = Field(min_length=1, max_length=32)
    confirm_text: str = Field(min_length=1, max_length=120)

    @field_validator("removed_id")
    @classmethod
    def safe_removed_id(cls, value: str) -> str:
        return _safe_identifier(value, "removed id")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at(now: datetime | None = None) -> str:
    base = now or _now_dt()
    return (base + timedelta(days=RETENTION_DAYS)).isoformat()


def _safe_identifier(value: str, label: str) -> str:
    if "/" in value or "\\" in value or ".." in value or not SAFE_NAME.match(value):
        raise ValueError(f"{label} must be a safe identifier, not a path")
    return value


def _safe_skill_name(value: str) -> str:
    if not value or len(value) > 160:
        raise ValueError("skill name is required and must be <= 160 chars")
    if ".." in value or value.startswith("/") or "\\" in value:
        raise ValueError("skill name must not be a path")
    return value.strip()


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text())
    except Exception:
        return default
    return data if isinstance(data, dict) else default


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)


def _profile_dirs() -> list[Path]:
    if not PROFILE.exists():
        return []
    return [p for p in sorted(PROFILE.glob("jarvis*")) if p.is_dir() and (p / "config.yaml").exists()]


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _scan_skill_root(root: Path) -> list[SkillItem]:
    items: list[SkillItem] = []
    if not root.exists():
        return items
    for skill_file in sorted(root.glob("**/SKILL.md")):
        try:
            text = skill_file.read_text(errors="replace")
        except Exception:
            continue
        meta = _parse_frontmatter(text)
        rel_dir = skill_file.parent.relative_to(root)
        category = str(rel_dir.parent) if str(rel_dir.parent) != "." else ""
        name = str(meta.get("name") or skill_file.parent.name)
        description = str(meta.get("description") or "")
        source = str(skill_file)
        items.append(SkillItem(name=name, description=description, category=category, source=source))
    return items


def _skill_inventory() -> list[SkillItem]:
    roots = [PROFILE / "jarvis" / "skills", HERMES / "skills"]
    seen = set()
    skills: list[SkillItem] = []
    for root in roots:
        for item in _scan_skill_root(root):
            if item.name in seen:
                continue
            seen.add(item.name)
            skills.append(item)
    return sorted(skills, key=lambda item: (item.category, item.name))


def _known_model_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for p in _profile_dirs():
        try:
            cfg = yaml.safe_load((p / "config.yaml").read_text()) or {}
        except Exception:
            continue
        model = cfg.get("model") or {}
        provider = str(model.get("provider") or "")
        default = str(model.get("default") or model.get("model") or "")
        if provider and default:
            pairs.add((provider, default))
    return pairs


def _draft_config(req: AgentProposalRequest) -> dict:
    return {
        "profile": {
            "name": req.agent_name,
            "description": req.description or f"Jarvis agent {req.agent_name}",
        },
        "model": {
            "provider": req.provider,
            "default": req.model,
        },
        "agent_growth": {
            "skills_overlay_only": True,
            "assigned_skills": req.skills,
        },
        "safety": {
            "created_from_dashboard_proposal": True,
            "secrets_embedded": False,
            "requires_manual_gateway_setup": True,
        },
    }


def _proposals_payload() -> dict:
    return _read_json(PROPOSALS_FILE, {"version": 1, "proposals": []})


def _removed_payload() -> dict:
    data = _read_json(REMOVED_AGENTS_FILE, {"version": 1, "updated_at": "", "removed_agents": []})
    removed_agents = data.get("removed_agents") if isinstance(data.get("removed_agents"), list) else []
    return {
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at", ""),
        "storage": str(REMOVED_AGENTS_FILE),
        "writes_profile_configs": False,
        "removed_agents": removed_agents,
    }


def _write_proposals(proposals: list[dict]) -> None:
    _write_json(PROPOSALS_FILE, {"version": 1, "updated_at": _now(), "proposals": proposals})


def _write_removed(removed_agents: list[dict]) -> None:
    _write_json(REMOVED_AGENTS_FILE, {"version": 1, "updated_at": _now(), "removed_agents": removed_agents})


def _proposal_agent_name(proposal: dict) -> str:
    request = proposal.get("request") if isinstance(proposal.get("request"), dict) else {}
    return str(request.get("agent_name") or "")


def _assignment_agent_name(assignment: dict) -> str:
    return str(assignment.get("agent") or "")


def _assignments_payload() -> dict:
    data = _read_json(ASSIGNMENTS_FILE, {"version": 1, "updated_at": "", "assignments": []})
    assignments = data.get("assignments") if isinstance(data.get("assignments"), list) else []
    return {
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at", ""),
        "storage": str(ASSIGNMENTS_FILE),
        "writes_profile_configs": False,
        "assignments": assignments,
    }


@router.get("/skills")
def get_skills(user: str = Depends(get_current_user)):
    return {
        "skills": [item.model_dump() for item in _skill_inventory()],
        "writes_profile_configs": False,
    }


@router.get("/agents/skills")
def get_agent_skills(user: str = Depends(get_current_user)):
    return _assignments_payload()


@router.post("/agents/skills")
def save_agent_skills(payload: AgentSkillPayload, user: str = Depends(get_current_user)):
    known_agents = {p.name for p in _profile_dirs()}
    known_agents.update({item.get("request", {}).get("agent_name", "") for item in _proposals_payload().get("proposals", [])})
    known_skills = {item.name for item in _skill_inventory()}

    for assignment in payload.assignments:
        if assignment.agent not in known_agents:
            raise HTTPException(status_code=422, detail=f"unknown agent: {assignment.agent}")
        missing = [skill for skill in assignment.skills if skill not in known_skills]
        if missing:
            raise HTTPException(status_code=422, detail=f"unknown skills: {', '.join(missing[:5])}")

    data = {
        "version": 1,
        "updated_at": _now(),
        "updated_by": user,
        "writes_profile_configs": False,
        "assignments": [assignment.model_dump() for assignment in payload.assignments],
    }
    _write_json(ASSIGNMENTS_FILE, data)
    return _assignments_payload()


@router.get("/agents/proposals")
def get_agent_proposals(user: str = Depends(get_current_user)):
    data = _proposals_payload()
    return {
        "version": data.get("version", 1),
        "storage": str(PROPOSALS_FILE),
        "writes_profile_configs": False,
        "proposals": data.get("proposals", []),
    }


@router.post("/agents/propose")
def propose_agent(req: AgentProposalRequest, user: str = Depends(get_current_user)):
    target = PROFILE / req.agent_name
    if target.exists():
        raise HTTPException(status_code=409, detail="agent profile already exists")
    if not (PROFILE / req.clone_from / "config.yaml").exists():
        raise HTTPException(status_code=422, detail="clone_from profile does not exist")

    pairs = _known_model_pairs()
    model_verified = (req.provider, req.model) in pairs
    proposal = AgentProposal(
        proposal_id=uuid.uuid4().hex[:12],
        created_at=_now(),
        created_by=user,
        request=req,
        draft_config=_draft_config(req),
        writes_profile_configs=False,
        safety_note=(
            "Proposal only. No Hermes profile directory or config file was created. "
            + ("Selected provider/model pair was observed in existing profile configs." if model_verified else "Selected provider/model pair is not yet verified for provisioning.")
        ),
    )

    data = _proposals_payload()
    proposals = data.get("proposals") if isinstance(data.get("proposals"), list) else []
    proposals.append(proposal.model_dump())
    _write_proposals(proposals)
    return proposal.model_dump()


@router.get("/agents/removed")
def get_removed_agents(user: str = Depends(get_current_user)):
    return _removed_payload()


@router.post("/agents/remove")
def remove_agent(req: RemoveAgentRequest, user: str = Depends(get_current_user)):
    target = PROFILE / req.agent_name
    if target.exists():
        raise HTTPException(
            status_code=409,
            detail="real profile deletion is not allowed from dashboard overlay; use a human-gated provisioning workflow",
        )

    proposals_payload = _proposals_payload()
    proposals = proposals_payload.get("proposals") if isinstance(proposals_payload.get("proposals"), list) else []
    proposal = next((item for item in proposals if _proposal_agent_name(item) == req.agent_name), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail="agent proposal not found")

    assignments_payload = _assignments_payload()
    assignments = assignments_payload.get("assignments") if isinstance(assignments_payload.get("assignments"), list) else []
    assignment = next((item for item in assignments if _assignment_agent_name(item) == req.agent_name), None)

    now = _now_dt()
    removed_agent = {
        "removed_id": uuid.uuid4().hex[:12],
        "agent_name": req.agent_name,
        "status": "removed",
        "removed_at": now.isoformat(),
        "expires_at": _expires_at(now),
        "retention_days": RETENTION_DAYS,
        "removed_by": user,
        "reason": req.reason,
        "writes_profile_configs": False,
        "backup": {
            "proposal": proposal,
            "assignment": assignment,
        },
        "safety_note": "Dashboard-local tombstone only. No Hermes profile directory or config file was deleted.",
    }

    _write_proposals([item for item in proposals if _proposal_agent_name(item) != req.agent_name])
    if assignment is not None:
        remaining_assignments = [item for item in assignments if _assignment_agent_name(item) != req.agent_name]
        _write_json(ASSIGNMENTS_FILE, {
            "version": 1,
            "updated_at": _now(),
            "updated_by": user,
            "writes_profile_configs": False,
            "assignments": remaining_assignments,
        })

    removed_payload = _removed_payload()
    removed_agents = removed_payload.get("removed_agents") if isinstance(removed_payload.get("removed_agents"), list) else []
    removed_agents.insert(0, removed_agent)
    _write_removed(removed_agents)
    return {"writes_profile_configs": False, "removed_agent": removed_agent}


@router.post("/agents/restore")
def restore_agent(req: RestoreAgentRequest, user: str = Depends(get_current_user)):
    removed_payload = _removed_payload()
    removed_agents = removed_payload.get("removed_agents") if isinstance(removed_payload.get("removed_agents"), list) else []
    removed_agent = next((item for item in removed_agents if item.get("removed_id") == req.removed_id), None)
    if removed_agent is None:
        raise HTTPException(status_code=404, detail="removed agent backup not found")
    if removed_agent.get("status") == "permanently_deleted":
        raise HTTPException(status_code=410, detail="removed agent backup was permanently deleted")

    agent_name = str(removed_agent.get("agent_name") or "")
    target = PROFILE / agent_name
    if target.exists():
        raise HTTPException(status_code=409, detail="agent profile already exists")

    backup = removed_agent.get("backup") if isinstance(removed_agent.get("backup"), dict) else {}
    proposal = backup.get("proposal") if isinstance(backup.get("proposal"), dict) else None
    assignment = backup.get("assignment") if isinstance(backup.get("assignment"), dict) else None
    if proposal is None:
        raise HTTPException(status_code=422, detail="removed agent backup has no proposal to restore")

    proposals_payload = _proposals_payload()
    proposals = proposals_payload.get("proposals") if isinstance(proposals_payload.get("proposals"), list) else []
    proposals = [item for item in proposals if _proposal_agent_name(item) != agent_name]
    proposals.insert(0, proposal)
    _write_proposals(proposals)

    if assignment is not None:
        assignments_payload = _assignments_payload()
        assignments = assignments_payload.get("assignments") if isinstance(assignments_payload.get("assignments"), list) else []
        assignments = [item for item in assignments if _assignment_agent_name(item) != agent_name]
        assignments.insert(0, assignment)
        _write_json(ASSIGNMENTS_FILE, {
            "version": 1,
            "updated_at": _now(),
            "updated_by": user,
            "writes_profile_configs": False,
            "assignments": assignments,
        })

    for item in removed_agents:
        if item.get("removed_id") == req.removed_id:
            item["status"] = "restored"
            item["restored_at"] = _now()
            item["restored_by"] = user
    _write_removed(removed_agents)
    return {"writes_profile_configs": False, "restored_agent": agent_name, "removed_id": req.removed_id}


@router.post("/agents/permanent-delete")
def permanent_delete_agent(req: PermanentDeleteRequest, user: str = Depends(get_current_user)):
    removed_payload = _removed_payload()
    removed_agents = removed_payload.get("removed_agents") if isinstance(removed_payload.get("removed_agents"), list) else []
    removed_agent = next((item for item in removed_agents if item.get("removed_id") == req.removed_id), None)
    if removed_agent is None:
        raise HTTPException(status_code=404, detail="removed agent backup not found")
    agent_name = str(removed_agent.get("agent_name") or "")
    required = f"DELETE {agent_name}"
    if req.confirm_text != required:
        raise HTTPException(status_code=422, detail=f"confirmation text must be exactly: {required}")

    for item in removed_agents:
        if item.get("removed_id") == req.removed_id:
            item["status"] = "permanently_deleted"
            item["permanently_deleted_at"] = _now()
            item["permanently_deleted_by"] = user
            item["backup"] = None
    _write_removed(removed_agents)
    return {"writes_profile_configs": False, "permanently_deleted_agent": agent_name, "removed_id": req.removed_id}
