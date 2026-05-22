from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlackLedgerVariant:
    name: str
    player_count: int = 3
    starting_ledger_cards: int = 2
    starting_line_cards: int = 3
    numerals: tuple[str, ...] = ("I", "II", "III", "IV")
    numerals_to_close: int = 3
    loose_card_points: int = 2
    call_success_max: int = 2
    clean_claim_bonus: bool = True
    furnace_limit: int = 6
    accounts_to_end: int | None = 2


VARIANTS: dict[str, BlackLedgerVariant] = {
    "base_3p": BlackLedgerVariant("base_3p"),
    "starting_ledger_3": BlackLedgerVariant("starting_ledger_3", starting_ledger_cards=3),
    "close_2_accounts_test": BlackLedgerVariant("close_2_accounts_test", numerals_to_close=2),
    "five_numerals": BlackLedgerVariant("five_numerals", numerals=("I", "II", "III", "IV", "V")),
    "five_numerals_loose_1": BlackLedgerVariant("five_numerals_loose_1", numerals=("I", "II", "III", "IV", "V"), loose_card_points=1),
    "five_numerals_loose_2": BlackLedgerVariant("five_numerals_loose_2", numerals=("I", "II", "III", "IV", "V"), loose_card_points=2),
    "five_numerals_loose_3": BlackLedgerVariant("five_numerals_loose_3", numerals=("I", "II", "III", "IV", "V"), loose_card_points=3),
    "five_numerals_furnace_6": BlackLedgerVariant("five_numerals_furnace_6", numerals=("I", "II", "III", "IV", "V"), furnace_limit=6),
    "five_numerals_furnace_7": BlackLedgerVariant("five_numerals_furnace_7", numerals=("I", "II", "III", "IV", "V"), furnace_limit=7),
    "five_numerals_starting_line_4": BlackLedgerVariant("five_numerals_starting_line_4", numerals=("I", "II", "III", "IV", "V"), starting_line_cards=4),
    "five_numerals_starting_ledger_3": BlackLedgerVariant("five_numerals_starting_ledger_3", numerals=("I", "II", "III", "IV", "V"), starting_ledger_cards=3),
    "five_num_start3_loose1": BlackLedgerVariant("five_num_start3_loose1", numerals=("I", "II", "III", "IV", "V"), starting_ledger_cards=3, loose_card_points=1),
    "five_num_start3_loose2": BlackLedgerVariant("five_num_start3_loose2", numerals=("I", "II", "III", "IV", "V"), starting_ledger_cards=3, loose_card_points=2),
    "five_num_start3_loose3": BlackLedgerVariant("five_num_start3_loose3", numerals=("I", "II", "III", "IV", "V"), starting_ledger_cards=3, loose_card_points=3),
    "five_numerals_deck_end_only": BlackLedgerVariant("five_numerals_deck_end_only", numerals=("I", "II", "III", "IV", "V"), accounts_to_end=None),
    "loose_cards_1_point": BlackLedgerVariant("loose_cards_1_point", loose_card_points=1),
    "loose_cards_2_points": BlackLedgerVariant("loose_cards_2_points", loose_card_points=2),
    "loose_cards_3_points": BlackLedgerVariant("loose_cards_3_points", loose_card_points=3),
    "call_success_0_to_1": BlackLedgerVariant("call_success_0_to_1", call_success_max=1),
    "call_success_0_to_2": BlackLedgerVariant("call_success_0_to_2", call_success_max=2),
    "clean_claim_bonus_on": BlackLedgerVariant("clean_claim_bonus_on", clean_claim_bonus=True),
    "clean_claim_bonus_off": BlackLedgerVariant("clean_claim_bonus_off", clean_claim_bonus=False),
    "furnace_5": BlackLedgerVariant("furnace_5", furnace_limit=5),
    "furnace_6": BlackLedgerVariant("furnace_6", furnace_limit=6),
    "furnace_7": BlackLedgerVariant("furnace_7", furnace_limit=7),
}


def get_variant(name: str) -> BlackLedgerVariant:
    try:
        return VARIANTS[name]
    except KeyError as exc:
        raise ValueError(f"unknown Black Ledger variant: {name}") from exc
