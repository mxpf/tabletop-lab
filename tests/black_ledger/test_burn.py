from tabletop_lab.games.black_ledger.actions import ClaimAction


def test_burn_is_illegal_for_three_newest_cards(rules, state):
    rules.begin_turn(state)
    legal = rules.legal_actions(state, state.current_player)
    newest = {len(state.line) - 1, len(state.line) - 2, len(state.line) - 3}
    for index in newest:
        assert ClaimAction(state.current_player, index) not in legal


def test_burn_is_legal_for_old_enough_unstaked_card(rules, state):
    rules.begin_turn(state)
    old_card = state.line[0].card
    action = ClaimAction(state.current_player, 0)
    assert action in rules.legal_actions(state, state.current_player)
    rules.apply_action(state, action, None)
    assert old_card in state.discard
