"""Pluggable model invoker registry (D-2026-06-09, Phase 4 sub-task 4.2).

Tiny function-registry abstraction so the Council of Departments (and
anything else that needs to "ask a model") can resolve a
`(provider, model)` pair to an invoker function at runtime.

Design rules (per Phase 4 codex verdict):
- **No class hierarchy.** A function registry is enough for v1.
- **No abstract base classes** until real adapters need shared
  lifecycle/config (a YAGNI guard).
- **Stubs return synthetic template output** for `codex`, `ollama`,
  and `nemotron` so tests can exercise the full 3-stage council flow
  with no subprocess / network calls. The contract is
  `(provider, model, prompt, metadata) -> ModelResponse` — keeping
  metadata as a free-form dict so future adapters can carry
  temperature, max_tokens, etc. without breaking the signature.
- **Validation reuses `agent_growth._known_model_pairs()`** so the
  Council cannot ask for a `(provider, model)` pair that the rest
  of the system has not seen.

Load-bearing invariant: this module does NOT touch Hermes profile
configs. Pure in-process function dispatch + JSON-serializable
responses. Council decisions are persisted separately by the caller
(via `backend/api/council.py`).
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("jarvis.model_invoker")


# ---------------------------------------------------------------------------
# Adapter signature
# ---------------------------------------------------------------------------
# An adapter is just a callable with the right signature. We type-annotate
# it as a `ModelAdapter` for docs, but Python's duck typing means any
# callable with the right shape works (tests inject fakes trivially).
ModelAdapter = Callable[[str, str, str, Dict[str, Any]], "ModelResponse"]


@dataclass
class ModelResponse:
    """A single model's answer to a prompt.

    `response` is the model's free-form text. `model_metadata`
    carries the raw provider response (or our stub of it) for replay
    and audit. `latency_ms` is wall-clock from the adapter's POV.
    """
    provider: str
    model: str
    response: str
    model_metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
# `_ADAPTERS` is the global function registry. Keyed by `provider` (so
# one adapter handles all models for that provider, e.g. all `ollama:*`
# models go through the same HTTP call). Tests can `register_adapter()`
# a fake to inject deterministic responses.
_ADAPTERS: Dict[str, ModelAdapter] = {}


def register_adapter(provider: str, fn: ModelAdapter) -> None:
    """Register (or replace) the adapter for a provider.

    Provider names are lowercased on insert. Validates the name shape
    to catch typos at registration time rather than at first call.
    """
    if not isinstance(provider, str) or not re.match(r"^[a-z0-9_-]{1,32}$", provider):
        raise ValueError(f"invalid provider name: {provider!r}")
    _ADAPTERS[provider.lower()] = fn
    log.info("model_invoker.register provider=%s", provider)


def resolve_invoker(provider: str) -> ModelAdapter:
    """Look up the adapter for a provider. Raises KeyError on miss."""
    try:
        return _ADAPTERS[provider.lower()]
    except KeyError as e:
        raise KeyError(f"no adapter registered for provider={provider!r}. "
                       f"Known: {sorted(_ADAPTERS)}") from e


def known_providers() -> List[str]:
    return sorted(_ADAPTERS)


def invoke(
    provider: str,
    model: str,
    prompt: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ModelResponse:
    """Resolve and call the adapter. Latency is timed in-process."""
    fn = resolve_invoker(provider)
    meta = dict(metadata or {})
    t0 = time.time()
    try:
        resp = fn(provider, model, prompt, meta)
    except Exception as e:
        # Convert adapter errors into a structured ModelResponse so the
        # council runner can record a "vote error" rather than crashing
        # the whole stage. The runner can still see the exception class
        # in `model_metadata["error"]` and decide whether to retry or
        # skip.
        log.exception("model_invoker.invoke error provider=%s model=%s", provider, model)
        return ModelResponse(
            provider=provider,
            model=model,
            response=f"[adapter error: {type(e).__name__}: {e}]",
            model_metadata={**meta, "error": type(e).__name__, "error_msg": str(e)},
            latency_ms=int((time.time() - t0) * 1000),
        )
    # Normalize: if the adapter returned a dict, accept it; if it
    # returned a ModelResponse, accept it; anything else is a bug.
    if isinstance(resp, ModelResponse):
        if resp.latency_ms == 0:
            resp.latency_ms = int((time.time() - t0) * 1000)
        return resp
    if isinstance(resp, dict):
        return ModelResponse(
            provider=resp.get("provider", provider),
            model=resp.get("model", model),
            response=str(resp.get("response", "")),
            model_metadata={**meta, **resp.get("model_metadata", {})},
            latency_ms=resp.get("latency_ms", int((time.time() - t0) * 1000)),
        )
    raise TypeError(
        f"adapter for {provider!r} returned {type(resp).__name__}; "
        f"expected ModelResponse or dict"
    )


# ---------------------------------------------------------------------------
# Stub adapters (v1)
# ---------------------------------------------------------------------------
# These are deliberately tiny — they return template output that varies
# per model name so a 3-stage council produces visibly distinct
# stage1 perspectives in the replay log. Real adapters (Phase 5+) will
# replace these with HTTP calls; the contract is stable.

def _stub_codex(provider: str, model: str, prompt: str, metadata: Dict[str, Any]) -> ModelResponse:
    return ModelResponse(
        provider=provider, model=model,
        response=(
            f"[codex/{model} stub] Considering: {prompt[:140]}{'...' if len(prompt) > 140 else ''}. "
            f"Recommended action: analyze tradeoffs, then commit to the option with the fewest "
            f"long-term maintenance costs."
        ),
        model_metadata={"stub": "codex", "prompt_chars": len(prompt)},
    )


def _stub_ollama(provider: str, model: str, prompt: str, metadata: Dict[str, Any]) -> ModelResponse:
    return ModelResponse(
        provider=provider, model=model,
        response=(
            f"[ollama/{model} stub] Pragmatic take on: {prompt[:140]}{'...' if len(prompt) > 140 else ''}. "
            f"Recommended action: pick the simplest working solution; document the rollback."
        ),
        model_metadata={"stub": "ollama", "prompt_chars": len(prompt)},
    )


def _stub_nemotron(provider: str, model: str, prompt: str, metadata: Dict[str, Any]) -> ModelResponse:
    return ModelResponse(
        provider=provider, model=model,
        response=(
            f"[nemotron/{model} stub] Structured analysis of: {prompt[:140]}{'...' if len(prompt) > 140 else ''}. "
            f"Recommended action: list 3 risks, 3 mitigations, then pick the lowest-risk path."
        ),
        model_metadata={"stub": "nemotron", "prompt_chars": len(prompt)},
    )


# ---------------------------------------------------------------------------
# Real HTTP adapters (v1) — Ollama + Nemotron
# ---------------------------------------------------------------------------
# D-2026-06-09 (Phase 6): these were stubs in v1. They are real HTTP
# adapters now, calling Ollama's /api/generate and a Nemotron-compatible
# /api/generate endpoint. Both share the same payload shape
# (`{model, prompt, stream: false}`) per the codex verdict.
#
# `codex` stays a stub — there is no real codex API to call in v1. The
# user-locked architecture uses codex as the council chairman, and the
# runner already tolerates a missing/broken chairman (see
# `core/council_departments.py` stage-3 fallback synthesis). When a
# real codex endpoint lands in a future phase, the codex stub gets the
# same treatment.
import httpx as _httpx


# Env-driven base URLs with sane defaults. Tests override via
# `OLLAMA_BASE_URL` / `NEMOTRON_BASE_URL` (or by injecting a
# `httpx.MockTransport` via the `_httpx_client_factory` indirection).
def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _nemotron_base_url() -> str:
    return os.environ.get("NEMOTRON_BASE_URL", "http://localhost:8000").rstrip("/")


def _adapter_timeout_s(metadata: Dict[str, Any]) -> float:
    try:
        return float(metadata.get("timeout_s", 30.0))
    except (TypeError, ValueError):
        return 30.0


def _ollama_httpx_client_factory():
    """Returns a callable that produces an httpx.Client.

    Indirected so tests can swap in `httpx.MockTransport`. Per codex
    verdict: a new client per call; connection pooling is opt-in.
    """
    def _factory():
        return _httpx.Client(timeout=_adapter_timeout_s({}))
    return _factory


def _nemotron_httpx_client_factory():
    def _factory():
        return _httpx.Client(timeout=_adapter_timeout_s({}))
    return _factory


# Module-level factory indirections so tests can override.
_ollama_httpx_client_factory = _ollama_httpx_client_factory()
_nemotron_httpx_client_factory = _nemotron_httpx_client_factory()


def _http_ollama(provider: str, model: str, prompt: str, metadata: Dict[str, Any]) -> ModelResponse:
    """Real HTTP adapter for Ollama. POSTs to {OLLAMA_BASE_URL}/api/generate.

    Per codex verdict: best-effort — the caller (`invoke()`) catches
    exceptions and converts them to a structured `ModelResponse` with
    `model_metadata["error"]` set, so the council runner can still
    record a vote (with an error marker) rather than crashing.
    """
    url = f"{_ollama_base_url()}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    timeout = _adapter_timeout_s(metadata)
    try:
        with _ollama_httpx_client_factory() as client:
            resp = client.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        body = resp.json() if resp.content else {}
        # Ollama's /api/generate returns `{"response": "..."}`.
        return ModelResponse(
            provider=provider, model=model,
            response=str(body.get("response", "")),
            model_metadata={
                "stub": False,
                "endpoint": url,
                "ollama_eval_count": body.get("eval_count"),
                "ollama_eval_duration_ns": body.get("eval_duration"),
            },
        )
    except _httpx.HTTPError as e:
        # Re-raise so `invoke()` can convert it via the structured
        # error path. We deliberately do NOT swallow here — the
        # invoke() helper is the single chokepoint for adapter
        # error → ModelResponse.
        raise


def _http_nemotron(provider: str, model: str, prompt: str, metadata: Dict[str, Any]) -> ModelResponse:
    """Real HTTP adapter for Nemotron. POSTs to {NEMOTRON_BASE_URL}/api/generate.

    Same payload shape as Ollama (per codex verdict). Best-effort —
    see `_http_ollama` for the error model.
    """
    url = f"{_nemotron_base_url()}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    timeout = _adapter_timeout_s(metadata)
    try:
        with _nemotron_httpx_client_factory() as client:
            resp = client.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        body = resp.json() if resp.content else {}
        return ModelResponse(
            provider=provider, model=model,
            response=str(body.get("response", "")),
            model_metadata={
                "stub": False,
                "endpoint": url,
            },
        )
    except _httpx.HTTPError as e:
        raise


# Register the v1 adapters at import time. Replace these by calling
# `register_adapter()` with a different function (e.g. a real discord.py
# client wrapper) when the real network endpoints are wired.
register_adapter("codex", _stub_codex)
register_adapter("ollama", _http_ollama)
register_adapter("nemotron", _http_nemotron)


# ---------------------------------------------------------------------------
# Model pair validation
# ---------------------------------------------------------------------------
def _default_known_pairs() -> set[Tuple[str, str]]:
    """Default v1 (provider, model) allowlist.

    Falls back to a tiny explicit set when `agent_growth` cannot
    resolve (e.g. minimal test harnesses). The Council and the
    Agent Growth Studio share this allowlist so a `(provider, model)`
    accepted in `propose_agent` is also accepted in `council/ask`.
    """
    pairs: set[Tuple[str, str]] = {
        ("codex", "gpt-5.5"),
        ("ollama", "llama3.1:8b"),
        ("ollama", "qwen2.5:7b"),
        ("nemotron", "nemotron-mini:4b"),
    }
    try:
        from api.agent_growth import _known_model_pairs as _ag_pairs
        pairs.update(_ag_pairs())
    except Exception:
        pass
    return pairs


# Env-overridable allowlist, mainly for tests. Empty string disables
# the env override.
KNOWN_MODEL_PAIRS_OVERRIDE_ENV = "JARVIS_MODEL_INVOKER_KNOWN_PAIRS"


def known_model_pairs() -> set[Tuple[str, str]]:
    """Return the set of accepted (provider, model) pairs.

    The env-override is a comma-separated list of `provider:model`
    tokens, used by tests to inject extra pairs. The default union
    includes anything `agent_growth._known_model_pairs()` returns.
    """
    pairs = _default_known_pairs()
    env = os.environ.get(KNOWN_MODEL_PAIRS_OVERRIDE_ENV, "").strip()
    if not env:
        return pairs
    for token in env.split(","):
        token = token.strip()
        if not token or ":" not in token:
            continue
        provider, model = token.split(":", 1)
        provider = provider.strip().lower()
        model = model.strip()
        if provider and model:
            pairs.add((provider, model))
    return pairs


def is_known_model_pair(provider: str, model: str) -> bool:
    return (provider.lower(), model) in known_model_pairs()

class TuningEngine:
    """Continuous learning via LoRA and reinforcement learning."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.feedback_log = os.path.expanduser(
            f"~/.hermes/memory/projects/{self.project_id}/feedback.jsonl"
        )

    def log_feedback(self, task_id: str, outcome: str, model: str) -> None:
        """Log feedback for continuous learning."""
        with open(self.feedback_log, "a") as f:
            f.write(json.dumps({
                "task_id": task_id,
                "outcome": outcome,
                "model": model,
                "timestamp": int(time.time())
            }) + "\n")

    def fine_tune(self) -> None:
        """Trigger LoRA fine-tuning (e.g., via MiniMax M3)."""
        # Stub: Call MiniMax M3 API for fine-tuning
        pass
