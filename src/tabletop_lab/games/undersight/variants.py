from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UndersightVariant:
    name: str
    player_count: int = 3
    dice_count: int = 34
    starting_hand_size: int = 3
    vp_target: int = 20
    severance_limit: int = 7
    idle_dice_end_threshold: int = 4
    first_player: int | None = None


VARIANTS: dict[str, UndersightVariant] = {
    "base_3p": UndersightVariant("base_3p"),
    "base_2p": UndersightVariant("base_2p", player_count=2),
    "base_4p": UndersightVariant("base_4p", player_count=4),
    "quick_2p": UndersightVariant("quick_2p", player_count=2, vp_target=8, severance_limit=4),
}


def get_variant(name: str) -> UndersightVariant:
    try:
        return VARIANTS[name]
    except KeyError as exc:
        raise ValueError(f"unknown Undersight variant: {name}") from exc
