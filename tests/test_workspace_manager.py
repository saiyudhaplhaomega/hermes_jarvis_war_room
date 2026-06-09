"""Tests for workspace_manager (D-2026-06-08-w, project directory fix).

The bug: BASE_DIR was hard-coded to Path.home() / "projects" — on Windows
that resolves to C:\\Users\\saiyu\\projects\\, NOT the user's expected
location of C:\\Users\\saiyu\\Desktop\\projects\\KI_projects\\hermes_projects\\.

Fix: BASE_DIR is now read from the HERMES_PROJECTS_DIR env var, defaulting
to ~/Desktop/projects/KI_projects/hermes_projects (matching the rest of
the War Room's project layout).

This test asserts:
  1. When HERMES_PROJECTS_DIR is unset, the Windows default is
     ~/Desktop/projects/KI_projects/hermes_projects
  2. When HERMES_PROJECTS_DIR is set, BASE_DIR honors it
  3. The clone path, list path, and remove path all use BASE_DIR
  4. Unix-only `du` and `rm -rf` calls are replaced with cross-platform
     equivalents (shutil.disk_usage + shutil.rmtree)
  5. Workspace name validation still rejects path traversal
"""
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_default_base_dir_on_windows():
    """When HERMES_PROJECTS_DIR is unset, default to KI_projects/hermes_projects."""
    env = {k: v for k, v in os.environ.items() if k != "HERMES_PROJECTS_DIR"}
    with patch.dict(os.environ, env, clear=True):
        if "workspace_manager" in sys.modules:
            del sys.modules["workspace_manager"]
        import workspace_manager
        expected = Path.home() / "Desktop" / "projects" / "KI_projects" / "hermes_projects"
        assert workspace_manager.BASE_DIR == expected, (
            f"Expected {expected}, got {workspace_manager.BASE_DIR}"
        )


def test_explicit_base_dir_from_env():
    """When HERMES_PROJECTS_DIR is set, BASE_DIR honors it."""
    custom = r"C:\some\other\path"
    with patch.dict(os.environ, {"HERMES_PROJECTS_DIR": custom}):
        if "workspace_manager" in sys.modules:
            del sys.modules["workspace_manager"]
        import workspace_manager
        assert workspace_manager.BASE_DIR == Path(custom)


def test_validate_name_rejects_path_traversal():
    from workspace_manager import _validate_name
    import pytest
    for bad in ("../etc", "foo/bar", "..", "", "a" * 65, "foo bar", "foo;bar"):
        with pytest.raises(ValueError):
            _validate_name(bad)


def test_validate_name_accepts_safe():
    from workspace_manager import _validate_name
    assert _validate_name("my-project_v2") == "my-project_v2"
    assert _validate_name("simple") == "simple"


def test_resolve_path_rejects_traversal(tmp_path, monkeypatch):
    """Path traversal must be blocked even if base exists."""
    monkeypatch.setenv("HERMES_PROJECTS_DIR", str(tmp_path))
    if "workspace_manager" in sys.modules:
        del sys.modules["workspace_manager"]
    import workspace_manager
    # Create a real workspace dir
    (tmp_path / "good").mkdir()
    # Inside-workspace path: OK
    p = workspace_manager._resolve_path("good", "src/file.py")
    assert p.exists() or str(p).endswith("src\\file.py") or str(p).endswith("src/file.py")
    # Path traversal attempt: must raise
    import pytest
    with pytest.raises((PermissionError, ValueError)):
        workspace_manager._resolve_path("good", "../../../etc/passwd")


def test_list_workspaces_uses_disk_usage_not_du(tmp_path, monkeypatch):
    """`du -sm` is Unix-only. list_workspaces should use shutil.disk_usage or
    a cross-platform size calculation, not call `du`."""
    monkeypatch.setenv("HERMES_PROJECTS_DIR", str(tmp_path))
    if "workspace_manager" in sys.modules:
        del sys.modules["workspace_manager"]
    import workspace_manager
    # Make a fake workspace with a known size
    ws = tmp_path / "fake-ws"
    ws.mkdir()
    (ws / ".git").mkdir()
    (ws / "README.md").write_text("x" * 1024)
    result = workspace_manager.list_workspaces()
    assert any(w["name"] == "fake-ws" for w in result)
    item = next(w for w in result if w["name"] == "fake-ws")
    # size_mb should be a number ≥ 0, NOT an exception from missing `du`
    assert isinstance(item["size_mb"], (int, float))
    assert item["size_mb"] >= 0
    assert item["has_git"] is True


def test_remove_workspace_uses_shutil_not_rm(tmp_path, monkeypatch):
    """`rm -rf` is Unix-only. remove_workspace should use shutil.rmtree."""
    monkeypatch.setenv("HERMES_PROJECTS_DIR", str(tmp_path))
    if "workspace_manager" in sys.modules:
        del sys.modules["workspace_manager"]
    import workspace_manager
    ws = tmp_path / "to-remove"
    ws.mkdir()
    (ws / "file.txt").write_text("bye")
    result = workspace_manager.remove_workspace("to-remove")
    assert result == {"removed": "to-remove"}
    assert not ws.exists()


def test_clone_workspace_rejects_non_github_urls(tmp_path, monkeypatch):
    """Clone must reject anything that isn't a github.com HTTPS URL."""
    monkeypatch.setenv("HERMES_PROJECTS_DIR", str(tmp_path))
    if "workspace_manager" in sys.modules:
        del sys.modules["workspace_manager"]
    import workspace_manager
    import pytest
    for bad in (
        "https://gitlab.com/foo/bar",
        "http://github.com/foo/bar",   # http not https
        "git@github.com:foo/bar.git",  # ssh, not https
        "https://github.com/foo",      # no repo name
        "https://github.com/foo/bar/extra/stuff",
    ):
        with pytest.raises(ValueError):
            workspace_manager.clone_workspace(bad)


def test_clone_workspace_derives_name_from_url(tmp_path, monkeypatch):
    """When name is not provided, derive it from the URL's last segment."""
    monkeypatch.setenv("HERMES_PROJECTS_DIR", str(tmp_path))
    if "workspace_manager" in sys.modules:
        del sys.modules["workspace_manager"]
    import workspace_manager
    # Mock subprocess.run to fake a successful clone
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Create the target dir ourselves to simulate what git clone would do
        def fake_run(cmd, *a, **kw):
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
            (target / ".git").mkdir()
            return MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = fake_run
        result = workspace_manager.clone_workspace(
            "https://github.com/octocat/Hello-World"
        )
        assert result["name"] == "Hello-World"
        assert (tmp_path / "Hello-World").exists()


def test_clone_workspace_rejects_existing_target(tmp_path, monkeypatch):
    """If the target dir already exists, clone must refuse (no clobber)."""
    monkeypatch.setenv("HERMES_PROJECTS_DIR", str(tmp_path))
    if "workspace_manager" in sys.modules:
        del sys.modules["workspace_manager"]
    import workspace_manager
    import pytest
    (tmp_path / "already-here").mkdir()
    with pytest.raises(FileExistsError):
        workspace_manager.clone_workspace(
            "https://github.com/octocat/already-here", name="already-here"
        )
