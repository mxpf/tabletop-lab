def test_setup_deals_two_cards_to_each_player_and_three_to_line(state):
    assert [len(player.tableau) for player in state.players] == [2, 2, 2]
    assert len(state.line) == 3
    assert len(state.deck) == 23
    assert state.first_player == state.current_player
