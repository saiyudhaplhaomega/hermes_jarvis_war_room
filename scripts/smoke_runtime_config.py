#!/usr/bin/env python3
"""Regression checks for Jarvis dashboard runtime wiring.

These checks intentionally avoid printing secrets. They validate that systemd starts
both backend and SPA with the same EnvironmentFile and that the SPA uses the real
proxy server, not python -m http.server.
"""
from __future__ import annotations

import re
from pathlib import Path

USER_SYSTEMD = Path.home() / ".config/systemd/user"
BACKEND_SERVICE = USER_SYSTEMD / "jarvis-dashboard.service"
SPA_SERVICE = USER_SYSTEMD / "jarvis-dashboard-static.service"
ENV_FILE = Path.home() / ".config/jarvis-dashboard/dashboard.env"
BACKEND_DIR = Path.home() / ".hermes/profiles/jarvis/plugins/jarvis-dashboard/backend"
SPA_SERVER = Path.home() / ".hermes/profiles/jarvis/plugins/jarvis-dashboard/spa_server.py"
DIST_DIR = Path.home() / ".hermes/profiles/jarvis/plugins/jarvis-dashboard/frontend-react/dist"
HERMES_PYTHON = Path.home() / ".hermes/hermes-agent/venv/bin/python3"


def read(path: Path) -> str:
    assert path.exists(), f"missing required file: {path}"
    return path.read_text()


def test_backend_service_uses_hermes_python_and_env_file() -> None:
    text = read(BACKEND_SERVICE)
    assert f"EnvironmentFile={ENV_FILE}" in text
    assert str(HERMES_PYTHON) in text
    assert "-m uvicorn server:app" in text
    assert "--workers 1" in text
    assert f"WorkingDirectory={BACKEND_DIR}" in text
    assert "JARVIS_DASHBOARD_DEV_TOKEN=" not in text
    assert "/jarvis-dashboard/venv/bin" not in text


def test_spa_service_uses_proxy_server_and_env_file() -> None:
    text = read(SPA_SERVICE)
    assert f"EnvironmentFile={ENV_FILE}" in text
    assert str(HERMES_PYTHON) in text
    assert str(SPA_SERVER) in text
    assert "8503" in text
    assert str(DIST_DIR) in text
    assert "python3 -m http.server" not in text
    assert "JARVIS_DASHBOARD_DEV_TOKEN=" not in text


def test_env_file_exists_but_secret_not_placeholder() -> None:
    text = read(ENV_FILE).strip()
    assert re.match(r"^JARVIS_DASHBOARD_DEV_TOKEN=.+$", text)
    value = text.split("=", 1)[1]
    assert len(value) >= 16
    assert "..." not in value
    assert "REDACTED" not in value.upper()


def test_spa_server_redacts_sensitive_query_logs() -> None:
    text = read(SPA_SERVER)
    assert "def _redact_url" in text
    assert "[REDACTED]" in text
    assert "log_message" in text
    namespace: dict[str, object] = {}
    exec(compile(text, str(SPA_SERVER), "exec"), namespace)
    redacted = namespace["_redact_url"]("GET /api/plugins/jarvis-dashboard/v1/chat?token=supersecret&project=x HTTP/1.1")
    assert "supersecret" not in redacted
    assert "token=[REDACTED]&project=x HTTP/1.1" in redacted


def test_frontend_does_not_log_tokenized_urls() -> None:
    client = read(Path.home() / ".hermes/profiles/jarvis/plugins/jarvis-dashboard/frontend-react/src/api/client.ts")
    chat = read(Path.home() / ".hermes/profiles/jarvis/plugins/jarvis-dashboard/frontend-react/src/contexts/ChatContext.tsx")
    assert "console.log('API GET:'" not in client
    assert "console.log('API GET response:'" not in client
    assert "[ChatContext] chat response" not in chat


if __name__ == "__main__":
    failures: list[str] = []
    for test in [
        test_backend_service_uses_hermes_python_and_env_file,
        test_spa_service_uses_proxy_server_and_env_file,
        test_env_file_exists_but_secret_not_placeholder,
        test_spa_server_redacts_sensitive_query_logs,
        test_frontend_does_not_log_tokenized_urls,
    ]:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:  # noqa: BLE001 - smoke script reports concise failures
            failures.append(f"FAIL {test.__name__}: {exc}")
    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    print("runtime config smoke: PASS")
