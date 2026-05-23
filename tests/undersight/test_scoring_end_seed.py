from tabletop_lab.engine import Simulator
from tabletop_lab.games.undersight.actions import UndersightAction
from tabletop_lab.games.undersight.bots import RandomBot
from tabletop_lab.games.undersight.rules import UndersightRules
from tabletop_lab.games.undersight.variants import get_variant


def test_score_includes_final_resource_conversion(rules, state):
    player = state.players[0]
    player.vp = 3
    player.gems = 3
    player.anomalies = 2
    player.influence = 7
    scored = rules.score(state)
    assert scored["scores"][0] == 6


def test_vp_target_triggers_end_after_round_finish(rules, state):
    player_id = state.current_player
    state.players[player_id].vp = state.variant.vp_target
    rules.apply_action(state, next(a for a in rules.legal_actions(state, player_id) if a.allocate_card_id is None), None)
    assert state.end_triggered
    assert state.end_condition == "vp_target"
    assert not rules.is_game_over(state)
    while not rules.is_game_over(state):
        rules.apply_action(state, UndersightAction(state.current_player), None)


def test_idle_dice_low_triggers_end(rules, state):
    state.idle_dice = [1, 2, 3]
    rules.apply_action(state, UndersightAction(state.current_player), None)
    assert state.end_condition == "idle_dice_low"


def test_seed_replay_produces_identical_undersight_results():
    variant = get_variant("quick_2p")
    one = Simulator().run_game(UndersightRules(), [RandomBot(), RandomBot()], variant, seed=123, max_turns=100)
    two = Simulator().run_game(UndersightRules(), [RandomBot(), RandomBot()], variant, seed=123, max_turns=100)
    assert one.scores == two.scores
    assert one.winners == two.winners
    assert one.metrics["action_counts"] == two.metrics["action_counts"]
    assert one.metrics["end_condition"] == two.metrics["end_condition"]
