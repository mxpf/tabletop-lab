from tabletop_lab.games.black_ledger.actions import ClaimAction, CoverAction

from .conftest import stake_ids


def test_claim_highest_total_awards_card(rules, state):
    rules.begin_turn(state)
    p0 = state.current_player
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(0, 0, stake_ids(state.players[0], [5])), None)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [3])), None)
    state.current_player = 2
    state.metrics_data["turn_started"] = 1
    card = state.line[0].card
    rules.apply_action(state, ClaimAction(2, 0), None)
    assert card in state.players[0].tableau
    assert p0 in range(3)


def test_claim_tie_discards_card(rules, state):
    rules.begin_turn(state)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(0, 0, stake_ids(state.players[0], [3])), None)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [3])), None)
    state.current_player = 2
    state.metrics_data["turn_started"] = 1
    card = state.line[0].card
    rules.apply_action(state, ClaimAction(2, 0), None)
    assert card in state.discard
    assert all(card not in player.tableau for player in state.players)


def test_claim_cannot_take_unstaked_card_for_free(rules, state):
    rules.begin_turn(state)
    newest_index = len(state.line) - 1
    action = ClaimAction(state.current_player, newest_index)
    assert action not in rules.legal_actions(state, state.current_player)
