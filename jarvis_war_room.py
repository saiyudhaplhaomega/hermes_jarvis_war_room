#!/usr/bin/env python3
"""
Jarvis War Room — desktop launcher.

Boots both servers (FastAPI backend on :8502, Vite preview on :8503),
opens the dashboard in the user's default browser, and stays running
with a live log panel so the user can see what's happening.

Two modes:
  python jarvis_war_room.py            # GUI mode (default) — tk window + log
  python jarvis_war_room.py --headless # CLI mode — no window, just log to stdout

GUI controls:
  Start  /  Stop  — boot or tear down both servers
  Open Browser    — pop the dashboard in the default browser
  Restart All     — kill + relaunch both
  Clear Log       — wipe the log panel

Clean shutdown:
  Closing the window, Ctrl+C, or pressing Stop kills both subprocesses
  and releases ports 8502/8503.

Environment:
  Reads .env.local at the project root for JARVIS_DASHBOARD_DEV_TOKEN
  and JARVIS_CONTROL_TOKEN_SECRET, then exports them so the backend
  picks them up. Sets JARVIS_CLI_PROVIDER=auto so the chat route
  can fall back to local codex/claude CLIs.

Run with no arguments from the project root, or pass --headless to
embed in CI / systemd / etc.
"""
from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from queue import Empty, Queue
from tkinter import scrolledtext, ttk
from typing import Optional

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
VITE_BIN = ROOT / "frontend-react" / "node_modules" / "vite" / "bin" / "vite.js"
NODE_BIN = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs" / "node.exe"
if not NODE_BIN.exists():
    # fall back to whatever's on PATH
    NODE_BIN = Path(
        subprocess.check_output(["where", "node"], text=True, encoding="utf-8", errors="ignore")
        .strip()
        .splitlines()[0]
    )
BACKEND_PORT = 8502
FRONTEND_PORT = 8503
DASHBOARD_URL = f"http://127.0.0.1:{FRONTEND_PORT}/"
HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/api/plugins/jarvis-dashboard/health"
ENV_FILE = ROOT / ".env.local"


# ─── helpers ────────────────────────────────────────────────────────────
def _log_path() -> Path:
    p = ROOT / "state" / "launcher.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read_env_file() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_FILE.exists():
        return out
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _port_listening(port: int) -> bool:
    """Check whether anything is listening on 127.0.0.1:<port>."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        except OSError:
            return False


def _kill_port(port: int) -> None:
    """Kill whatever is listening on 127.0.0.1:<port> (Windows).

    On the Hermes desktop GUI host, processes may be owned by a different
    logon session (the Hermes parent). `taskkill` requires privileges to
    signal those, which we may or may not have. We log the failure rather
    than swallow it so the launcher user knows to investigate.
    """
    if not _port_listening(port):
        return
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, encoding="utf-8", errors="ignore"
        )
    except Exception as e:
        print(f"[launcher] netstat failed: {e}")
        return
    pids: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if f":{port} " not in line and not line.endswith(f":{port}"):
            continue
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        pid = parts[-1]
        if not pid.isdigit():
            continue
        pids.append(pid)
    for pid in pids:
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", pid],
                capture_output=True,
                timeout=5,
                text=True,
            )
            if result.returncode != 0:
                print(
                    f"[launcher] taskkill /F /T /PID {pid} returned "
                    f"rc={result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
                )
            else:
                print(f"[launcher] killed stale pid {pid} holding :{port}")
        except Exception as e:
            print(f"[launcher] taskkill pid {pid} raised: {e}")
    # Give the OS a moment to actually release the port
    deadline = time.time() + 2.0
    while time.time() < deadline and _port_listening(port):
        time.sleep(0.1)


def _frontend_dist_ready() -> bool:
    p = ROOT / "frontend-react" / "dist" / "index.html"
    return p.exists() and p.stat().st_size > 0


# ─── server controller ──────────────────────────────────────────────────


def _pidfile_path() -> Path:
    """Path to the file that records the launcher's child PIDs.

    Survives across crashes so the next launch can reap orphans.
    """
    p = ROOT / "state" / "launcher.children.pid"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


class Servers:
    """Owns the two child processes and streams their output to subscribers."""

    def __init__(self, log_sink):
        self.backend: Optional[subprocess.Popen] = None
        self.frontend: Optional[subprocess.Popen] = None
        self.log_sink = log_sink
        self.env = os.environ.copy()
        env = _read_env_file()
        for k, v in env.items():
            self.env[k] = v
        self.env.setdefault("JARVIS_CLI_PROVIDER", "auto")
        # ensure we tear down children if the launcher itself dies
        atexit.register(self.stop)
        # signal handlers — fire BEFORE atexit on Windows when the process is
        # killed externally (taskkill /F, Hermes "process kill", Ctrl+Break).
        # Without these, atexit may not run and children leak holding the ports.
        if os.name == "nt":
            try:
                signal.signal(signal.SIGBREAK, self._signal_stop)
            except (AttributeError, ValueError):
                pass
        try:
            signal.signal(signal.SIGTERM, self._signal_stop)
        except (AttributeError, ValueError):
            pass

    def _signal_stop(self, signum, frame):  # noqa: ARG002
        try:
            self.log_sink(f"[servers] received signal {signum}, stopping children")
        except Exception:
            pass
        self.stop()
        # Don't sys.exit — let atexit / interpreter teardown run, and let the
        # GUI's signal handler (if installed) finish its after-callback.

    def _spawn(
        self,
        label: str,
        cmd: list[str],
        cwd: Optional[Path] = None,
    ) -> subprocess.Popen:
        self.log_sink(f"[{label}] $ {' '.join(cmd)}")
        creationflags = 0
        if os.name == "nt":
            # CREATE_NEW_PROCESS_GROUP so we can send Ctrl+Break / kill cleanly
            creationflags = 0x00000200
        return subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
            creationflags=creationflags,
        )

    def start(self) -> None:
        if self.backend or self.frontend:
            self.log_sink("[servers] already running; stop first")
            return
        if not PYTHON.exists():
            self.log_sink(f"[servers] FATAL: {PYTHON} not found")
            return
        if not _frontend_dist_ready():
            self.log_sink(
                "[servers] dist/index.html missing — run scripts/inject_runtime_config.py first"
            )
        # Sweep stale child PIDs from any previous crashed run
        self._reap_stale_pidfile()
        # Reap anything currently holding our ports
        _kill_port(BACKEND_PORT)
        _kill_port(FRONTEND_PORT)
        try:
            self.backend = self._spawn(
                "backend",
                [
                    str(PYTHON),
                    "-m",
                    "uvicorn",
                    "backend.server:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(BACKEND_PORT),
                ],
                cwd=ROOT,
            )
            threading.Thread(
                target=self._pump,
                args=(self.backend, "backend"),
                daemon=True,
            ).start()
        except Exception as e:
            self.log_sink(f"[servers] backend spawn failed: {e}")
            self.backend = None
        # Frontend
        if VITE_BIN.exists():
            try:
                self.frontend = self._spawn(
                    "frontend",
                    [str(NODE_BIN), str(VITE_BIN), "preview",
                     "--port", str(FRONTEND_PORT), "--host", "127.0.0.1"],
                    cwd=ROOT / "frontend-react",
                )
                threading.Thread(
                    target=self._pump,
                    args=(self.frontend, "frontend"),
                    daemon=True,
                ).start()
            except Exception as e:
                self.log_sink(f"[servers] frontend spawn failed: {e}")
                self.frontend = None
        else:
            self.log_sink(f"[servers] FATAL: {VITE_BIN} not found")
        # Record child PIDs so a future launcher can reap them if this one
        # is hard-killed (Hermes process kill, OOM, etc.).
        self._write_pidfile()

    def stop(self) -> None:
        """Tear down both children. Safe to call multiple times."""
        for name, proc in (("backend", self.backend), ("frontend", self.frontend)):
            if not proc:
                continue
            pid = proc.pid
            if proc.poll() is None:
                self.log_sink(f"[servers] stopping {name} (pid={pid})")
                # First try: gentle terminate via taskkill (no /F).
                # Falls through to /F if the child is stuck.
                try:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/T", "/PID", str(pid)],
                            capture_output=True,
                            timeout=3,
                        )
                    else:
                        proc.terminate()
                except Exception as e:
                    self.log_sink(f"[servers] gentle kill {name} failed: {e}")
                # Give it 2s to exit cleanly
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.log_sink(f"[servers] {name} didn't exit, force-killing")
                    try:
                        if os.name == "nt":
                            subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", str(pid)],
                                capture_output=True,
                                timeout=3,
                            )
                        else:
                            proc.kill()
                    except Exception as e:
                        self.log_sink(f"[servers] force kill {name} failed: {e}")
        self.backend = None
        self.frontend = None
        # Clear the pidfile so a future start doesn't try to reap live children
        try:
            _pidfile_path().unlink(missing_ok=True)
        except Exception:
            pass

    def _write_pidfile(self) -> None:
        """Record child PIDs so a future launcher can reap them if this one
        was hard-killed (Hermes process kill, OOM, etc.) before stop() ran."""
        try:
            lines = []
            if self.backend:
                lines.append(f"backend={self.backend.pid}")
            if self.frontend:
                lines.append(f"frontend={self.frontend.pid}")
            if lines:
                _pidfile_path().write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as e:
            self.log_sink(f"[servers] pidfile write failed: {e}")

    def _reap_stale_pidfile(self) -> None:
        """If a previous launcher died hard, its child PIDs are recorded here.
        Reap them so the new servers can bind the ports."""
        pf = _pidfile_path()
        if not pf.exists():
            return
        try:
            for line in pf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                name, _, pid_str = line.partition("=")
                if not pid_str.isdigit():
                    continue
                pid = int(pid_str)
                self.log_sink(f"[servers] reaping stale {name} (pid={pid}) from previous run")
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=3,
                    )
                except Exception:
                    pass
        except Exception as e:
            self.log_sink(f"[servers] pidfile reap failed: {e}")
        finally:
            try:
                pf.unlink(missing_ok=True)
            except Exception:
                pass

    def restart(self) -> None:
        self.stop()
        time.sleep(0.5)
        self.start()

    def _pump(self, proc: subprocess.Popen, label: str) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            self.log_sink(f"[{label}] {line.rstrip()}")
        rc = proc.poll()
        self.log_sink(f"[{label}] exited rc={rc}")

    def is_running(self) -> bool:
        return bool(
            (self.backend and self.backend.poll() is None)
            or (self.frontend and self.frontend.poll() is None)
        )


# ─── GUI ────────────────────────────────────────────────────────────────
class App:
    BG = "#0b1220"
    FG = "#e5e7eb"
    OK = "#10b981"
    BAD = "#ef4444"
    WARN = "#f59e0b"

    def __init__(self):
        self.servers = Servers(self._enqueue_log)
        self.log_q: Queue[str] = Queue()
        self.root = tk.Tk()
        self.root.title("Jarvis War Room")
        self.root.geometry("960x620")
        self.root.minsize(720, 480)
        self.root.configure(bg=self.BG)
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # signal handlers so Ctrl-C in the terminal also stops servers cleanly
        signal.signal(signal.SIGINT, lambda *_: self.root.after(0, self._on_close))
        self.root.after(80, self._drain_logs)
        self.root.after(800, self._poll_status)
        # auto-start on launch (user can press Stop)
        self.root.after(300, self._cmd_start)

    def _build_ui(self) -> None:
        # Top toolbar
        bar = tk.Frame(self.root, bg=self.BG, padx=10, pady=8)
        bar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(
            bar,
            text="🛡 Hermes / JARVIS WAR ROOM",
            font=("Segoe UI", 12, "bold"),
            fg="#7dd3fc",
            bg=self.BG,
        ).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            bar,
            text="● stopped",
            font=("Consolas", 10, "bold"),
            fg=self.WARN,
            bg=self.BG,
        )
        self.status_lbl.pack(side=tk.RIGHT, padx=(8, 0))
        self.port_lbl = tk.Label(
            bar,
            text=f"backend  :{BACKEND_PORT}  ·  frontend :{FRONTEND_PORT}",
            font=("Consolas", 9),
            fg="#94a3b8",
            bg=self.BG,
        )
        self.port_lbl.pack(side=tk.RIGHT)

        # Buttons
        btn_bar = tk.Frame(self.root, bg=self.BG, padx=10, pady=4)
        btn_bar.pack(side=tk.TOP, fill=tk.X)
        for label, cmd, color in [
            ("▶ Start", self._cmd_start, self.OK),
            ("■ Stop", self._cmd_stop, self.BAD),
            ("↻ Restart All", self._cmd_restart, "#3b82f6"),
            ("🌐 Open Browser", self._cmd_open, "#a855f7"),
            ("Clear Log", self._cmd_clear, "#6b7280"),
        ]:
            b = tk.Button(
                btn_bar,
                text=label,
                command=cmd,
                bg=color,
                fg="white",
                activebackground=color,
                activeforeground="white",
                bd=0,
                padx=12,
                pady=6,
                font=("Segoe UI", 9, "bold"),
            )
            b.pack(side=tk.LEFT, padx=(0, 6))

        # Log panel
        log_frame = tk.Frame(self.root, bg=self.BG, padx=10, pady=6)
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.log = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.NONE,
            bg="#020617",
            fg=self.FG,
            insertbackground=self.FG,
            font=("Consolas", 10),
            bd=0,
            highlightthickness=1,
            highlightbackground="#1e293b",
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        # tag styles
        self.log.tag_configure("backend", foreground="#7dd3fc")
        self.log.tag_configure("frontend", foreground="#a78bfa")
        self.log.tag_configure("meta", foreground="#fbbf24")
        self.log.tag_configure("err", foreground="#fca5a5")

    # commands
    def _cmd_start(self) -> None:
        _kill_port(BACKEND_PORT)
        _kill_port(FRONTEND_PORT)
        time.sleep(0.3)
        self._enqueue_log("[meta] starting servers…")
        self.servers.start()
        # give them a sec, then open browser
        self.root.after(2500, self._open_browser_if_ready)

    def _cmd_stop(self) -> None:
        self._enqueue_log("[meta] stopping servers…")
        self.servers.stop()
        _kill_port(BACKEND_PORT)
        _kill_port(FRONTEND_PORT)

    def _cmd_restart(self) -> None:
        self._enqueue_log("[meta] restarting…")
        self.servers.restart()
        self.root.after(2500, self._open_browser_if_ready)

    def _cmd_open(self) -> None:
        webbrowser.open(DASHBOARD_URL)

    def _cmd_clear(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def _open_browser_if_ready(self) -> None:
        if _port_listening(FRONTEND_PORT) and _port_listening(BACKEND_PORT):
            webbrowser.open(DASHBOARD_URL)
        else:
            self.root.after(1500, self._open_browser_if_ready)

    # status
    def _poll_status(self) -> None:
        backend_ok = _port_listening(BACKEND_PORT)
        frontend_ok = _port_listening(FRONTEND_PORT)
        if backend_ok and frontend_ok:
            text = "● running"
            color = self.OK
        elif self.servers.is_running():
            text = "● starting…"
            color = self.WARN
        else:
            text = "● stopped"
            color = self.WARN
        self.status_lbl.configure(text=text, fg=color)
        self.root.after(1000, self._poll_status)

    # log handling
    def _enqueue_log(self, line: str) -> None:
        self.log_q.put(line)
        try:
            with _log_path().open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _drain_logs(self) -> None:
        try:
            while True:
                line = self.log_q.get_nowait()
                self._append_log(line)
        except Empty:
            pass
        self.root.after(80, self._drain_logs)

    def _append_log(self, line: str) -> None:
        tag = "meta"
        if line.startswith("[backend]"):
            tag = "backend"
        elif line.startswith("[frontend]"):
            tag = "frontend"
        elif line.startswith("[err]") or "Traceback" in line or "ERROR" in line:
            tag = "err"
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, line + "\n", (tag,))
        self.log.see(tk.END)
        # cap log size to keep GUI snappy
        line_count = int(self.log.index("end-1c").split(".")[0])
        if line_count > 4000:
            self.log.delete("1.0", f"{line_count - 3000}.0")
        self.log.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        self._enqueue_log("[meta] window closing, stopping servers…")
        try:
            self.servers.stop()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


# ─── entry point ────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis War Room desktop launcher")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a window; just start servers and open browser.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open the browser (works with both modes).",
    )
    args = parser.parse_args()

    if not args.no_browser:
        # schedule open-browser
        threading.Timer(2.5, lambda: webbrowser.open(DASHBOARD_URL)).start()

    if args.headless:
        servers = Servers(print)
        try:
            servers.start()
            print(f"[launcher] running headless.  URLs:")
            print(f"  backend  http://127.0.0.1:{BACKEND_PORT}/api/plugins/jarvis-dashboard/health")
            print(f"  frontend http://127.0.0.1:{FRONTEND_PORT}/")
            print("press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[launcher] shutting down…")
            servers.stop()
            return 0
    else:
        App().run()
        return 0


if __name__ == "__main__":
    sys.exit(main())
