import random

from tabletop_lab.games.black_ledger.actions import ClaimAction, CoverIntent
from tabletop_lab.games.black_ledger.bots import BuilderBot, GreedyBot


def test_builder_prefers_cover_over_unstaked_burn(rules, state):
    rules.begin_turn(state)
    player_id = state.current_player
    visible = rules.visible_state_for(state, player_id)
    action = BuilderBot().choose_action(visible, rules.legal_actions(state, player_id), random.Random(1))
    assert isinstance(action, CoverIntent)


def test_greedy_prefers_cover_over_unstaked_burn(rules, state):
    rules.begin_turn(state)
    player_id = state.current_player
    visible = rules.visible_state_for(state, player_id)
    action = GreedyBot().choose_action(visible, rules.legal_actions(state, player_id), random.Random(1))
    assert isinstance(action, CoverIntent)


def test_builder_still_claims_staked_cards(rules, state):
    rules.begin_turn(state)
    player_id = state.current_player
    rules.apply_action(state, CoverIntent(player_id, 0), random.Random(1))
    player_id = state.current_player
    legal = rules.legal_actions(state, player_id)
    visible = rules.visible_state_for(state, player_id)
    action = BuilderBot().choose_action(visible, legal, random.Random(1))
    assert isinstance(action, ClaimAction)
