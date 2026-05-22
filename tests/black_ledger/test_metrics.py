def test_metrics_include_zero_count_rule_outcomes(rules, state):
    metrics = rules.metrics(state)
    assert metrics["call_attempts"] == 0
    assert metrics["call_successes"] == 0
    assert metrics["call_failures"] == 0
    assert metrics["furnace_resolutions"] == 0
    assert metrics["furnace_wins"] == 0
    assert metrics["furnace_empty_discards"] == 0
    assert metrics["furnace_tie_discards"] == 0
    assert metrics["manual_claim_tie_discards"] == 0
