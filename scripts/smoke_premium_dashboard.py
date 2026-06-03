#!/usr/bin/env python3
"""Smoke test the premium Jarvis dashboard role overlay and SPA runtime."""
from __future__ import annotations

import json
import os
import socket
import sys
import urllib.error
import urllib.request

TOKEN = os.environ.get("JARVIS_DASHBOARD_DEV_TOKEN", "")
BASE = "http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1"


def get(path: str) -> tuple[int, str]:
    url = f"{BASE}{path}?token={TOKEN}"
    try:
        with urllib.request.urlopen(url, timeout=5) as res:
            return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    failures: list[str] = []
    if not TOKEN:
        failures.append("JARVIS_DASHBOARD_DEV_TOKEN is not set")
    for port in (8502, 8503):
        if not port_open(port):
            failures.append(f"port {port} is not listening")
    status, body = get("/roles")
    if status != 200:
        failures.append(f"GET /roles returned {status}: {body[:120]}")
    else:
        data = json.loads(body)
        if data.get("writes_profile_configs") is not False:
            failures.append("/roles did not declare writes_profile_configs=false")
        if not data.get("roles"):
            failures.append("/roles returned no mappings")
        if not data.get("available_agents"):
            failures.append("/roles returned no available agents")
    status, body = get("/models")
    if status != 200:
        failures.append(f"GET /models returned {status}: {body[:120]}")
    else:
        if "models" not in json.loads(body):
            failures.append("/models missing models key")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8503/war-room", timeout=5) as res:
            html = res.read().decode("utf-8", "replace")
            if res.status != 200:
                failures.append(f"SPA /war-room returned {res.status}")
            required_html = [
                "Jarvis War Room Dashboard",
                "id=\"root\"",
                "window.__CONFIG__",
                "/assets/index-",
            ]
            for marker in required_html:
                if marker not in html:
                    failures.append(f"React SPA /war-room missing marker: {marker}")
            forbidden = ["Jarvis War Room v1.1.0", "chat-history", "cmd-input", "cmd-send", "python3 -m http.server", "43.131.26.109:8502", "TOKEN=\"dev\""]
            for marker in forbidden:
                if marker in html:
                    failures.append(f"React SPA /war-room still contains forbidden marker: {marker}")

            import re
            bundle_paths = re.findall(r'src="(/assets/index-[^"]+\.js)(?:\?v=\d+)?"', html)
            if not bundle_paths:
                failures.append("React SPA bundle path not found")
            else:
                bundle_url = f"http://127.0.0.1:8503{bundle_paths[0]}"
                with urllib.request.urlopen(bundle_url, timeout=5) as bundle_res:
                    bundle = bundle_res.read().decode("utf-8", "replace")
                required_bundle = [
                    "Open dashboard command menu",
                    "Agent Growth Studio",
                    "Provider/model dropdowns, skill feed, proposals, graveyard",
                    "/agents/skills",
                    "/skills",
                    "PROFILE-SAFE OVERLAY",
                ]
                for marker in required_bundle:
                    if marker not in bundle:
                        failures.append(f"React bundle missing marker: {marker}")
    except Exception as exc:
        failures.append(f"SPA /war-room failed: {exc}")
    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
        return 1
    print("PASS premium dashboard runtime smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
