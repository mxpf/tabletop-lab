from tabletop_lab.games.black_ledger.actions import CoverAction, CoverIntent

from .conftest import stake_ids


def test_cover_commits_one_to_three_hidden_stake_cards(rules, state):
    rules.begin_turn(state)
    player = state.players[state.current_player]
    action = CoverAction(state.current_player, 0, stake_ids(player, [0, 1, 2]))
    rules.apply_action(state, action, None)
    slot = state.line[0]
    assert len(slot.commitments) == 3
    assert all(not commitment.face_up for commitment in slot.commitments)
    assert len(player.hand) == 5


def test_cover_legal_actions_use_one_intent_per_line_instead_of_stake_combinations(rules, state):
    rules.begin_turn(state)
    actions = [
        action
        for action in rules.legal_actions(state, state.current_player)
        if isinstance(action, CoverIntent)
    ]
    assert actions == [
        CoverIntent(state.current_player, line_index)
        for line_index in range(len(state.line))
    ]


def test_cover_with_duplicate_stake_id_is_illegal(rules, state):
    rules.begin_turn(state)
    player = state.players[state.current_player]
    stake_id = player.hand[0].id
    action = CoverAction(state.current_player, 0, (stake_id, stake_id))
    assert action not in rules.legal_actions(state, state.current_player)


def test_cover_intent_resolves_to_one_to_three_stake_cards_from_hand(rules, state):
    import random

    rules.begin_turn(state)
    player = state.players[state.current_player]
    hand_ids = {stake.id for stake in player.hand}
    rules.apply_action(state, CoverIntent(state.current_player, 0), random.Random(1))
    committed = state.line[0].commitments
    assert 1 <= len(committed) <= 3
    assert {commitment.stake.id for commitment in committed}.issubset(hand_ids)
    assert all(commitment.stake not in player.hand for commitment in committed)
