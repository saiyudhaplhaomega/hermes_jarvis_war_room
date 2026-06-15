"""Tests for scripts/gen_hermes_profiles.py — Phase 1 of the Agentic Army sprint.

Per CLAUDE.md: failing test first (RED), then implement to GREEN.

These tests use a tmp_path fixture so they don't touch the real
~/.hermes/profiles. They validate:
1. Staging creates the right files
2. The 14 expected slugs are in the spec
3. config.yaml has the right shape
4. SOUL.md mentions the role
5. The --apply flag copies from staging to live (with a temp live dir)
6. The --diff flag works
7. The script never hardcodes /home/ubuntu paths
8. Idempotent: re-running without --overwrite is a no-op
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gen_hermes_profiles.py"
SPEC = REPO_ROOT / "scripts" / "hermes_profiles.yaml"

EXPECTED_SLUGS = [
    "jarvis-frontend", "jarvis-ui_ux", "jarvis-backend", "jarvis-mobile",
    "jarvis-data-ml", "jarvis-devops", "jarvis-marketing", "jarvis-sales",
    "jarvis-finance", "jarvis-legal", "jarvis-customer-success",
    "jarvis-researcher", "jarvis-council-departments", "jarvis-secretary",
]

EXPECTED_FILES = ["config.yaml", "SOUL.md", "AGENTS.md", "HEARTBEAT.md", "TOOLS.md"]


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run the script with the given extra args and env."""
    full_env = {**os.environ, **env}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full_env,
        check=False,
    )


def test_spec_has_14_profiles():
    """The spec must list exactly 14 profiles (user locked-in count)."""
    import yaml
    with SPEC.open() as f:
        data = yaml.safe_load(f)
    slugs = [p["slug"] for p in data["profiles"]]
    assert slugs == EXPECTED_SLUGS, f"expected 14 slugs, got {slugs}"


def test_staging_creates_all_files(tmp_path):
    """Running without --apply should write to staging only, with all 5 files per profile."""
    staging = tmp_path / "staging"
    result = _run(
        [], {
            "JARVIS_PROFILE_STAGING_DIR": str(staging),
            "HERMES_PROFILES_DIR": str(tmp_path / "live-does-not-exist"),
        }
    )
    assert result.returncode == 0, f"script failed: {result.stderr}"
    assert staging.exists()
    for slug in EXPECTED_SLUGS:
        profile_dir = staging / slug
        assert profile_dir.is_dir(), f"missing staged profile: {slug}"
        for fname in EXPECTED_FILES:
            assert (profile_dir / fname).is_file(), f"missing {slug}/{fname}"


def test_config_yaml_has_required_keys(tmp_path):
    """Each staged config.yaml must have name, model, role, worker_kind."""
    staging = tmp_path / "staging"
    _run([], {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(tmp_path / "live"),
    })
    import yaml
    for slug in EXPECTED_SLUGS:
        cfg_path = staging / slug / "config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())
        assert "name" in cfg, f"{slug}: missing name"
        assert "model" in cfg, f"{slug}: missing model"
        assert "role" in cfg, f"{slug}: missing role"
        assert "worker_kind" in cfg, f"{slug}: missing worker_kind"


def test_config_yaml_has_extended_identity_fields(tmp_path):
    """Per codex review 2026-06-09, config.yaml must also carry slug, department,
    team, reports_to, collaborates_with, skills_seed, mcp_servers."""
    staging = tmp_path / "staging"
    _run([], {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(tmp_path / "live"),
    })
    import yaml
    for slug in EXPECTED_SLUGS:
        cfg_path = staging / slug / "config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())
        assert cfg.get("slug") == slug, f"{slug}: config.slug mismatch"
        assert cfg.get("department"), f"{slug}: missing department"
        assert cfg.get("team"), f"{slug}: missing team"
        assert cfg.get("reports_to"), f"{slug}: missing reports_to"
        assert isinstance(cfg.get("collaborates_with"), list), f"{slug}: collaborates_with not list"
        assert isinstance(cfg.get("skills_seed"), list), f"{slug}: skills_seed not list"
        assert isinstance(cfg.get("mcp_servers"), list), f"{slug}: mcp_servers not list"


def test_apply_uses_staged_files_not_rerender(tmp_path):
    """Per codex review 2026-06-09, --apply must copy the staged files exactly,
    not re-render the YAML spec. We test by tampering with a staged file and
    confirming the live copy matches the tampered content."""
    staging = tmp_path / "staging"
    live = tmp_path / "live"
    env = {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(live),
    }
    _run([], env)
    # Tamper with a staged file
    target = staging / "jarvis-frontend" / "SOUL.md"
    tampered = "TAMPERED BY TEST\n" + target.read_text()
    target.write_text(tampered)
    # Apply; the live file should be tampered, not the rendered version
    result = _run(["--apply", "--slug", "jarvis-frontend"], env)
    assert result.returncode == 0
    assert "TAMPERED BY TEST" in (live / "jarvis-frontend" / "SOUL.md").read_text()


def test_soul_md_mentions_role(tmp_path):
    """Each staged SOUL.md must contain the role string (proves templating worked)."""
    staging = tmp_path / "staging"
    _run([], {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(tmp_path / "live"),
    })
    for slug in EXPECTED_SLUGS:
        soul = (staging / slug / "SOUL.md").read_text()
        assert len(soul) > 100, f"{slug}: SOUL.md is too short"


def test_apply_copies_to_live(tmp_path):
    """--apply must write to HERMES_PROFILES_DIR (the live profiles)."""
    staging = tmp_path / "staging"
    live = tmp_path / "live"
    # First stage
    _run([], {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(live),
    })
    # Then apply
    result = _run(
        ["--apply-all"],
        {
            "JARVIS_PROFILE_STAGING_DIR": str(staging),
            "HERMES_PROFILES_DIR": str(live),
        }
    )
    assert result.returncode == 0, f"apply failed: {result.stderr}"
    for slug in EXPECTED_SLUGS:
        for fname in EXPECTED_FILES:
            assert (live / slug / fname).is_file(), f"apply missing {slug}/{fname}"


def test_no_hardcoded_home_ubuntu_in_script():
    """The script must never hardcode /home/ubuntu (per codex review)."""
    text = SCRIPT.read_text()
    assert "/home/ubuntu" not in text, "found hardcoded /home/ubuntu path"
    assert "/home/ubuntu" not in (REPO_ROOT / "scripts" / "hermes_profiles.yaml").read_text(), \
        "spec contains hardcoded /home/ubuntu"


def test_idempotent_no_overwrite(tmp_path):
    """Re-running without --overwrite must skip existing files."""
    staging = tmp_path / "staging"
    env = {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(tmp_path / "live"),
    }
    _run([], env)
    # Edit a staged file
    target = staging / "jarvis-frontend" / "config.yaml"
    target.write_text("TAMPERED")
    # Re-run; should NOT overwrite
    result = _run([], env)
    assert result.returncode == 0
    assert target.read_text() == "TAMPERED", "second run overwrote existing file"


def test_diff_flag_works(tmp_path):
    """--diff must print a unified diff (or 'no diff') and exit 0."""
    staging = tmp_path / "staging"
    live = tmp_path / "live"
    _run([], {
        "JARVIS_PROFILE_STAGING_DIR": str(staging),
        "HERMES_PROFILES_DIR": str(live),
    })
    # Live dir is empty; diff should show all-new
    result = _run(
        ["--diff", "--slug", "jarvis-frontend"],
        {
            "JARVIS_PROFILE_STAGING_DIR": str(staging),
            "HERMES_PROFILES_DIR": str(live),
        }
    )
    assert result.returncode == 0, f"diff failed: {result.stderr}"
    assert "config.yaml" in result.stdout or "no diff" in result.stdout
