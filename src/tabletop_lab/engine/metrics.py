from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metrics:
    action_counts: Counter[str] = field(default_factory=Counter)
    counters: Counter[str] = field(default_factory=Counter)

    def action(self, action_type: str) -> None:
        self.action_counts[action_type] += 1

    def inc(self, key: str, amount: int = 1) -> None:
        self.counters[key] += amount

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_counts": dict(self.action_counts),
            **dict(self.counters),
        }
