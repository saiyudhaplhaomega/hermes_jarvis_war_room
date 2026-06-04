"""Release report validator."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class ReleaseValidator:
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report

    def validate(self) -> list[str]:
        errors: list[str] = []
        for required in ("phase", "timestamp", "commands", "gates", "artifacts"):
            if required not in self.report:
                errors.append(f"missing required field: {required}")

        commands = self.report.get("commands") or []
        if not isinstance(commands, list) or not commands:
            errors.append("commands must be a non-empty list")
        for index, command in enumerate(commands):
            for field in ("name", "command", "exit_code"):
                if field not in command:
                    errors.append(f"commands[{index}].{field} missing")
            if "exit_code" in command and not isinstance(command["exit_code"], int):
                errors.append(f"commands[{index}].exit_code must be an integer (got {type(command['exit_code']).__name__})")

        gates = self.report.get("gates") or []
        if not isinstance(gates, list) or not gates:
            errors.append("gates must be a non-empty list")
        for index, gate in enumerate(gates):
            for field in ("name", "passed"):
                if field not in gate:
                    errors.append(f"gates[{index}].{field} missing")

        artifacts = self.report.get("artifacts") or []
        for index, artifact in enumerate(artifacts):
            for field in ("path", "sha256"):
                if field not in artifact:
                    errors.append(f"artifacts[{index}].{field} missing")
            sha = artifact.get("sha256")
            if isinstance(sha, str) and not SHA256_PATTERN.match(sha):
                errors.append(f"artifacts[{index}].sha256 must be 64 hex chars")
        return errors
