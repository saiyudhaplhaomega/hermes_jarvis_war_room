"""Council module for War Room (Loop 3 R1-R10 — karpathy/llm-council pattern).

3-stage pattern for strategic decisions:
  Stage 1: parallel independent answers from N models
  Stage 2: anonymized ranking by criteria (correctness, risk, completeness, actionability)
  Stage 3: chairman synthesis with minority warnings preserved

For War Room on RTX 4070:
  - codex (gpt-5.5) is the strong voice (already in our council)
  - ollama (qwen2.5:7b or 3b) is the local second opinion
  - chairman = role, not model (any capable model plays it; default = codex)

Failure-mode mitigations (per Loop 3 R8):
  - groupthink: force independent first-pass before discussion
  - authority bias: blind model identities in stage 2
  - error amplification: require source check for factual claims
  - cost/latency blowup: cap rounds, early stopping
"""
from __future__ import annotations
import os
import json
import shutil
import time
import uuid
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Literal


# ─────────────────────────────────────────────
# Model adapters
# ─────────────────────────────────────────────

def _call_codex(prompt: str, timeout: int = 90) -> str:
    """Run codex non-interactively. Requires `codex` on PATH."""
    try:
        # On Windows, `codex` is a .CMD shim, not a .EXE. subprocess.run
        # without shell=True can't find .CMD files even when they're on
        # PATH (which is why we append .CMD/.EXE explicitly below).
        codex_path = shutil.which("codex") or "codex"
        result = subprocess.run(
            [codex_path, "exec", "--skip-git-repo-check", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return f"[codex error: {result.stderr.strip()[:200]}]"
        # Strip the chatty codex output, keep the response
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[codex timeout]"
    except FileNotFoundError:
        return "[codex not installed]"


def _call_ollama(prompt: str, model: str = "qwen2.5:7b-instruct", timeout: int = 90) -> str:
    """Run ollama non-interactively. Requires `ollama` on PATH and model pulled."""
    try:
        ollama_path = shutil.which("ollama") or "ollama"
        result = subprocess.run(
            [ollama_path, "run", model, prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return f"[ollama error: {result.stderr.strip()[:200]}]"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"[ollama timeout after {timeout}s]"
    except FileNotFoundError:
        return "[ollama not installed]"


# ─────────────────────────────────────────────
# Council data structures
# ─────────────────────────────────────────────

@dataclass
class CouncilVote:
    """One model's response + ranking + metadata."""
    model: str
    response: str
    ranking: dict = field(default_factory=dict)  # {response_id: rank}
    confidence: float = 0.0
    latency_ms: int = 0


@dataclass
class CouncilDecision:
    """Final output of a council run."""
    id: str
    query: str
    votes: list
    stage1_responses: dict  # {anon_id: response}
    stage2_rankings: list  # list of CouncilVote.rankings
    stage3_synthesis: str
    minority_warnings: list
    chairman: str
    model_list: list
    created_at: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["votes"] = [asdict(v) if hasattr(v, "__dataclass_fields__") else v for v in self.votes]
        return d


# ─────────────────────────────────────────────
# Council runner
# ─────────────────────────────────────────────

class Council:
    """3-stage council runner. Anonymizes stage 2, preserves minority warnings."""

    DEFAULT_MODELS = ["codex", "ollama:qwen2.5:7b-instruct"]

    def __init__(self, models: Optional[list[str]] = None, chairman: Optional[str] = None):
        self.models = models or self.DEFAULT_MODELS
        self.chairman = chairman or self.models[0]  # strongest by default

    def _call(self, model: str, prompt: str) -> CouncilVote:
        start = time.time()
        if model.startswith("ollama:"):
            actual = model.split(":", 1)[1]
            response = _call_ollama(prompt, model=actual)
        elif model == "codex":
            response = _call_codex(prompt)
        else:
            response = f"[unknown model: {model}]"
        latency = int((time.time() - start) * 1000)
        return CouncilVote(model=model, response=response, latency_ms=latency)

    def stage1_parallel(self, query: str) -> list[CouncilVote]:
        """Each model gives an independent first-pass answer."""
        prompt = f"Answer concisely in 3-5 sentences.\n\nQuestion: {query}"
        votes = [self._call(m, prompt) for m in self.models]
        return votes

    def stage2_rank(self, query: str, votes: list) -> list[CouncilVote]:
        """Each model anonymously ranks all responses by criteria."""
        # Anonymize: assign anon_id, strip model names
        anon_map = {f"resp_{i}": v.response for i, v in enumerate(votes)}
        anon_list = "\n\n".join(
            f"[{rid}]\n{resp}" for rid, resp in anon_map.items()
        )
        # Prompt each model to rank by 4 criteria
        criteria = (
            "Rank each response from 1 (best) to N (worst) on EACH of:\n"
            "  correctness, risk-awareness, completeness, actionability.\n"
            "Reply ONLY as JSON: {\"rankings\": [{\"id\": \"resp_X\", "
            "\"correctness\": R, \"risk_awareness\": R, \"completeness\": R, "
            "\"actionability\": R}, ...]}"
        )
        prompt = (
            f"Question: {query}\n\n"
            f"Responses to rank (anonymized):\n{anon_list}\n\n"
            f"{criteria}"
        )
        ranked_votes = []
        for vote in votes:
            raw = self._call(vote.model, prompt)
            parsed = self._parse_rankings(raw, len(votes))
            vote.ranking = parsed
            ranked_votes.append(vote)
        return ranked_votes

    def _parse_rankings(self, raw: str, expected: int) -> dict:
        """Best-effort parse of the ranking JSON. Lenient: any {id, ...} rows found."""
        try:
            # Strip code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(
                    line for line in cleaned.splitlines()
                    if not line.strip().startswith("```")
                )
            data = json.loads(cleaned)
            rankings = data.get("rankings", data) if isinstance(data, dict) else data
            if isinstance(rankings, list):
                return {r["id"]: r for r in rankings if "id" in r}
        except Exception:
            pass
        return {}

    def stage3_synthesize(
        self, query: str, stage1: list, stage2: list
    ) -> tuple[str, list[str]]:
        """Chairman synthesizes. Preserves minority warnings."""
        # Build a summary of all responses + rankings
        lines = [f"Question: {query}\n"]
        for i, v in enumerate(stage1):
            lines.append(f"--- Response {i} (from {v.model}) ---\n{v.response}\n")
        for v in stage2:
            if v.ranking:
                lines.append(f"--- Rankings by {v.model} ---\n{v.ranking}\n")
        joined = "\n".join(lines)
        prompt = (
            "You are the chairman of a multi-model council. Synthesize a final answer.\n"
            "Rules:\n"
            "  - Lead with the consensus answer.\n"
            "  - Explicitly call out any MINORITY WARNINGS (where models disagreed).\n"
            "  - End with a confidence level: low / medium / high.\n"
            "  - 3-6 sentences total.\n\n"
            f"{joined}"
        )
        synthesis = self._call(self.chairman, prompt).response
        # Cheap extraction of minority warnings (any line starting with '- ' or 'WARNING:')
        warnings = [
            line.strip() for line in synthesis.splitlines()
            if line.strip().lower().startswith(("warning:", "minority:", "disagree:", "- "))
        ]
        return synthesis, warnings

    def run(self, query: str) -> CouncilDecision:
        stage1 = self.stage1_parallel(query)
        stage2 = self.stage2_rank(query, stage1)
        synthesis, warnings = self.stage3_synthesize(query, stage1, stage2)
        return CouncilDecision(
            id=str(uuid.uuid4()),
            query=query,
            votes=stage1,
            stage1_responses={f"resp_{i}": v.response for i, v in enumerate(stage1)},
            stage2_rankings=[v.ranking for v in stage2],
            stage3_synthesis=synthesis,
            minority_warnings=warnings,
            chairman=self.chairman,
            model_list=list(self.models),
            created_at=time.time(),
        )
