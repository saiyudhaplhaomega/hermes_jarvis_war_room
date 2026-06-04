"""Memory trust tiers, decay, and promotion gate.

Adapted from gstack's "Memory v0" pattern. Project-scoped only.
"""
from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass


class TrustTier(str, enum.Enum):
    OBSERVED = "observed"
    USER_STATED = "user_stated"
    INFERRED = "inferred"
    CROSS_MODEL = "cross_model"


@dataclass
class MemoryItem:
    id: str
    content: str
    tier: TrustTier
    observed_at: float
    last_used_at: float
    project: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "tier": self.tier.value,
            "observed_at": self.observed_at,
            "last_used_at": self.last_used_at,
            "project": self.project,
        }


class PromotionGate:
    """Decide whether a memory item may be auto-applied."""

    def may_auto_apply(self, item: MemoryItem, *, current_project: str | None = None) -> bool:
        if item.tier is TrustTier.OBSERVED:
            return True
        if item.tier is TrustTier.USER_STATED:
            if current_project and item.project and current_project != item.project:
                return False
            return True
        return False


class ConfidenceDecay:
    def __init__(self, half_life_seconds: float) -> None:
        if half_life_seconds <= 0:
            raise ValueError("half_life_seconds must be positive")
        self.half_life_seconds = half_life_seconds

    def confidence(self, item: MemoryItem, *, now: float | None = None) -> float:
        now = now if now is not None else time.time()
        if item.tier is TrustTier.USER_STATED or item.tier is TrustTier.OBSERVED:
            return 1.0
        age = max(0.0, now - item.observed_at)
        return 0.5 ** (age / self.half_life_seconds)
