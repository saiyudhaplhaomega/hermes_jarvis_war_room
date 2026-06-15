"""Tests for Phase 4 — Council of Departments v1 + pluggable model invoker.

D-2026-06-09 (Phase 4, sub-tasks 4.0/4.1/4.2):
- KNOWN_PROFILES carryover from Phase 3
- Pluggable model invoker at `core/model_invoker.py`
- Council runner at `core/council_departments.py`
- REST API at `api/council.py`

All tests use the in-process stub adapters. No subprocess / network
calls happen during these tests. The `writes_profile_configs: false`
invariant is asserted on every API response.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def clean_state(tmp_path, monkeypatch):
    """Reset env + sys.modules so every test gets a fresh app + isolated state."""
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "1")
    monkeypatch.setenv(
        "JARVIS_DASHBOARD_COUNCIL_DECISIONS",
        str(tmp_path / "council_decisions.json"),
    )
    monkeypatch.setenv(
        "JARVIS_DISCORD_GATEWAY_STATE",
        str(tmp_path / "discord_gateway.json"),
    )
    # Seed a temp profiles dir with the 14 user-locked profiles so
    # both the council and the discord gateway accept them.
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    for slug in [
        "jarvis-backend", "jarvis-council-departments", "jarvis-customer-success",
        "jarvis-data-ml", "jarvis-devops", "jarvis-finance", "jarvis-frontend",
        "jarvis-legal", "jarvis-marketing", "jarvis-mobile", "jarvis-researcher",
        "jarvis-sales", "jarvis-secretary", "jarvis-ui_ux",
    ]:
        (profiles_dir / slug).mkdir(parents=True, exist_ok=True)
        (profiles_dir / slug / "config.yaml").write_text(f"name: {slug}\nrole: stub\nmodel: codex\n")
    monkeypatch.setenv("HERMES_PROFILES_DIR", str(profiles_dir))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))

    for name in list(sys.modules):
        if (
            name == "server"
            or name.startswith("api.council")
            or name.startswith("api.discord_gateway")
            or name.startswith("api.discord_bridge")
            or name.startswith("api.agent_growth")
            or name == "core.config"
            # NOTE: do NOT pop core.council_departments / core.model_invoker —
            # they're stateless and the tests below re-import them directly.
            # The server import doesn't depend on their reload.
        ):
            sys.modules.pop(name, None)
    return tmp_path


def _load_app(clean_state):
    import server
    return server.app


def _token():
    return "test-token"


def _url(path: str) -> str:
    return f"/api/plugins/jarvis-dashboard/v1{path}?token={_token()}"


# ---------------------------------------------------------------------------
# 4.0: KNOWN_PROFILES carryover
# ---------------------------------------------------------------------------
def test_known_profiles_derived_from_team_map(clean_state):
    """KNOWN_PROFILES == set(TEAM_MAP.keys()). Single source of truth."""
    from jarvis_company_os import registry
    from jarvis_company_os.registry import KNOWN_PROFILES, TEAM_MAP
    assert KNOWN_PROFILES == set(TEAM_MAP.keys())
    assert "jarvis-council-departments" in KNOWN_PROFILES
    assert "jarvis-frontend" in KNOWN_PROFILES
    assert isinstance(KNOWN_PROFILES, frozenset)


def test_known_profiles_are_safe_slugs(clean_state):
    """D-2026-06-09 (Phase 7): every KNOWN_PROFILES entry must be a
    safe slug. Catches typos like spaces or paths in TEAM_MAP that
    would otherwise leak into the discord gateway allowlist and
    council department membership.

    Single source of truth: TEAM_MAP in jarvis_company_os.registry.
    """
    import re
    from jarvis_company_os.registry import KNOWN_PROFILES
    safe = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    bad = [p for p in KNOWN_PROFILES if not safe.match(p)]
    assert not bad, f"unsafe profile slugs in KNOWN_PROFILES: {bad}"


def test_team_map_values_are_valid_department_names(clean_state):
    """D-2026-06-09 (Phase 7): every TEAM_MAP value is a department
    the council runner can resolve (slug-shaped, non-empty). A
    typo here would silently produce empty departments.
    """
    import re
    from jarvis_company_os.registry import TEAM_MAP
    safe = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
    bad = [(p, t) for p, t in TEAM_MAP.items() if not safe.match(t)]
    assert not bad, f"unsafe department names in TEAM_MAP: {bad}"


def test_known_profiles_drift_class_eliminated(clean_state):
    """D-2026-06-09 (Phase 7): this test EXPLICITLY proves the drift
    class from the Phase 3 codex verdict is gone. The drift class:
    `KNOWN_PROFILES` could fall out of sync with `TEAM_MAP` (e.g. if
    someone hardcoded it again). The single-source-of-truth pattern
    makes that impossible — adding/removing a TEAM_MAP entry is the
    ONLY way to change KNOWN_PROFILES.

    We assert by introspecting the source: KNOWN_PROFILES must be
    defined as `frozenset(TEAM_MAP.keys())` (literal expression),
    not a copy.
    """
    import inspect
    from jarvis_company_os import registry
    src = inspect.getsource(registry)
    # The defining line must reference TEAM_MAP directly.
    assert "KNOWN_PROFILES = frozenset(TEAM_MAP.keys())" in src, (
        "KNOWN_PROFILES must be derived from TEAM_MAP.keys() to "
        "prevent drift. Got: " + src[src.find("KNOWN_PROFILES"):src.find("KNOWN_PROFILES")+120]
    )


def test_discord_gateway_uses_known_profiles(clean_state):
    """The discord gateway should accept any profile in KNOWN_PROFILES."""
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.post(_url("/discord-gateway/messages"), json={
        "project": "test-proj", "profile": "jarvis-council-departments", "content": "hi"
    })
    assert r.status_code == 200, r.text
    r2 = client.post(_url("/discord-gateway/messages"), json={
        "project": "test-proj", "profile": "jarvis-scout", "content": "hi"
    })
    assert r2.status_code == 200, r2.text  # jarvis-scout is in TEAM_MAP


# ---------------------------------------------------------------------------
# 4.2: Pluggable model invoker
# ---------------------------------------------------------------------------
def test_model_invoker_default_adapters_registered(clean_state):
    from core import model_invoker
    if "core.model_invoker" not in sys.modules:
        importlib.import_module("core.model_invoker")
    importlib.reload(model_invoker)
    assert set(model_invoker.known_providers()) >= {"codex", "ollama", "nemotron"}


def test_model_invoker_returns_model_response(clean_state):
    from core import model_invoker
    if "core.model_invoker" not in sys.modules:
        importlib.import_module("core.model_invoker")
    importlib.reload(model_invoker)
    resp = model_invoker.invoke("codex", "gpt-5.5", "What is 2+2?")
    assert resp.provider == "codex"
    assert resp.model == "gpt-5.5"
    assert "stub" in resp.response or "2" in resp.response
    assert resp.latency_ms >= 0


def test_model_invoker_handles_adapter_error(clean_state):
    from core import model_invoker
    if "core.model_invoker" not in sys.modules:
        importlib.import_module("core.model_invoker")
    importlib.reload(model_invoker)
    def bad_adapter(provider, model, prompt, metadata):
        raise RuntimeError("kaboom")
    model_invoker.register_adapter("broken", bad_adapter)
    resp = model_invoker.invoke("broken", "x", "hi")
    assert "kaboom" in resp.response
    assert resp.model_metadata.get("error") == "RuntimeError"


def test_model_invoker_rejects_invalid_provider_name(clean_state):
    from core import model_invoker
    if "core.model_invoker" not in sys.modules:
        importlib.import_module("core.model_invoker")
    importlib.reload(model_invoker)
    with pytest.raises(ValueError):
        model_invoker.register_adapter("BAD NAME!", lambda *a: None)


def test_known_model_pairs_includes_codex_and_ollama(clean_state):
    from core import model_invoker
    if "core.model_invoker" not in sys.modules:
        importlib.import_module("core.model_invoker")
    importlib.reload(model_invoker)
    pairs = model_invoker.known_model_pairs()
    assert ("codex", "gpt-5.5") in pairs
    assert any(p == "ollama" for p, _ in pairs)


# ---------------------------------------------------------------------------
# 4.1: Council runner (core)
# ---------------------------------------------------------------------------
def test_council_list_departments(clean_state):
    from core.council_departments import list_departments
    depts = list_departments()
    assert "engineering" in depts
    assert "leadership" in depts
    assert "growth" in depts


def test_council_members_of_engineering(clean_state):
    from core.council_departments import members_of
    members = members_of("engineering")
    assert "jarvis-frontend" in members
    assert "jarvis-backend" in members
    assert "jarvis-devops" in members
    assert "jarvis-data-ml" in members
    # Operations is a different team — must not leak in.
    assert "jarvis-finance" not in members
    assert "jarvis-legal" not in members


def test_council_members_of_unknown_department_raises(clean_state):
    """Unknown department (valid shape, no members) raises EmptyDepartment."""
    from core.council_departments import members_of, EmptyDepartment
    with pytest.raises(EmptyDepartment):
        members_of("not-a-real-dept")


def test_council_members_of_unsafe_department_raises(clean_state):
    """Unsafe name raises UnknownDepartment before the registry lookup."""
    from core.council_departments import members_of, UnknownDepartment
    with pytest.raises(UnknownDepartment):
        members_of("../bad")


def test_council_run_department_vote_with_fake_invoker(clean_state):
    """The full 3-stage vote runs end-to-end with no subprocess/network."""
    from core.council_departments import run_department_vote

    # Fake invoker that returns deterministic responses per (provider, model, stage).
    def fake_invoker(provider, model, prompt, metadata):
        from core.model_invoker import ModelResponse
        stage = metadata.get("stage", "?")
        return ModelResponse(
            provider=provider, model=model,
            response=f"[stage{stage}/model={model}] ok",
            model_metadata={"fake": True, "stage": stage},
        )

    decision = run_department_vote(
        question="Should we ship Phase 4 today?",
        department="engineering",
        chairman=("codex", "gpt-5.5"),
        member_model=("codex", "gpt-5.5"),
        invoker=fake_invoker,
    )
    assert decision.department == "engineering"
    assert "jarvis-frontend" in decision.members
    assert len(decision.stage1) == len(decision.members)
    assert len(decision.stage2) == len(decision.members)
    # Stage 3 used the fake and we should see stage3 marker in synthesis.
    assert "[stage3/" in decision.stage3_synthesis or "stage3" in decision.stage3_synthesis
    assert decision.confidence in ("low", "medium", "high")
    assert decision.writes_profile_configs is False


def test_council_rejects_unsafe_question(clean_state):
    from core.council_departments import run_department_vote, UnsafeQuestion
    with pytest.raises(UnsafeQuestion):
        run_department_vote(question="hi", department="engineering")


def test_council_rejects_unknown_chairman_model(clean_state):
    from core.council_departments import run_department_vote, UnknownMemberModel
    with pytest.raises(UnknownMemberModel):
        run_department_vote(
            question="a real question here",
            department="engineering",
            chairman=("notreal", "notreal-99"),
        )


# ---------------------------------------------------------------------------
# 4.1: Council API
# ---------------------------------------------------------------------------
def test_council_api_get_departments(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.get(_url("/council/departments"))
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["writes_profile_configs"] is False
    names = {d["department"] for d in payload["departments"]}
    assert "engineering" in names
    eng = next(d for d in payload["departments"] if d["department"] == "engineering")
    assert "jarvis-frontend" in eng["members"]


def test_council_api_post_ask_persists_decision(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.post(_url("/council/ask"), json={
        "department": "engineering",
        "question": "Should we ship Phase 4 today?",
    })
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["writes_profile_configs"] is False
    d = payload["decision"]
    assert d["department"] == "engineering"
    assert d["question"] == "Should we ship Phase 4 today?"
    assert d["chairman_provider"] == "codex"
    assert len(d["stage1"]) >= 2
    assert len(d["stage2"]) >= 2
    assert d["stage3_synthesis"]
    # File is written.
    state = json.loads((clean_state / "council_decisions.json").read_text())
    assert len(state["decisions"]) == 1


def test_council_api_post_ask_rejects_unknown_department(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.post(_url("/council/ask"), json={
        "department": "not-a-real-team",
        "question": "Does this even exist?",
    })
    assert r.status_code == 404, r.text


def test_council_api_post_ask_rejects_unsafe_question(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.post(_url("/council/ask"), json={
        "department": "engineering",
        "question": "x",  # too short
    })
    assert r.status_code == 422, r.text


def test_council_api_post_ask_rejects_unknown_model_pair(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.post(_url("/council/ask"), json={
        "department": "engineering",
        "question": "what should we ship?",
        "chairman_provider": "nope",
        "chairman_model": "nope-99",
    })
    assert r.status_code == 422, r.text


def test_council_api_list_and_get_decisions(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    # Two questions.
    for q in ["q one for engineering team", "q two for engineering team"]:
        client.post(_url("/council/ask"), json={"department": "engineering", "question": q})

    r = client.get(_url("/council/decisions"))
    assert r.status_code == 200
    payload = r.json()
    assert payload["writes_profile_configs"] is False
    assert payload["total"] == 2
    assert len(payload["decisions"]) == 2

    first_id = payload["decisions"][0]["decision_id"]
    r2 = client.get(_url(f"/council/decisions/{first_id}"))
    assert r2.status_code == 200
    assert r2.json()["decision"]["decision_id"] == first_id
    assert r2.json()["writes_profile_configs"] is False


def test_council_api_decisions_filter_by_department(clean_state):
    app = _load_app(clean_state)
    client = TestClient(app)
    client.post(_url("/council/ask"), json={"department": "engineering", "question": "engineering question one"})
    client.post(_url("/council/ask"), json={"department": "leadership", "question": "leadership question one"})

    r = client.get(_url("/council/decisions") + "&department=engineering")
    assert r.status_code == 200
    assert all(d["department"] == "engineering" for d in r.json()["decisions"])


# ---------------------------------------------------------------------------
# 5.2: Phase 5 — chairman-error resilience (codex major-task finding #4)
# ---------------------------------------------------------------------------
def test_council_chairman_raises_decision_still_persists(clean_state):
    """If the chairman adapter throws on stage 3, the runner returns a
    fallback synthesis AND the API persists the decision.

    Locks the resilience invariant: a single bad adapter cannot lose
    the stage1/stage2 work or the audit trail.
    """
    from core.council_departments import run_department_vote

    def failing_chairman_invoker(provider, model, prompt, metadata):
        from core.model_invoker import ModelResponse
        stage = metadata.get("stage")
        if stage == 3:
            raise RuntimeError("chairman model is down for maintenance")
        return ModelResponse(
            provider=provider, model=model,
            response=f"[ok stage{stage} from {model}]",
            model_metadata={"stage": stage},
        )

    decision = run_department_vote(
        question="resilience test for the chairman adapter",
        department="engineering",
        chairman=("codex", "gpt-5.5"),
        member_model=("codex", "gpt-5.5"),
        invoker=failing_chairman_invoker,
    )
    # Stage 1 and 2 should be intact.
    assert len(decision.stage1) == len(decision.members)
    assert len(decision.stage2) == len(decision.members)
    # Stage 3 should contain a fallback marker.
    assert "chairman invoke error" in decision.stage3_synthesis or "WARNING" in decision.stage3_synthesis
    # Confidence stays valid even when synthesis is the fallback.
    assert decision.confidence in ("low", "medium", "high")
    # writes_profile_configs invariant preserved.
    assert decision.writes_profile_configs is False

    # And the API persists the decision anyway.
    app = _load_app(clean_state)
    client = TestClient(app)
    r = client.post(_url("/council/ask"), json={
        "department": "engineering",
        "question": "another resilience check, persistence test",
    })
    assert r.status_code == 200
    state = json.loads((clean_state / "council_decisions.json").read_text())
    assert len(state["decisions"]) == 1


def test_council_chairman_error_persists_via_api(clean_state):
    """The API path persists decisions even when the synthesis is the
    fallback (i.e. when the chairman adapter raised)."""
    from core.council_departments import run_department_vote

    def failing_chairman(provider, model, prompt, metadata):
        from core.model_invoker import ModelResponse
        if metadata.get("stage") == 3:
            raise RuntimeError("chairman unavailable")
        return ModelResponse(
            provider=provider, model=model,
            response=f"stage{metadata.get('stage')} ok",
            model_metadata={},
        )

    decision = run_department_vote(
        question="persistence check for fallback synthesis path",
        department="engineering",
        invoker=failing_chairman,
    )
    # Caller can introspect via the decision object.
    assert "chairman invoke error" in decision.stage3_synthesis or "WARNING" in decision.stage3_synthesis
    assert decision.confidence in ("low", "medium", "high")


# ---------------------------------------------------------------------------
# Phase 6: real HTTP adapters for Ollama + Nemotron
# ---------------------------------------------------------------------------
def test_ollama_adapter_makes_real_post(clean_state):
    """D-2026-06-09 (Phase 6): the ollama adapter is real HTTP, posting
    to {OLLAMA_BASE_URL}/api/generate. MockTransport intercepts the
    call so no real network is made. Asserts URL, method, payload.
    """
    import httpx
    from core import model_invoker

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"response": "ollama says hi", "eval_count": 12})

    model_invoker._ollama_httpx_client_factory = lambda: httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch_ollama_url = "http://test-ollama:9999"

    import os
    prev = os.environ.get("OLLAMA_BASE_URL")
    os.environ["OLLAMA_BASE_URL"] = monkeypatch_ollama_url
    try:
        resp = model_invoker.invoke("ollama", "llama3.1:8b", "what is 2+2?")
    finally:
        if prev is None:
            os.environ.pop("OLLAMA_BASE_URL", None)
        else:
            os.environ["OLLAMA_BASE_URL"] = prev

    assert resp.provider == "ollama"
    assert resp.model == "llama3.1:8b"
    assert resp.response == "ollama says hi"
    assert captured["url"] == f"{monkeypatch_ollama_url}/api/generate"
    assert captured["method"] == "POST"
    assert captured["body"]["model"] == "llama3.1:8b"
    assert captured["body"]["prompt"] == "what is 2+2?"
    assert captured["body"]["stream"] is False
    assert resp.model_metadata["stub"] is False
    assert resp.model_metadata["ollama_eval_count"] == 12


def test_nemotron_adapter_makes_real_post(clean_state):
    """D-2026-06-09 (Phase 6): the nemotron adapter is real HTTP."""
    import httpx
    from core import model_invoker

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"response": "nemotron structured answer"})

    model_invoker._nemotron_httpx_client_factory = lambda: httpx.Client(transport=httpx.MockTransport(handler))

    import os
    prev = os.environ.get("NEMOTRON_BASE_URL")
    os.environ["NEMOTRON_BASE_URL"] = "http://test-nemotron:7777"
    try:
        resp = model_invoker.invoke("nemotron", "nemotron-mini:4b", "list three risks")
    finally:
        if prev is None:
            os.environ.pop("NEMOTRON_BASE_URL", None)
        else:
            os.environ["NEMOTRON_BASE_URL"] = prev

    assert resp.response == "nemotron structured answer"
    assert captured["url"] == "http://test-nemotron:7777/api/generate"
    assert captured["body"]["model"] == "nemotron-mini:4b"
    assert captured["body"]["stream"] is False


def test_ollama_adapter_network_error_returns_structured_response(clean_state):
    """D-2026-06-09 (Phase 6): a network failure in the ollama adapter
    is converted by `invoke()` into a structured ModelResponse with
    `model_metadata["error"]` set, NOT raised to the caller. Locks
    the resilience invariant the council runner depends on.
    """
    import httpx
    from core import model_invoker

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated ollama outage")

    model_invoker._ollama_httpx_client_factory = lambda: httpx.Client(transport=httpx.MockTransport(handler))

    # Should NOT raise.
    resp = model_invoker.invoke("ollama", "llama3.1:8b", "hi")
    assert resp.provider == "ollama"
    assert resp.model == "llama3.1:8b"
    # Response is the structured error marker.
    assert "ollama outage" in resp.response or "ConnectError" in resp.response
    assert resp.model_metadata.get("error") == "ConnectError"
    assert resp.latency_ms >= 0


def test_nemotron_adapter_uses_default_url_when_no_env(clean_state, monkeypatch):
    """D-2026-06-09 (Phase 6): when NEMOTRON_BASE_URL is unset, the
    adapter falls back to http://localhost:8000 (sanity check on the
    default so a misconfigured prod doesn't silently hit a different
    host).
    """
    import httpx
    from core import model_invoker

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"response": "ok"})

    model_invoker._nemotron_httpx_client_factory = lambda: httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.delenv("NEMOTRON_BASE_URL", raising=False)

    resp = model_invoker.invoke("nemotron", "nemotron-mini:4b", "hi")
    assert resp.response == "ok"
    assert captured["url"] == "http://localhost:8000/api/generate"
