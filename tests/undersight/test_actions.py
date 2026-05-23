from tabletop_lab.games.undersight.actions import UndersightAction
from tabletop_lab.games.undersight.cards import CardKind, RewardKind, UndersightCard
from tabletop_lab.games.undersight.state import BoundDie, TableauCard


def test_legal_actions_include_allocation_to_open_tableau_slot(rules, state):
    player_id = state.current_player
    actions = rules.legal_actions(state, player_id)
    assert actions
    assert any(action.allocate_card_id == "base-camp" for action in actions)


def test_allocate_binds_value_one_die_to_player_slot(rules, state):
    player_id = state.current_player
    rules.apply_action(state, UndersightAction(player_id, allocate_card_id="base-camp"), None)
    die = state.dice[0]
    assert die.owner == player_id
    assert die.card_id == "base-camp"
    assert die.value == 1
    assert 0 not in state.idle_dice


def test_discharge_returns_die_and_grants_reward(rules, state):
    player_id = state.current_player
    rules.apply_action(state, UndersightAction(player_id, allocate_card_id="base-camp"), None)
    state.current_player = player_id
    rules.apply_action(state, UndersightAction(player_id, discharge_die_ids=(0,)), None)
    assert 0 in state.idle_dice
    assert 0 not in state.dice
    assert state.players[player_id].influence == 1


def test_play_installation_places_owned_card(rules, state):
    player_id = state.current_player
    card = UndersightCard(
        f"p{player_id}-test",
        "Test Rig",
        CardKind.INSTALLATION,
        discharge_reward=RewardKind.GEMS,
        reward_amount=1,
    )
    state.players[player_id].hand = [card]
    action = next(a for a in rules.legal_actions(state, player_id) if a.play_card_id == card.id)
    rules.apply_action(state, action, None)
    assert state.tableau[card.id].owner == player_id


def test_spillover_increases_adjacent_escalation(rules, state):
    player_id = state.current_player
    card = UndersightCard("test-card", "Test Card", CardKind.ZONE, 1, RewardKind.GEMS, 1)
    state.tableau[card.id] = TableauCard(card, (0, 1), spillover_tokens=1)
    rules.apply_action(state, UndersightAction(player_id, allocate_card_id="base-camp"), None)
    while state.current_player != state.first_player:
        rules.apply_action(state, UndersightAction(state.current_player), None)
    assert state.dice[0].value == 3


def test_owner_bonus_claims_once_per_round_per_installation(rules, state):
    owner_id = state.current_player
    user_id = (owner_id + 1) % len(state.players)
    card = UndersightCard(
        "owner-test",
        "Owner Test",
        CardKind.INSTALLATION,
        discharge_reward=RewardKind.GEMS,
        reward_amount=1,
        owner_bonus=RewardKind.INFLUENCE,
        owner_bonus_amount=1,
    )
    state.tableau[card.id] = TableauCard(card, (1, 2), owner=owner_id)
    state.dice[20] = BoundDie(20, user_id, card.id, value=3)
    state.dice[21] = BoundDie(21, user_id, card.id, value=3)
    state.idle_dice = [die_id for die_id in state.idle_dice if die_id not in {20, 21}]
    state.current_player = user_id

    rules.apply_action(state, UndersightAction(user_id, discharge_die_ids=(20, 21)), None)

    assert state.players[user_id].gems == 2
    assert state.players[owner_id].influence == 1


def test_severance_returns_die_penalizes_owner_and_counts_end(rules, state):
    player_id = state.current_player
    state.dice[12] = BoundDie(12, player_id, "base-camp", value=8)
    state.idle_dice.remove(12)
    state.players[player_id].vp = 1
    state.variant = type(state.variant)(
        **{
            **state.variant.__dict__,
            "severance_limit": 1,
        }
    )

    while state.current_player != state.first_player or state.turn_count == 0:
        rules.apply_action(state, UndersightAction(state.current_player), None)

    assert 12 in state.idle_dice
    assert 12 not in state.dice
    assert state.players[player_id].vp == 0
    assert state.severance_count == 1
    assert state.end_condition == "severance_limit"
