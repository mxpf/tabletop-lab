from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MinorAction = Literal["stabilize", "divert"]


@dataclass(frozen=True)
class UndersightAction:
    player_id: int
    play_card_id: str | None = None
    play_position: tuple[int, int] | None = None
    allocate_card_id: str | None = None
    discharge_die_ids: tuple[int, ...] = ()
    minor_action: MinorAction | None = None
    minor_die_id: int | None = None
    minor_target_card_id: str | None = None
    action_type: str = "Turn"
