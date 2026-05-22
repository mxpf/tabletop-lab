from tabletop_lab.games.black_ledger.actions import ClaimAction, CoverAction, CountAction
from tabletop_lab.games.black_ledger.variants import get_variant

from .conftest import stake_ids


def test_furnace_triggers_at_six_cards(rules, state):
    rules.begin_turn(state)
    state.line.append(state.line[-1].__class__(state.deck.pop()))
    state.line.append(state.line[-1].__class__(state.deck.pop()))
    assert len(state.line) == 6
    old = state.line[0].card
    rules.apply_action(state, CountAction(state.current_player), None)
    assert len(state.line) == 5
    assert old in state.furnace


def test_furnace_resolves_like_forced_claim_without_bonus(rules, state):
    rules.begin_turn(state)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(0, 0, stake_ids(state.players[0], [8])), None)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    state.players[0].spent.append(state.players[0].hand.pop())
    hand_before = len(state.players[0].hand)
    state.line.append(state.line[-1].__class__(state.deck.pop()))
    state.line.append(state.line[-1].__class__(state.deck.pop()))
    old = state.line[0].card
    rules.apply_action(state, CountAction(1), None)
    assert old in state.players[0].tableau
    assert len(state.players[0].hand) == hand_before


def test_clean_claim_bonus_only_applies_to_manual_claim_wins(rules, state):
    rules.begin_turn(state)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(0, 0, stake_ids(state.players[0], [8])), None)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    state.players[0].spent.append(state.players[0].hand.pop())
    hand_before = len(state.players[0].hand)
    rules.apply_action(state, ClaimAction(0, 0), None)
    assert len(state.players[0].hand) > hand_before


def test_clean_claim_bonus_does_not_apply_when_active_player_loses_claim(rules, state):
    rules.begin_turn(state)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(0, 0, stake_ids(state.players[0], [3])), None)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [8])), None)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    state.players[1].spent.append(state.players[1].hand.pop())
    hand_before = len(state.players[1].hand)
    rules.apply_action(state, ClaimAction(0, 0), None)
    assert len(state.players[1].hand) == hand_before


def test_clean_claim_bonus_can_be_disabled(rules):
    import random

    state = rules.setup(random.Random(5), get_variant("clean_claim_bonus_off"))
    rules.begin_turn(state)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(0, 0, stake_ids(state.players[0], [8])), None)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    state.players[0].spent.append(state.players[0].hand.pop())
    hand_before = len(state.players[0].hand)
    rules.apply_action(state, ClaimAction(0, 0), None)
    assert len(state.players[0].hand) == hand_before
