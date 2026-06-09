"""Tests for the 3-stage Council (Loop 3 R1-R10)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_council_default_models_use_codex_and_ollama():
    from core.council import Council
    c = Council()
    assert "codex" in c.models
    assert any("ollama" in m for m in c.models)
    assert c.chairman == "codex"  # strongest by default


def test_council_can_be_configured_with_different_models():
    from core.council import Council
    c = Council(models=["ollama:qwen2.5:3b-instruct"], chairman="ollama:qwen2.5:3b-instruct")
    assert len(c.models) == 1
    assert c.chairman == "ollama:qwen2.5:3b-instruct"


def test_council_parse_rankings_handles_clean_json():
    from core.council import Council
    c = Council()
    raw = '{"rankings": [{"id": "resp_0", "correctness": 1}, {"id": "resp_1", "correctness": 2}]}'
    parsed = c._parse_rankings(raw, expected=2)
    assert parsed == {"resp_0": {"id": "resp_0", "correctness": 1},
                      "resp_1": {"id": "resp_1", "correctness": 2}}


def test_council_parse_rankings_strips_code_fences():
    from core.council import Council
    c = Council()
    raw = '```json\n{"rankings": [{"id": "resp_0", "correctness": 1}]}\n```'
    parsed = c._parse_rankings(raw, expected=1)
    assert "resp_0" in parsed


def test_council_parse_rankings_returns_empty_on_garbage():
    from core.council import Council
    c = Council()
    parsed = c._parse_rankings("not json at all, sorry", expected=2)
    assert parsed == {}


def test_council_call_routes_to_ollama_prefixed_models(monkeypatch):
    """Verify the routing logic: 'ollama:foo' -> _call_ollama with model=foo."""
    from core import council as council_mod
    from core.council import Council as _Council  # avoid name collision with monkeypatch's Council
    calls = []
    def fake_ollama(prompt, model, timeout=90):
        calls.append(("ollama", model))
        return f"ollama:{model}:{prompt[:20]}"
    def fake_codex(prompt, timeout=90):
        calls.append(("codex", None))
        return f"codex:{prompt[:20]}"
    monkeypatch.setattr(council_mod, "_call_ollama", fake_ollama)
    monkeypatch.setattr(council_mod, "_call_codex", fake_codex)
    c = _Council(models=["codex", "ollama:qwen2.5:7b-instruct"])
    votes = c.stage1_parallel("What is War Room?")
    assert len(votes) == 2
    # Codex was called
    assert ("codex", None) in calls
    # Ollama was called with the model stripped of prefix
    assert ("ollama", "qwen2.5:7b-instruct") in calls
    # Vote models are recorded correctly
    assert votes[0].model == "codex"
    assert votes[1].model == "ollama:qwen2.5:7b-instruct"


def test_council_decision_to_dict_is_json_serializable():
    from core.council import Council, CouncilVote
    c = Council(models=["m1", "m2"])
    # Build a fake decision directly
    from core.council import CouncilDecision
    import time
    d = CouncilDecision(
        id="x", query="q", votes=[
            CouncilVote(model="m1", response="r1", ranking={"resp_0": {"id": "resp_0", "rank": 1}}),
        ],
        stage1_responses={"resp_0": "r1"},
        stage2_rankings=[{"resp_0": {"id": "resp_0", "rank": 1}}],
        stage3_synthesis="answer",
        minority_warnings=["w1"],
        chairman="m1",
        model_list=["m1", "m2"],
        created_at=time.time(),
    )
    as_dict = d.to_dict()
    # Must be JSON-serializable (no dataclass leaking)
    json.dumps(as_dict)  # raises if not serializable
    assert as_dict["chairman"] == "m1"
    assert as_dict["stage1_responses"]["resp_0"] == "r1"


def test_council_minority_warnings_extracted_from_synthesis():
    from core.council import Council
    c = Council(models=["m1"])
    synthesis = (
        "The consensus is X.\n"
        "WARNING: model A disagreed about Y.\n"
        "Confidence: high."
    )
    warnings = [l.strip() for l in synthesis.splitlines() if l.strip().lower().startswith("warning:")]
    assert any("disagreed" in w for w in warnings)
