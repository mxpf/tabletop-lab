from tabletop_lab.games.black_ledger.actions import CallAction, CoverAction
from tabletop_lab.games.black_ledger.variants import get_variant

from .conftest import stake_ids


def test_successful_call_catches_total_0_1_or_2_and_moves_heat(rules, state):
    rules.begin_turn(state)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [2])), None)
    state.current_player = 0
    state.players[0].heat = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CallAction(0, 0, 1), None)
    assert state.players[0].heat == 0
    assert state.players[1].heat == 2
    assert not [c for c in state.line[0].commitments if c.owner == 1]


def test_failed_call_happens_on_total_3_or_more(rules, state):
    rules.begin_turn(state)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [3])), None)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CallAction(0, 0, 1), None)
    assert state.players[0].heat == 1
    called = [c for c in state.line[0].commitments if c.owner == 1]
    assert called and all(c.face_up for c in called)


def test_call_success_threshold_variant_can_be_zero_to_one(rules):
    import random

    state = rules.setup(random.Random(3), get_variant("call_success_0_to_1"))
    rules.begin_turn(state)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [2])), None)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CallAction(0, 0, 1), None)
    assert state.players[0].heat == 1
    assert state.players[1].heat == 0
    assert [c for c in state.line[0].commitments if c.owner == 1 and c.face_up]
