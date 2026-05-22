from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    action_type: str
    player_id: int
