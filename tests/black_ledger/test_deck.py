from collections import Counter

from tabletop_lab.games.black_ledger.cards import ACCOUNTS, NUMERALS, build_ledger_deck


def test_deck_construction_has_32_cards():
    assert len(build_ledger_deck()) == 32


def test_each_account_has_four_numerals():
    by_account = {}
    for card in build_ledger_deck():
        by_account.setdefault(card.account, set()).add(card.numeral)
    assert set(by_account) == set(ACCOUNTS)
    assert all(numerals == set(NUMERALS) for numerals in by_account.values())


def test_account_values_are_correct():
    assert ACCOUNTS == {
        "Crow": 12,
        "Knife": 11,
        "Mask": 10,
        "Key": 9,
        "Lantern": 8,
        "Coin": 7,
        "Chain": 6,
        "Bell": 5,
    }
    assert Counter(card.value for card in build_ledger_deck())[12] == 4
