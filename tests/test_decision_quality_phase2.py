from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_decision_quality_artifacts_exist_and_name_required_rules():
    required = [
        ROOT / "decisions" / "brief-template.md",
        ROOT / "decisions" / "classifier.md",
        ROOT / "decisions" / "record-schema.json",
        ROOT / "decisions" / "scoped-agent-token-design.md",
        ROOT / "CLAUDE.md",
    ]
    for path in required:
        assert path.exists(), f"missing {path}"


def test_decision_brief_template_has_gstack_required_fields_and_split_rule():
    text = (ROOT / "decisions" / "brief-template.md").read_text()
    for phrase in [
        "D-ID",
        "Context",
        "ELI10",
        "Stakes",
        "Recommendation",
        "Options",
        "Risks",
        "Reversibility",
        "Acceptance",
        "split-if-5+",
    ]:
        assert phrase in text


def test_classifier_defines_three_classes_and_user_challenge_hard_stop():
    text = (ROOT / "decisions" / "classifier.md").read_text()
    assert "Mechanical" in text
    assert "Taste" in text
    assert "User Challenge" in text
    assert "never override Saiyudh" in text
    assert "Boss+Manager cannot override" in text


def test_record_schema_validates_minimal_decision_record_shape():
    schema = json.loads((ROOT / "decisions" / "record-schema.json").read_text())
    assert schema["type"] == "object"
    for field in ["decision_id", "decision_class", "context", "recommendation", "options", "status"]:
        assert field in schema["required"]
    assert set(schema["properties"]["decision_class"]["enum"]) == {"mechanical", "taste", "user_challenge"}


def test_repo_claude_guidance_contains_phase2_behavioral_gates():
    text = (ROOT / "CLAUDE.md").read_text()
    assert "User Challenge" in text
    assert "Never override Saiyudh" in text
    assert "file:line" in text
    assert "quoted text" in text
    assert "split-if-5+" in text
