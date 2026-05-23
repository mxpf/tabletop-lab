from tabletop_lab.games.undersight.cards import CardKind


def test_setup_creates_base_starter_zones_players_and_idle_dice(state):
    assert len(state.players) == 3
    assert len(state.idle_dice) == 34
    assert state.tableau["base-camp"].card.kind == CardKind.BASE
    assert sum(1 for slot in state.tableau.values() if slot.card.kind == CardKind.ZONE) == 4
    assert [len(player.hand) for player in state.players] == [3, 3, 3]
    assert state.first_player == state.current_player


def test_setup_keeps_private_hands_out_of_visible_opponents(rules, state):
    viewer = rules.visible_state_for(state, 0)
    assert len(viewer.own_hand) == len(state.players[0].hand)
    assert viewer.players[1].hand_count == len(state.players[1].hand)
    assert all(card not in viewer.own_hand for card in state.players[1].hand)
