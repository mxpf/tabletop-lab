from tabletop_lab.engine.metrics import Metrics


def test_metrics_counts_actions_and_counters():
    metrics = Metrics()
    metrics.action("Cover")
    metrics.action("Cover")
    metrics.inc("claim_wins")
    assert metrics.as_dict()["action_counts"] == {"Cover": 2}
    assert metrics.as_dict()["claim_wins"] == 1
