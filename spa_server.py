#!/usr/bin/env python3
"""
SPA static server with API proxy + index.html fallback + 1-hour auto-shutdown.
Frontend pings /inactivity-ping every 30s to reset timer.
API calls to /api/plugins/... are proxied to backend on localhost:8502.
"""
import http.server, socketserver, os, sys, mimetypes, threading, time, re
import urllib.parse
import urllib.request, json as json_mod

def _arg_int(index: int, default: int) -> int:
    try:
        return int(sys.argv[index])
    except (IndexError, TypeError, ValueError):
        return default


PORT = _arg_int(1, 8503)
ROOT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "frontend-react", "dist")
HOST = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
INDEX = os.path.join(ROOT, "index.html")
BACKEND = "http://127.0.0.1:8502"

IDLE_SHUTDOWN_SECONDS = 3600
WARNING_SECONDS = 300
CHECK_INTERVAL = 30

last_request_time = time.time()
httpd_ref = [None]
shutdown_scheduled = [False]

RUNTIME_CONFIG = """window.__CONFIG__ = {
  API_BASE: '/api/plugins/jarvis-dashboard/v1',
  TOKEN: %s,
  WS_URL: (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/api/plugins/jarvis-dashboard/v1/ws'
};""" % json_mod.dumps(os.environ.get("JARVIS_DASHBOARD_DEV_TOKEN", ""))

def _content_security_policy() -> str:
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "connect-src 'self' ws://127.0.0.1:8503 ws://localhost:8503 wss://127.0.0.1:8503 wss://localhost:8503; "
        "img-src 'self' data: https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com;"
    )


def _inject_config(html: bytes) -> bytes:
    text = html.decode('utf-8')
    script = f'<script>{RUNTIME_CONFIG}</script>'
    ts = str(int(time.time()))
    text = re.sub(r'src="(/assets/[^"]+)"', f'src="\\1?v={ts}"', text)
    text = re.sub(r'href="(/assets/[^"]+)"', f'href="\\1?v={ts}"', text)
    match = re.search(r'(<script(?:\s+src|\s+type))', text, re.IGNORECASE)
    if match:
        pos = match.start()
        text = text[:pos] + script + '\n' + text[pos:]
    else:
        body_close = text.lower().find('</body>')
        if body_close != -1:
            text = text[:body_close] + script + '\n' + text[body_close:]
        else:
            text = text.replace('</body>', script + '\n</body>', 1)
    return text.encode('utf-8')

def _proxy_to_backend(handler):
    backend_url = f"{BACKEND}{handler.path}"
    body = None
    if handler.command in ('POST', 'PUT', 'PATCH'):
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length > 0:
            body = handler.rfile.read(content_length)

    req = urllib.request.Request(
        backend_url,
        data=body,
        method=handler.command,
        headers={k: v for k, v in handler.headers.items() if k.lower() not in ('host', 'content-length')},
    )
    if handler.headers.get('Content-Type'):
        req.add_header('Content-Type', handler.headers.get('Content-Type'))
    if handler.headers.get('Authorization'):
        req.add_header('Authorization', handler.headers.get('Authorization'))

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            handler.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in ('transfer-encoding', 'content-encoding', 'connection'):
                    handler.send_header(k, v)
            # Add CORS headers
            handler.send_header('Access-Control-Allow-Origin', 'http://localhost:5173')
            handler.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
            handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            handler.send_header('Access-Control-Allow-Credentials', 'true')
            handler.end_headers()
            handler.wfile.write(resp.read())
    except urllib.error.HTTPError as e:
        handler.send_response(e.code)
        for k, v in e.headers.items():
            handler.send_header(k, v)
        handler.end_headers()
        handler.wfile.write(e.read())
    except Exception as e:
        handler.send_response(502)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json_mod.dumps({'error': str(e)}).encode())

def _inactivity_watcher():
    while True:
        time.sleep(CHECK_INTERVAL)
        idle = time.time() - last_request_time
        if idle >= IDLE_SHUTDOWN_SECONDS and not shutdown_scheduled[0]:
            shutdown_scheduled[0] = True
            print(f"[INACTIVITY] No requests for {int(idle)}s. Shutting down in {WARNING_SECONDS}s...")
            time.sleep(WARNING_SECONDS)
            idle2 = time.time() - last_request_time
            if idle2 >= IDLE_SHUTDOWN_SECONDS:
                print("[INACTIVITY] Server shutting down now.")
                try:
                    if httpd_ref[0]:
                        httpd_ref[0].shutdown()
                except Exception:
                    pass
                os._exit(0)
            else:
                shutdown_scheduled[0] = False
                print("[INACTIVITY] Activity resumed — shutdown cancelled.")

watcher = threading.Thread(target=_inactivity_watcher, daemon=True)
watcher.start()

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        fpath = path.split('?',1)[0].split('#',1)[0]
        local = os.path.join(ROOT, fpath.lstrip('/'))
        if os.path.exists(local) and os.path.isfile(local):
            return local
        if os.path.exists(local + "/index.html"):
            return local + "/index.html"
        return INDEX

    def _dispatch(self):
        global last_request_time
        last_request_time = time.time()

        # Proxy API requests to backend
        if self.path.startswith('/api/plugins/'):
            _proxy_to_backend(self)
            return

        # Heartbeat endpoint
        if self.path == "/inactivity-ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            idle = time.time() - last_request_time + CHECK_INTERVAL
            remaining = max(0, IDLE_SHUTDOWN_SECONDS - (time.time() - last_request_time))
            self.wfile.write(b'{"pong": true, "idle_seconds": %d, "shutdown_in_seconds": %d}' % (
                int(time.time() - last_request_time), int(remaining)))
            return

        # Serve index.html with config injection
        is_index = self.path == '/' or self.path.startswith('/index.html') or self.path.startswith('/war-room')
        if is_index and os.path.exists(INDEX):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Security-Policy", _content_security_policy())
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            with open(INDEX, 'rb') as f:
                html = f.read()
            html = _inject_config(html)
            self.wfile.write(html)
            return

        super().do_GET()

    def do_GET(self): self._dispatch()
    def do_POST(self): self._dispatch()
    def do_PUT(self): self._dispatch()
    def do_PATCH(self): self._dispatch()
    def do_DELETE(self): self._dispatch()
    def do_OPTIONS(self): self._dispatch()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        if self.path.startswith("/_hc") or self.path == "/inactivity-ping":
            return
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(_redact_url(arg))
            else:
                safe_args.append(arg)
        super().log_message(fmt, *safe_args)

def _redact_url(value: str) -> str:
    """Redact sensitive query values before access logs reach journald."""
    return re.sub(
        r"([?&](?:token|api_key|key|password)=)[^&\s]+",
        r"\1[REDACTED]",
        value,
        flags=re.IGNORECASE,
    )

def main() -> None:
    os.chdir(ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((HOST, PORT), SPAHandler) as httpd:
        httpd_ref[0] = httpd
        print(f"SPA server at http://{HOST}:{PORT} serving {ROOT}")
        print(f"API proxy to {BACKEND}")
        print(f"Auto-shutdown after {IDLE_SHUTDOWN_SECONDS}s inactivity (warning at {IDLE_SHUTDOWN_SECONDS - WARNING_SECONDS}s)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
