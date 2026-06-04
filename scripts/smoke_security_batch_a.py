#!/usr/bin/env python3
import asyncio
import json
import sys
from http.client import HTTPConnection

import websockets

HOST = "127.0.0.1"
PORT = 8512
TOKEN = "test-token"
BASE = "/api/plugins/jarvis-dashboard/v1"


def request(method, path, headers=None, body=None):
    conn = HTTPConnection(HOST, PORT, timeout=10)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read().decode("utf-8", errors="replace")
    headers_out = dict(resp.getheaders())
    conn.close()
    return resp.status, headers_out, data


async def ws_check(cookie):
    uri = f"ws://{HOST}:{PORT}{BASE}/ws"
    async with websockets.connect(uri, additional_headers={"Cookie": cookie}) as ws:
        first = await asyncio.wait_for(ws.recv(), timeout=5)
        payload = json.loads(first)
        assert payload.get("type") == "snapshot", payload


def header(headers, name):
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def main():
    status, headers, body = request("GET", f"{BASE}/ready", {"Authorization": f"Bearer {TOKEN}"})
    assert status == 200, (status, body)
    assert "test-token" not in body

    status, headers, body = request("GET", f"{BASE}/ready?token={TOKEN}")
    assert status == 401, (status, body)

    status, headers, body = request("POST", f"{BASE}/auth/session", {"Authorization": f"Bearer {TOKEN}"})
    assert status == 200, (status, body)
    cookie = header(headers, "Set-Cookie")
    assert cookie and "HttpOnly" in cookie, cookie
    assert "test-token" not in body

    status, headers, _body = request("OPTIONS", f"{BASE}/ready", {
        "Origin": "http://127.0.0.1:8503",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
    })
    assert status == 200, status
    assert header(headers, "Access-Control-Allow-Origin") == "http://127.0.0.1:8503", headers

    status, headers, _body = request("OPTIONS", f"{BASE}/ready", {
        "Origin": "http://43.131.26.109:8503",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
    })
    assert header(headers, "Access-Control-Allow-Origin") is None, headers

    asyncio.run(ws_check(cookie))
    print("TEMP_BACKEND_SMOKE_PASS")


if __name__ == "__main__":
    main()
