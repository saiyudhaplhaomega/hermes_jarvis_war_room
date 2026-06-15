"""Council of Departments v1 (D-2026-06-09, Phase 4 sub-task 4.1).

Runs a 3-stage strategic vote on a question, scoped to a single
department (e.g. `engineering`, `growth`, `operations`). The runner
is the dashboard-side engine; the user-facing API is in
`backend/api/council.py`.

Flow (per the user-locked council format in
`decisions/council-vote.md` and the Phase 0 plan):

  Stage 1 — independent perspectives: each member profile of the
            department answers the question in isolation. No
            cross-member context. Deterministic per (profile, model)
            pair given the stub adapters.
  Stage 2 — anonymized ranking: each member profile ranks the
            stage-1 responses (best -> worst, no author names).
  Stage 3 — chairman synthesis: the chairman model (default
            `(codex, gpt-5.5)`) reads all stage-1 + stage-2 outputs
            and produces a final answer with explicit minority
            warnings. Confidence is one of `low | medium | high`.

Department membership is derived from
`jarvis_company_os.registry.TEAM_MAP`. The single source of truth for
profiles (`KNOWN_PROFILES`) is the union of all TEAM_MAP keys; the
council never asks a profile that isn't in TEAM_MAP.

Load-bearing invariant: this module does NOT touch Hermes profile
configs. Returns a JSON-serializable decision dict the caller can
persist. The replay store lives in `backend/api/council.py`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("jarvis.council_departments")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Default chairman. User-locked: codex for now; the runner accepts
# any (chairman_provider, chairman_model) pair as long as
# `core.model_invoker.is_known_model_pair` says yes.
DEFAULT_CHAIRMAN: Tuple[str, str] = ("codex", "gpt-5.5")

# Default per-member model. Each member is allowed to use its own
# model in v1 (per codex verdict, "pluggable" — codex now, ollama/
# nemotron later). The default is the chairman's model for v1
# simplicity.
DEFAULT_MEMBER_MODEL: Tuple[str, str] = ("codex", "gpt-5.5")

SAFE_SLUG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
SAFE_QUESTION_MIN = 4
SAFE_QUESTION_MAX = 2000
DEPARTMENT_MAX_MEMBERS = 16  # bound stage-1 fan-out

WRITES_PROFILE_CONFIGS = False  # load-bearing invariant


# ---------------------------------------------------------------------------
# Decision shape
# ---------------------------------------------------------------------------
@dataclass
class Stage1Perspective:
    """A single member's independent answer in stage 1."""
    profile: str
    provider: str
    model: str
    response: str
    latency_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Stage2Ranking:
    """A single member's anonymized ranking of stage-1 responses."""
    profile: str
    ranking: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CouncilDecision:
    """The full output of one council run."""
    decision_id: str
    question: str
    department: str
    members: List[str]
    chairman_provider: str
    chairman_model: str
    member_provider: str
    member_model: str
    stage1: List[Stage1Perspective]
    stage2: List[Stage2Ranking]
    stage3_synthesis: str
    minority_warnings: List[str]
    confidence: str
    created_at: float
    writes_profile_configs: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stage1"] = [s.to_dict() for s in self.stage1]
        d["stage2"] = [s.to_dict() for s in self.stage2]
        return d


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class CouncilError(Exception):
    """Base for all council runner errors."""


class UnknownDepartment(CouncilError):
    pass


class EmptyDepartment(CouncilError):
    pass


class UnsafeQuestion(CouncilError):
    pass


class UnknownMemberModel(CouncilError):
    pass


# ---------------------------------------------------------------------------
# Department membership
# ---------------------------------------------------------------------------
def list_departments() -> List[str]:
    """Return the sorted unique set of team names from TEAM_MAP.

    This is the user-locked "13 departments" + the few legacy
    team names. Adding a new team in TEAM_MAP shows up here
    automatically.
    """
    try:
        from jarvis_company_os.registry import TEAM_MAP
        return sorted(set(TEAM_MAP.values()))
    except Exception as e:
        log.warning("council.list_departments failed: %s", e)
        return []


def members_of(department: str) -> List[str]:
    """Return the sorted list of jarvis profiles in the given department."""
    if not SAFE_SLUG.match(department):
        raise UnknownDepartment(f"invalid department name: {department!r}")
    try:
        from jarvis_company_os.registry import TEAM_MAP
    except Exception as e:
        raise CouncilError(f"registry unavailable: {e}") from e
    members = sorted(p for p, team in TEAM_MAP.items() if team == department)
    if not members:
        raise EmptyDepartment(
            f"no members found for department={department!r}. "
            f"Known departments: {list_departments()}"
        )
    if len(members) > DEPARTMENT_MAX_MEMBERS:
        log.warning("council.members_of capping %d members to %d", len(members), DEPARTMENT_MAX_MEMBERS)
        members = members[:DEPARTMENT_MAX_MEMBERS]
    return members


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
def _stage1_prompt(question: str, profile: str, department: str) -> str:
    return (
        f"You are {profile}, a member of the {department} department in the "
        f"jarvis-war-room multi-agent system. The boss is asking the council:\n\n"
        f"Q: {question}\n\n"
        f"Give your independent perspective. No need to consult anyone else. "
        f"Be specific, 2-4 sentences. If you see a risk, name it."
    )


def _stage2_prompt(question: str, stage1_responses: List[str]) -> str:
    options = "\n".join(f"[{i}] {r[:200]}" for i, r in enumerate(stage1_responses))
    return (
        f"Below are {len(stage1_responses)} anonymized perspectives on this question:\n\n"
        f"Q: {question}\n\n"
        f"Responses (numbered):\n{options}\n\n"
        f"Rank them best-to-worst. Output format: a single line of comma-separated "
        f"index numbers, e.g. `2,0,1`. Do not include any other text."
    )


def _stage3_prompt(question: str, stage1: List[Stage1Perspective], stage2: List[Stage2Ranking]) -> str:
    lines = [f"Question: {question}\n"]
    for i, v in enumerate(stage1):
        lines.append(f"--- Perspective {i} (from {v.profile}) ---\n{v.response}\n")
    for v in stage2:
        if v.ranking:
            lines.append(f"--- Rankings by {v.profile} ---\n{v.ranking}\n")
    joined = "\n".join(lines)
    return (
        "You are the chairman of the council. Synthesize a final answer.\n"
        "Rules:\n"
        "  - Lead with the consensus answer in 1-2 sentences.\n"
        "  - Then add a 'Rationale:' line summarizing the top-ranked reasons.\n"
        "  - Then add a 'Minority warnings:' block listing any perspectives that "
        "disagreed with the consensus. Prefix each warning with `WARNING: `.\n"
        "  - End with a final line `Confidence: low|medium|high`.\n\n"
        f"{joined}"
    )


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------
def run_department_vote(
    question: str,
    department: str,
    *,
    chairman: Tuple[str, str] = DEFAULT_CHAIRMAN,
    member_model: Tuple[str, str] = DEFAULT_MEMBER_MODEL,
    invoker: Optional[Callable] = None,
) -> CouncilDecision:
    """Run the 3-stage council vote for a department. Returns a decision.

    `invoker` is a callable with the same shape as
    `core.model_invoker.invoke` — defaults to the real one. Tests
    inject a fake to assert on the prompts without making network
    calls. The real `invoke` already swallows adapter errors and
    returns a structured response, so stage 1 cannot crash the
    runner on a single bad member.
    """
    if not isinstance(question, str) or not (SAFE_QUESTION_MIN <= len(question) <= SAFE_QUESTION_MAX):
        raise UnsafeQuestion(
            f"question must be {SAFE_QUESTION_MIN}-{SAFE_QUESTION_MAX} chars; got {len(question or '')}"
        )
    members = members_of(department)
    inv = invoker or _default_invoker()

    # Validate model pairs up-front so we fail loud instead of mid-stage.
    _validate_model_pair(chairman, "chairman")
    _validate_model_pair(member_model, "member")

    # --- Stage 1: independent perspectives ---
    stage1: List[Stage1Perspective] = []
    for profile in members:
        prompt = _stage1_prompt(question, profile, department)
        try:
            resp = inv(member_model[0], member_model[1], prompt, {"stage": 1, "profile": profile})
        except Exception as e:
            log.warning("stage1 invoke error profile=%s: %s", profile, e)
            stage1.append(Stage1Perspective(
                profile=profile, provider=member_model[0], model=member_model[1],
                response="", latency_ms=0, error=f"{type(e).__name__}: {e}",
            ))
            continue
        stage1.append(Stage1Perspective(
            profile=profile,
            provider=resp.provider,
            model=resp.model,
            response=resp.response,
            latency_ms=resp.latency_ms,
            error=(resp.model_metadata.get("error") if resp.model_metadata else None),
        ))

    # --- Stage 2: anonymized rankings ---
    stage1_responses = [s.response or f"(no response from {s.profile})" for s in stage1]
    stage2: List[Stage2Ranking] = []
    for profile in members:
        prompt = _stage2_prompt(question, stage1_responses)
        try:
            resp = inv(member_model[0], member_model[1], prompt, {"stage": 2, "profile": profile})
        except Exception as e:
            log.warning("stage2 invoke error profile=%s: %s", profile, e)
            stage2.append(Stage2Ranking(profile=profile, ranking="", error=f"{type(e).__name__}: {e}"))
            continue
        stage2.append(Stage2Ranking(profile=profile, ranking=resp.response.strip(), error=None))

    # --- Stage 3: chairman synthesis ---
    stage3_prompt = _stage3_prompt(question, stage1, stage2)
    try:
        synth_resp = inv(chairman[0], chairman[1], stage3_prompt, {"stage": 3, "role": "chairman"})
        synthesis = synth_resp.response
    except Exception as e:
        log.warning("stage3 invoke error: %s", e)
        synthesis = (
            f"[chairman invoke error: {type(e).__name__}: {e}]\n"
            f"WARNING: council could not synthesize a final answer. "
            f"See stage1/stage2 raw responses."
        )

    confidence = _extract_confidence(synthesis)
    warnings = _extract_minority_warnings(synthesis)

    return CouncilDecision(
        decision_id=uuid.uuid4().hex[:12],
        question=question,
        department=department,
        members=members,
        chairman_provider=chairman[0],
        chairman_model=chairman[1],
        member_provider=member_model[0],
        member_model=member_model[1],
        stage1=stage1,
        stage2=stage2,
        stage3_synthesis=synthesis,
        minority_warnings=warnings,
        confidence=confidence,
        created_at=time.time(),
        writes_profile_configs=WRITES_PROFILE_CONFIGS,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _default_invoker():
    from core.model_invoker import invoke
    return invoke


def _validate_model_pair(pair: Tuple[str, str], role: str) -> None:
    try:
        from core.model_invoker import is_known_model_pair
    except Exception as e:
        raise CouncilError(f"model_invoker unavailable: {e}") from e
    if not is_known_model_pair(pair[0], pair[1]):
        raise UnknownMemberModel(
            f"unknown {role} model pair {pair!r}. "
            f"See core.model_invoker.known_model_pairs()."
        )


def _extract_confidence(synthesis: str) -> str:
    """Pull `Confidence: low|medium|high` from the synthesis. Default medium."""
    m = re.search(r"confidence\s*[:=]\s*(low|medium|high)", synthesis, re.IGNORECASE)
    return m.group(1).lower() if m else "medium"


def _extract_minority_warnings(synthesis: str) -> List[str]:
    """Pull `WARNING:` lines and any standalone `- ` warnings from stage 3."""
    out: List[str] = []
    for line in synthesis.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.lower().startswith("warning:") or s.lower().startswith("minority:"):
            out.append(s)
    return out
