#!/usr/bin/env python3
"""Read the 2 secrets from C:\\Users\\saiyu\\jarvis_dashboard_secrets.txt,
write .env.local, build the SPA, kill old processes, and start the
backend + static SPA server on ports 8502 and 8503.

This avoids the Vite dev server entirely so the browser URL is stable.
"""
import os
import sys
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room")
SECRETS_FILE = Path.home() / "jarvis_dashboard_secrets.txt"
ENV_LOCAL = ROOT / "frontend-react" / ".env.local"
DIST = ROOT / "frontend-react" / "dist"

# Pick a Python interpreter that actually has uvicorn installed.
# The project venv may be missing uvicorn; the Hermes venv has it.
PYTHON = Path(r"C:\Users\saiyu\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe")
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def _load_secrets():
    if not SECRETS_FILE.exists():
        print(f"ERROR: {SECRETS_FILE} not found.")
        print("Create it with:\n")
        print("    JARVIS_DASHBOARD_DEV_TOKEN=your-token-here")
        print("    JARVIS_CONTROL_TOKEN_SECRET=your-secret-here")
        sys.exit(1)

    values = {}
    for line in SECRETS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip()

    dev = values.get("JARVIS_DASHBOARD_DEV_TOKEN", "")
    ctrl = values.get("JARVIS_CONTROL_TOKEN_SECRET", "")
    if not dev:
        print("ERROR: JARVIS_DASHBOARD_DEV_TOKEN is empty or missing")
        sys.exit(1)
    if not ctrl:
        print("ERROR: JARVIS_CONTROL_TOKEN_SECRET is empty or missing")
        sys.exit(1)
    return dev, ctrl


def _write_env(dev: str) -> None:
    ENV_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    ENV_LOCAL.write_text(
        "# Vite env - auto-loaded by Vite on start. Local dev only.\n"
        "VITE_API_BASE=/api/plugins/jarvis-dashboard/v1\n"
        f"VITE_TOKEN={dev}\n"
        "VITE_WS_URL=ws://localhost:8503/api/plugins/jarvis-dashboard/v1/ws\n"
    )
    print(f"Wrote {ENV_LOCAL}")


def _kill_port(port: int) -> None:
    try:
        out = subprocess.check_output(
            f'netstat -ano | findstr ":{port}.*LISTENING"',
            shell=True, text=True, stderr=subprocess.DEVNULL,
        )
        for line in out.strip().splitlines():
            pid = line.split()[-1]
            print(f"  Killing PID {pid} on port {port}")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(f"  nothing on port {port}")


def _build_frontend() -> None:
    print("\n=== Building frontend-react SPA ===")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(ROOT / "frontend-react"),
        shell=True,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        print("\nERROR: frontend build failed")
        sys.exit(1)
    print("  build OK")


def _wait_for(url: str, expected_status: int = 200, timeout: int = 30) -> bool:
    for _ in range(timeout):
        try:
            r = urllib.request.urlopen(url, timeout=2)
            if r.status == expected_status:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main() -> None:
    dev, ctrl = _load_secrets()
    _write_env(dev)
    _build_frontend()

    print("\n=== Killing old processes on 8502 / 8503 ===")
    for port in [8502, 8503]:
        _kill_port(port)
    time.sleep(2)

    print("\n=== Starting FastAPI backend on port 8502 ===")
    env = os.environ.copy()
    env["JARVIS_CONTROL_TOKEN_SECRET"] = ctrl
    env["JARVIS_DASHBOARD_DEV_TOKEN"] = dev
    subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "backend.server:app", "--host", "127.0.0.1", "--port", "8502"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
    )

    print("\n=== Starting static SPA server on port 8503 ===")
    subprocess.Popen(
        [str(PYTHON), "spa_server.py", "8503", str(DIST), "127.0.0.1"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
    )

    print("\n=== Waiting for services ===")
    if _wait_for("http://127.0.0.1:8502/api/plugins/jarvis-dashboard/health"):
        print("  Backend (8502):  OK")
    else:
        print("  Backend (8502):  FAILED")
        sys.exit(1)

    if _wait_for("http://127.0.0.1:8503/"):
        print("  SPA     (8503):  OK")
    else:
        print("  SPA     (8503):  FAILED")
        sys.exit(1)

    print("\n=== Dashboard ready ===")
    print("Open http://127.0.0.1:8503/ in your browser")


if __name__ == "__main__":
    main()
