from tabletop_lab.games.black_ledger.actions import CoverAction

from .conftest import stake_ids


def test_visible_state_hides_opponent_hand_spent_and_face_down_stake_values(rules, state):
    rules.begin_turn(state)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    hidden_ids = stake_ids(state.players[1], [8])
    rules.apply_action(state, CoverAction(1, 0, hidden_ids), None)
    state.players[1].spent.append(state.players[1].hand.pop())

    visible = rules.visible_state_for(state, 0)
    opponent = visible.players[1]
    commitment = next(c for c in visible.line[0].commitments if c.owner == 1)

    assert opponent.hand_count == len(state.players[1].hand)
    assert opponent.spent_count == len(state.players[1].spent)
    assert commitment.hidden_count == 1
    assert commitment.face_up_values == ()
    assert visible.own_hand_values == tuple(card.value for card in state.players[0].hand)
    assert visible.own_spent_values == tuple(card.value for card in state.players[0].spent)


def test_visible_state_reveals_face_up_called_stake_values(rules, state):
    from tabletop_lab.games.black_ledger.actions import CallAction

    rules.begin_turn(state)
    state.current_player = 1
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CoverAction(1, 0, stake_ids(state.players[1], [3])), None)
    state.current_player = 0
    state.metrics_data["turn_started"] = 1
    rules.apply_action(state, CallAction(0, 0, 1), None)

    visible = rules.visible_state_for(state, 2)
    commitment = next(c for c in visible.line[0].commitments if c.owner == 1)
    assert commitment.hidden_count == 0
    assert commitment.face_up_values == (3,)
