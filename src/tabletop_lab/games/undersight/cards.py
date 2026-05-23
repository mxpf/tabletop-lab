from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CardKind(str, Enum):
    BASE = "base"
    ZONE = "zone"
    INSTALLATION = "installation"
    DIRECTIVE = "directive"


class RewardKind(str, Enum):
    GEMS = "gems"
    INFLUENCE = "influence"
    ANOMALY = "anomaly"
    VP = "vp"
    WAIVER = "waiver"


@dataclass(frozen=True)
class UndersightCard:
    id: str
    name: str
    kind: CardKind
    depth: int = 0
    discharge_reward: RewardKind | None = None
    reward_amount: int = 0
    owner_bonus: RewardKind | None = None
    owner_bonus_amount: int = 0
    escalation_bonus: int = 0
    binding_slots_per_player: int = 1
    creates_spillover: bool = True


@dataclass(frozen=True)
class Department:
    id: str
    name: str
    passive: str
    active: str


DEPARTMENTS: tuple[Department, ...] = (
    Department(
        "permits",
        "Zoning & Permits Division",
        "Placement-focused department. TODO: full placement reservation rules are card-driven.",
        "Once per game may shut down a zone. TODO: shutdown duration and target restrictions are unspecified.",
    ),
    Department(
        "extraction",
        "Division of Extraction & Asset Recovery",
        "Gain +1 VP when discharging a die showing 8.",
        "Once per game may discharge all volatile dice controlled by this player.",
    ),
    Department(
        "oversight",
        "Hazard & Oversight Liaison Office",
        "Gain +1 Influence when creating a Spillover.",
        "Once per game may move one Spillover token.",
    ),
    Department(
        "anomalous",
        "Department of Anomalous Resource Studies",
        "May store extra Anomaly Tokens. TODO: storage limits are unspecified, so no cap is enforced.",
        "Once per game may convert Anomaly Tokens into VP. TODO: conversion rate is unspecified.",
    ),
    Department(
        "influence",
        "Office of Influence & Expedience",
        "The first minor action each game costs 1 less Influence.",
        "Once per game may take an extra turn. TODO: turn timing is unspecified.",
    ),
)


def department_by_id(department_id: str) -> Department:
    for department in DEPARTMENTS:
        if department.id == department_id:
            return department
    raise ValueError(f"unknown Undersight department: {department_id}")


def base_camp() -> UndersightCard:
    return UndersightCard(
        "base-camp",
        "Base Camp",
        CardKind.BASE,
        depth=0,
        discharge_reward=RewardKind.INFLUENCE,
        reward_amount=1,
        creates_spillover=False,
        binding_slots_per_player=2,
    )


def starter_zones() -> list[UndersightCard]:
    return [
        UndersightCard("starter-vein", "Starter Vein", CardKind.ZONE, 1, RewardKind.GEMS, 1),
        UndersightCard("permit-kiosk", "Permit Kiosk", CardKind.ZONE, 1, RewardKind.INFLUENCE, 1),
        UndersightCard("unstable-rift", "Unstable Rift", CardKind.ZONE, 1, RewardKind.ANOMALY, 1, escalation_bonus=1),
        UndersightCard("survey-office", "Survey Office", CardKind.ZONE, 1, RewardKind.WAIVER, 1),
        UndersightCard("deep-pump", "Deep Pump", CardKind.ZONE, 2, RewardKind.GEMS, 2, escalation_bonus=1),
    ]


def build_player_deck(player_id: int) -> list[UndersightCard]:
    prefix = f"p{player_id}"
    return [
        UndersightCard(
            f"{prefix}-sifter",
            "Gem Sifter",
            CardKind.INSTALLATION,
            discharge_reward=RewardKind.GEMS,
            reward_amount=1,
            owner_bonus=RewardKind.INFLUENCE,
            owner_bonus_amount=1,
        ),
        UndersightCard(
            f"{prefix}-refinery",
            "Refinery",
            CardKind.INSTALLATION,
            discharge_reward=RewardKind.VP,
            reward_amount=2,
            owner_bonus=RewardKind.GEMS,
            owner_bonus_amount=1,
            escalation_bonus=1,
        ),
        UndersightCard(
            f"{prefix}-waiver-desk",
            "Waiver Desk",
            CardKind.INSTALLATION,
            discharge_reward=RewardKind.WAIVER,
            reward_amount=1,
            owner_bonus=RewardKind.INFLUENCE,
            owner_bonus_amount=1,
        ),
        UndersightCard(
            f"{prefix}-anomaly-cage",
            "Anomaly Cage",
            CardKind.INSTALLATION,
            discharge_reward=RewardKind.ANOMALY,
            reward_amount=1,
            owner_bonus=RewardKind.VP,
            owner_bonus_amount=1,
            escalation_bonus=1,
        ),
        UndersightCard(
            f"{prefix}-stabilize-order",
            "Stabilize Order",
            CardKind.DIRECTIVE,
            discharge_reward=RewardKind.INFLUENCE,
            reward_amount=1,
            creates_spillover=False,
        ),
        UndersightCard(
            f"{prefix}-expedite",
            "Expedite",
            CardKind.DIRECTIVE,
            discharge_reward=RewardKind.VP,
            reward_amount=1,
            creates_spillover=False,
        ),
    ]
