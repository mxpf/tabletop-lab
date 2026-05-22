from tabletop_lab.engine import Simulator
from tabletop_lab.games.black_ledger.bots import RandomBot
from tabletop_lab.games.black_ledger.rules import BlackLedgerRules
from tabletop_lab.games.black_ledger.variants import get_variant
import pytest


def test_seed_replay_produces_identical_results():
    rules = BlackLedgerRules()
    variant = get_variant("base_3p")
    bots = [RandomBot(), RandomBot(), RandomBot()]
    one = Simulator().run_game(rules, bots, variant, seed=123)
    two = Simulator().run_game(BlackLedgerRules(), [RandomBot(), RandomBot(), RandomBot()], variant, seed=123)
    assert one.scores == two.scores
    assert one.winners == two.winners
    assert one.metrics["action_counts"] == two.metrics["action_counts"]
    assert one.metrics["end_condition"] == two.metrics["end_condition"]


def test_max_turns_stops_runaway_games():
    with pytest.raises(RuntimeError, match="max_turns=1"):
        Simulator().run_game(
            BlackLedgerRules(),
            [RandomBot(), RandomBot(), RandomBot()],
            get_variant("base_3p"),
            seed=123,
            max_turns=1,
        )


def test_simulator_requires_one_bot_per_player():
    with pytest.raises(ValueError, match="expected 3 bots"):
        Simulator().run_game(
            BlackLedgerRules(),
            [RandomBot()],
            get_variant("base_3p"),
            seed=123,
        )
