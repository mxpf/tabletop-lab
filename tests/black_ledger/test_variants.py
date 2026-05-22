import random

from tabletop_lab.games.black_ledger.cards import ACCOUNTS, LedgerCard, build_ledger_deck
from tabletop_lab.games.black_ledger.variants import get_variant


def test_starting_ledger_3_deals_three_face_up_cards_per_player(rules):
    state = rules.setup(random.Random(1), get_variant("starting_ledger_3"))
    assert [len(player.tableau) for player in state.players] == [3, 3, 3]
    assert len(state.line) == 3
    assert len(state.deck) == 20


def test_close_2_accounts_test_closes_with_two_different_numerals(rules, state):
    state.variant = get_variant("close_2_accounts_test")
    player = state.players[0]
    player.tableau = [LedgerCard("Crow", "I"), LedgerCard("Crow", "II")]
    rules._auto_close_all(state)
    assert "Crow" in player.closed_accounts
    assert len(player.closed_accounts["Crow"]) == 2
    assert player.tableau == []


def test_five_numerals_deck_has_40_cards():
    deck = build_ledger_deck(get_variant("five_numerals").numerals)
    assert len(deck) == 40
    for account in ACCOUNTS:
        assert {card.numeral for card in deck if card.account == account} == {"I", "II", "III", "IV", "V"}


def test_five_numerals_setup_and_closing_still_requires_three(rules):
    state = rules.setup(random.Random(2), get_variant("five_numerals"))
    assert len(state.deck) == 31
    player = state.players[0]
    player.tableau = [LedgerCard("Crow", "I"), LedgerCard("Crow", "V")]
    rules._auto_close_all(state)
    assert player.closed_accounts == {}
    player.tableau.append(LedgerCard("Crow", "III"))
    rules._auto_close_all(state)
    assert "Crow" in player.closed_accounts
    assert len(player.closed_accounts["Crow"]) == 3


def test_five_numerals_starting_line_4_reveals_four_line_cards(rules):
    state = rules.setup(random.Random(4), get_variant("five_numerals_starting_line_4"))
    assert len(state.line) == 4
    assert len(state.deck) == 30


def test_five_num_start3_loose_variants_use_three_starting_cards_and_expected_loose_values(rules):
    for name, loose_points in [
        ("five_num_start3_loose1", 1),
        ("five_num_start3_loose2", 2),
        ("five_num_start3_loose3", 3),
    ]:
        variant = get_variant(name)
        state = rules.setup(random.Random(6), variant)
        assert [len(player.tableau) for player in state.players] == [3, 3, 3]
        assert len(state.deck) == 28
        assert variant.loose_card_points == loose_points


def test_five_numerals_deck_end_only_ignores_closed_account_trigger(rules):
    state = rules.setup(random.Random(5), get_variant("five_numerals_deck_end_only"))
    state.players[0].closed_accounts = {
        "Crow": [LedgerCard("Crow", "I"), LedgerCard("Crow", "II"), LedgerCard("Crow", "III")],
        "Knife": [LedgerCard("Knife", "I"), LedgerCard("Knife", "II"), LedgerCard("Knife", "III")],
    }
    rules._trigger_end_if_needed(state)
    assert not state.end_triggered
    state.deck.clear()
    rules._trigger_end_if_needed(state)
    assert state.end_triggered
    assert state.end_condition == "deck_empty"
