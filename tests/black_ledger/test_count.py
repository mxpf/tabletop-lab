from tabletop_lab.games.black_ledger.actions import CountAction, CoverAction

from .conftest import stake_ids


def test_count_recovers_spent_stake_only(rules, state):
    player_id = state.current_player
    player = state.players[player_id]
    spent = player.hand.pop()
    committed_id = stake_ids(player, [5])
    player.spent.append(spent)
    rules.begin_turn(state)
    rules.apply_action(state, CoverAction(player_id, 0, committed_id), None)
    state.current_player = player_id
    state.metrics_data["turn_started"] = 1
    committed_count = len([c for slot in state.line for c in slot.commitments if c.owner == player_id])
    rules.apply_action(state, CountAction(player_id), None)
    assert spent in player.hand
    assert committed_count == 1
    assert all(c.stake not in player.hand for slot in state.line for c in slot.commitments if c.owner == player_id)
