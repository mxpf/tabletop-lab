from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .cards import Department, UndersightCard
from .variants import UndersightVariant


@dataclass
class BoundDie:
    die_id: int
    owner: int
    card_id: str
    value: int = 1


@dataclass
class TableauCard:
    card: UndersightCard
    position: tuple[int, int]
    owner: int | None = None
    spillover_tokens: int = 0
    tilted_next_time: bool = False
    owner_bonus_claimed_round: set[int] = field(default_factory=set)


@dataclass
class PlayerState:
    player_id: int
    department: Department
    hand: list[UndersightCard]
    deck: list[UndersightCard] = field(default_factory=list)
    discard: list[UndersightCard] = field(default_factory=list)
    gems: int = 0
    influence: int = 0
    anomalies: int = 0
    waivers: int = 0
    vp: int = 0
    active_used: bool = False
    reduced_minor_used: bool = False


@dataclass
class UndersightState:
    variant: UndersightVariant
    players: list[PlayerState]
    tableau: dict[str, TableauCard]
    dice: dict[int, BoundDie] = field(default_factory=dict)
    idle_dice: list[int] = field(default_factory=list)
    current_player: int = 0
    first_player: int = 0
    turn_count: int = 0
    round_count: int = 1
    severance_count: int = 0
    end_triggered: bool = False
    end_condition: str | None = None
    round_turns_remaining: int | None = None
    seed: int | None = None
    metrics_data: Counter[str] = field(default_factory=Counter)
    action_counts: Counter[str] = field(default_factory=Counter)
    turn_counts: Counter[int] = field(default_factory=Counter)
    action_counts_by_player: dict[int, Counter[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class VisiblePlayer:
    player_id: int
    department_id: str
    hand_count: int
    deck_count: int
    discard_count: int
    gems: int
    influence: int
    anomalies: int
    waivers: int
    vp: int


@dataclass(frozen=True)
class VisibleTableauCard:
    card: UndersightCard
    position: tuple[int, int]
    owner: int | None
    spillover_tokens: int
    tilted_next_time: bool
    dice: tuple[BoundDie, ...]


@dataclass(frozen=True)
class VisibleState:
    viewer_id: int
    current_player: int
    round_count: int
    severance_count: int
    idle_dice_count: int
    players: tuple[VisiblePlayer, ...]
    tableau: tuple[VisibleTableauCard, ...]
    own_hand: tuple[UndersightCard, ...]
    metrics_hint: dict[str, Any]
