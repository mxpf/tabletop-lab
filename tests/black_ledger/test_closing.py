from tabletop_lab.games.black_ledger.cards import LedgerCard
from tabletop_lab.games.black_ledger.actions import CountAction


def test_closing_requires_three_different_numerals(rules, state):
    player = state.players[0]
    player.tableau = [LedgerCard("Crow", "I"), LedgerCard("Crow", "I"), LedgerCard("Crow", "II")]
    rules._auto_close_all(state)
    assert player.closed_accounts == {}
    player.tableau.append(LedgerCard("Crow", "III"))
    rules._auto_close_all(state)
    assert "Crow" in player.closed_accounts
    assert len(player.closed_accounts["Crow"]) == 3


def test_endgame_triggers_at_two_closed_accounts(rules, state):
    state.players[0].closed_accounts = {
        "Crow": [LedgerCard("Crow", "I"), LedgerCard("Crow", "II"), LedgerCard("Crow", "III")],
        "Knife": [LedgerCard("Knife", "I"), LedgerCard("Knife", "II"), LedgerCard("Knife", "III")],
    }
    rules._trigger_end_if_needed(state)
    assert state.end_triggered
    assert state.end_condition == "closed_accounts"


def test_endgame_triggers_when_deck_runs_out(rules, state):
    state.deck.clear()
    rules._trigger_end_if_needed(state)
    assert state.end_triggered
    assert state.end_condition == "deck_empty"


def test_endgame_finishes_current_round_before_game_over(rules, state):
    state.first_player = 0
    state.current_player = 1
    state.players[0].closed_accounts = {
        "Crow": [LedgerCard("Crow", "I"), LedgerCard("Crow", "II"), LedgerCard("Crow", "III")],
        "Knife": [LedgerCard("Knife", "I"), LedgerCard("Knife", "II"), LedgerCard("Knife", "III")],
    }
    rules.begin_turn(state)
    rules.apply_action(state, CountAction(1), None)
    assert state.current_player == 2
    assert not rules.is_game_over(state)
    rules.apply_action(state, CountAction(2), None)
    assert rules.is_game_over(state)
