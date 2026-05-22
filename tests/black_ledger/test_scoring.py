from tabletop_lab.games.black_ledger.cards import LedgerCard


def test_closed_accounts_and_loose_cards_score_correctly(rules, state):
    player = state.players[0]
    player.closed_accounts = {
        "Crow": [LedgerCard("Crow", "I"), LedgerCard("Crow", "II"), LedgerCard("Crow", "III")]
    }
    player.tableau = [LedgerCard("Bell", "I"), LedgerCard("Key", "II")]
    scored = rules.score(state)
    assert scored["scores"][0] == 12 + 4


def test_heat_penalty_applies_correctly(rules, state):
    state.players[0].heat = 2
    state.players[1].heat = 3
    state.players[2].heat = 5
    scores = rules.score(state)["scores"]
    base0 = len(state.players[0].tableau) * state.variant.loose_card_points
    base1 = len(state.players[1].tableau) * state.variant.loose_card_points
    base2 = len(state.players[2].tableau) * state.variant.loose_card_points
    assert scores[0] == base0
    assert scores[1] == base1 - 5
    assert scores[2] == base2 - 12
