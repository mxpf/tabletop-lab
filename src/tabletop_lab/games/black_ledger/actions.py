from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class CoverIntent:
    player_id: int
    line_index: int
    action_type: str = "Cover"


@dataclass(frozen=True)
class CoverAction:
    player_id: int
    line_index: int
    stake_ids: tuple[str, ...]
    action_type: str = "Cover"


@dataclass(frozen=True)
class ClaimAction:
    player_id: int
    line_index: int
    action_type: str = "Claim"


@dataclass(frozen=True)
class CallAction:
    player_id: int
    line_index: int
    target_player: int
    action_type: str = "Call"


@dataclass(frozen=True)
class CountAction:
    player_id: int
    action_type: str = "Count"


BlackLedgerAction = Union[CoverIntent, CoverAction, ClaimAction, CallAction, CountAction]
