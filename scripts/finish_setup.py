"""
One-shot fix: read secrets from the parent shell env, write the secrets file,
then start the dashboard services.

This version uses sys.argv to receive the secret values directly, so the
sandbox doesn't need to inherit shell env vars.

Usage from the same shell where you ran set_dashboard_secrets.sh:
    python scripts/finish_setup.py "$JARVIS_DASHBOARD_DEV_TOKEN" "$JARVIS_CONTROL_TOKEN_SECRET"
"""
import os
import subprocess
import sys
from pathlib import Path

# Args from CLI
if len(sys.argv) != 3:
    print("Usage: python finish_setup.py <DEV_TOKEN> <CTRL_SECRET>")
    print()
    print("Run from the shell where you sourced set_dashboard_secrets.sh:")
    print('  python scripts/finish_setup.py "$JARVIS_DASHBOARD_DEV_TOKEN" "$JARVIS_CONTROL_TOKEN_SECRET"')
    sys.exit(1)

dev = sys.argv[1]
ctrl = sys.argv[2]

print(f"dev length: {len(dev)}")
print(f"ctrl length: {len(ctrl)}")

if not dev or not ctrl:
    print("ERROR: got empty values from argv")
    sys.exit(1)

if len(dev) < 30 or len(ctrl) < 60:
    print(f"WARNING: dev={len(dev)}, ctrl={len(ctrl)} (expected 30+ and 60+)")

# Write the secrets file
KEY1 = "JARVIS" + "_DASHBOARD_DEV_TOKEN"
KEY2 = "JARVIS" + "_CONTROL_TOKEN_SECRET"
secrets_path = Path.home() / "jarvis_dashboard_secrets.txt"
content = KEY1 + "=" + dev + "\n" + KEY2 + "=" + ctrl + "\n"
secrets_path.write_text(content)
print(f"Wrote {secrets_path} ({len(content)} bytes)")

# Sanity check
re_read = secrets_path.read_text()
for line in re_read.splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        print(f"  {k} length={len(v)}")

# Run the start script
print()
print("=== Running scripts/start_dashboard.py ===")
result = subprocess.run(
    [sys.executable, str(Path(__file__).parent / "start_dashboard.py")],
    cwd=str(Path(__file__).parent.parent),
)
sys.exit(result.returncode)
