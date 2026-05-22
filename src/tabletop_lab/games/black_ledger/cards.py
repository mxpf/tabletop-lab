from __future__ import annotations

from dataclasses import dataclass

ACCOUNTS: dict[str, int] = {
    "Crow": 12,
    "Knife": 11,
    "Mask": 10,
    "Key": 9,
    "Lantern": 8,
    "Coin": 7,
    "Chain": 6,
    "Bell": 5,
}
NUMERALS = ("I", "II", "III", "IV")
STAKE_VALUES = (0, 0, 1, 1, 2, 3, 5, 8)


@dataclass(frozen=True)
class LedgerCard:
    account: str
    numeral: str

    @property
    def id(self) -> str:
        return f"{self.account}-{self.numeral}"

    @property
    def value(self) -> int:
        return ACCOUNTS[self.account]

    def __str__(self) -> str:
        return f"{self.account} {self.numeral}"


@dataclass(frozen=True)
class StakeCard:
    owner: int
    value: int
    instance: int

    @property
    def id(self) -> str:
        return f"P{self.owner}-{self.value}-{self.instance}"


def build_ledger_deck(numerals: tuple[str, ...] = NUMERALS) -> list[LedgerCard]:
    return [LedgerCard(account, numeral) for account in ACCOUNTS for numeral in numerals]


def build_stake_hand(player_id: int) -> list[StakeCard]:
    return [StakeCard(player_id, value, i) for i, value in enumerate(STAKE_VALUES)]
