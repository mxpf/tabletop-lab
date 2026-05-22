from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .cards import LedgerCard, StakeCard
from .variants import BlackLedgerVariant


@dataclass
class Commitment:
    owner: int
    stake: StakeCard
    face_up: bool = False


@dataclass
class LineSlot:
    card: LedgerCard
    commitments: list[Commitment] = field(default_factory=list)


@dataclass
class PlayerState:
    player_id: int
    hand: list[StakeCard]
    spent: list[StakeCard] = field(default_factory=list)
    tableau: list[LedgerCard] = field(default_factory=list)
    closed_accounts: dict[str, list[LedgerCard]] = field(default_factory=dict)
    heat: int = 0


@dataclass
class BlackLedgerState:
    variant: BlackLedgerVariant
    players: list[PlayerState]
    deck: list[LedgerCard]
    line: list[LineSlot]
    discard: list[LedgerCard] = field(default_factory=list)
    furnace: list[LedgerCard] = field(default_factory=list)
    current_player: int = 0
    first_player: int = 0
    turn_count: int = 0
    round_turns_remaining: int | None = None
    end_triggered: bool = False
    end_condition: str | None = None
    seed: int | None = None
    metrics_data: dict[str, Any] = field(default_factory=dict)
    action_counts: Counter[str] = field(default_factory=Counter)
    turn_counts: Counter[int] = field(default_factory=Counter)
    action_counts_by_player: dict[int, Counter[str]] = field(default_factory=dict)
    ledger_won_counts: Counter[int] = field(default_factory=Counter)
    claim_win_counts: Counter[int] = field(default_factory=Counter)
    furnace_win_counts: Counter[int] = field(default_factory=Counter)
    last_revealed: LedgerCard | None = None


@dataclass(frozen=True)
class VisibleCommitment:
    owner: int
    count: int
    face_up_values: tuple[int, ...]
    hidden_count: int


@dataclass(frozen=True)
class VisibleLineSlot:
    card: LedgerCard
    index: int
    commitments: tuple[VisibleCommitment, ...]


@dataclass(frozen=True)
class VisiblePlayer:
    player_id: int
    hand_count: int
    spent_count: int
    tableau: tuple[LedgerCard, ...]
    closed_accounts: tuple[str, ...]
    heat: int


@dataclass(frozen=True)
class VisibleState:
    viewer_id: int
    current_player: int
    line: tuple[VisibleLineSlot, ...]
    players: tuple[VisiblePlayer, ...]
    own_hand_values: tuple[int, ...]
    own_spent_values: tuple[int, ...]
    deck_count: int
    discard_count: int
    furnace_count: int
