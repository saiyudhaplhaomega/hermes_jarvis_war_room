from pathlib import Path
import json
import time

ROOT = Path(__file__).resolve().parents[1]


def test_release_report_schema_and_required_fields():
    schema = json.loads((ROOT / "ops" / "release-report.schema.json").read_text())
    assert schema["type"] == "object"
    for field in ["phase", "timestamp", "commands", "gates", "artifacts"]:
        assert field in schema["required"]
    assert schema["properties"]["commands"]["items"]["required"] == ["name", "command", "exit_code"]
    assert schema["properties"]["gates"]["items"]["required"] == ["name", "passed"]
    assert schema["properties"]["artifacts"]["items"]["required"] == ["path", "sha256"]


def test_iron_law_fresh_evidence_rejects_stale_results(tmp_path):
    from ops.iron_law import FreshEvidenceGate

    evidence = tmp_path / "last_tests.json"
    evidence.write_text(json.dumps({"timestamp": time.time(), "exit_code": 0}))
    gate = FreshEvidenceGate(evidence_file=evidence)

    src = tmp_path / "service.py"
    src.write_text("x = 1\n")

    older = time.time() - 60
    stale_evidence = tmp_path / "stale.json"
    stale_evidence.write_text(json.dumps({"timestamp": older}))
    stale_gate = FreshEvidenceGate(evidence_file=stale_evidence)
    assert gate.is_fresh(roots=[src]) is True
    assert stale_gate.is_fresh(roots=[src]) is False


def test_docs_coverage_gate_recognizes_tutorial_reference_and_howto():
    from ops.docs_coverage import DiataxisGate

    gate = DiataxisGate(docs_root=ROOT / "docs")
    missing = gate.missing_categories()
    assert "tutorial" not in missing
    assert "reference" not in missing
    assert "how-to" not in missing
    assert "explanation" not in missing

    # Sanity: when run against a fresh dir, all four are reported missing.
    empty_gate = DiataxisGate(docs_root=ROOT / "ops")
    empty_missing = empty_gate.missing_categories()
    assert set(empty_missing) == {"tutorial", "how-to", "reference", "explanation"}


def test_release_validator_reports_missing_exit_code():
    from ops.release import ReleaseValidator

    bad = {
        "phase": "phase3",
        "timestamp": "2026-06-04T00:00:00Z",
        "commands": [{"name": "pytest", "command": "pytest -q", "exit_code": None}],
        "gates": [{"name": "tests", "passed": True}],
        "artifacts": [{"path": "docs/TUTORIAL.md", "sha256": "x" * 64}],
    }
    v = ReleaseValidator(report=bad)
    errors = v.validate()
    assert any("exit_code" in e for e in errors)


def test_release_validator_passes_with_complete_report(tmp_path):
    from ops.release import ReleaseValidator

    good = {
        "phase": "phase3",
        "timestamp": "2026-06-04T00:00:00Z",
        "commands": [
            {"name": "pytest", "command": "pytest -q", "exit_code": 0, "output_snippet": "36 passed"},
        ],
        "gates": [
            {"name": "tests", "passed": True},
            {"name": "security_review", "passed": True},
            {"name": "tutorial", "passed": True},
            {"name": "obsidian", "passed": True},
        ],
        "artifacts": [
            {"path": "docs/TUTORIAL.md", "sha256": "a" * 64},
            {"path": "docs/REFERENCE.md", "sha256": "b" * 64},
        ],
    }
    v = ReleaseValidator(report=good)
    assert v.validate() == []


def test_reference_doc_lists_modules_with_file_line_refs():
    text = (ROOT / "docs" / "REFERENCE.md").read_text()
    assert "## Modules" in text
    assert "backend/server.py" in text
    assert "frontend-react/src/contexts/ConnectionContext.tsx" in text
