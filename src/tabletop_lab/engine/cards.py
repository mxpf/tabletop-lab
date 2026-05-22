from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    """Generic immutable card identity."""

    id: str
    name: str
