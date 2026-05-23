from __future__ import annotations

from collections import Counter

from tabletop_lab.engine.rules import GameRules

from .actions import UndersightAction
from .cards import CardKind, RewardKind, base_camp, build_player_deck, department_by_id, starter_zones
from .state import (
    BoundDie,
    PlayerState,
    TableauCard,
    UndersightState,
    VisiblePlayer,
    VisibleState,
    VisibleTableauCard,
)
from .variants import UndersightVariant


# Rules audit / assumptions:
# TODO: The stored rules do not include actual Installation, Directive, Starter Zone,
# Department, minor action, or Spillover card text. This module provides a small
# deterministic starter card set in cards.py so the simulator can exercise the
# core loop without pretending those missing card rules are canonical.
# TODO: "Discharge any number" is supported by action payloads, but generated
# legal actions expose zero or one die discharge to keep bot action spaces small.
# TODO: Spillovers are modeled as orthogonal tokens that add +1 escalation to
# dice on affected cards. "Next time" tilt effects are represented in state but
# no starter card currently emits them.
# TODO: Forbidden Depths access is enforced for depth >= 4, but starter placement
# avoids Forbidden Depths because no complete excavation/zone deck is specified.


class UndersightRules(GameRules):
    def setup(self, rng, variant: UndersightVariant) -> UndersightState:
        department_ids = ["permits", "extraction", "oversight", "anomalous", "influence"]
        players = []
        for player_id in range(variant.player_count):
            deck = build_player_deck(player_id)
            rng.shuffle(deck)
            hand = [deck.pop() for _ in range(min(variant.starting_hand_size, len(deck)))]
            players.append(
                PlayerState(
                    player_id=player_id,
                    department=department_by_id(department_ids[player_id % len(department_ids)]),
                    hand=hand,
                    deck=deck,
                )
            )

        zones = starter_zones()
        rng.shuffle(zones)
        starter_count = 3 if variant.player_count <= 2 else 4 if variant.player_count == 3 else 5
        positions = [(1, 0), (1, -1), (1, 1), (2, 0), (2, -1)]
        tableau = {"base-camp": TableauCard(base_camp(), (0, 0))}
        for zone, position in zip(zones[:starter_count], positions):
            tableau[zone.id] = TableauCard(zone, position)

        first = variant.first_player if variant.first_player is not None else rng.randrange(variant.player_count)
        return UndersightState(
            variant=variant,
            players=players,
            tableau=tableau,
            idle_dice=list(range(variant.dice_count)),
            current_player=first,
            first_player=first,
            action_counts_by_player={i: Counter() for i in range(variant.player_count)},
        )

    def legal_actions(self, state: UndersightState, player_id: int) -> list[UndersightAction]:
        if player_id != state.current_player:
            return []
        play_options = self._play_options(state, player_id)
        allocate_options = self._allocation_options(state, player_id)
        discharge_options = [()] + [(die.die_id,) for die in self._controlled_dice(state, player_id)]
        minor_options = [(None, None, None)] + self._minor_options(state, player_id)
        actions = []
        for play_card_id, play_position in play_options:
            for allocate_card_id in allocate_options:
                for discharge_die_ids in discharge_options:
                    for minor_action, minor_die_id, minor_target in minor_options:
                        action = UndersightAction(
                            player_id,
                            play_card_id=play_card_id,
                            play_position=play_position,
                            allocate_card_id=allocate_card_id,
                            discharge_die_ids=discharge_die_ids,
                            minor_action=minor_action,
                            minor_die_id=minor_die_id,
                            minor_target_card_id=minor_target,
                        )
                        if self._is_legal_action(state, action):
                            actions.append(action)
        return actions or [UndersightAction(player_id)]

    def apply_action(self, state: UndersightState, action: UndersightAction, rng) -> None:
        if not self._is_legal_action(state, action):
            raise ValueError(f"illegal action: {action}")
        state.action_counts[action.action_type] += 1
        state.action_counts_by_player[action.player_id][action.action_type] += 1
        state.metrics_data["turn_actions"] += 1

        if action.play_card_id:
            self._play_card(state, action)
        if action.allocate_card_id:
            self._allocate_die(state, action.player_id, action.allocate_card_id)
        for die_id in action.discharge_die_ids:
            self._discharge_die(state, action.player_id, die_id)
        if action.minor_action:
            self._minor_action(state, action)

        self._trigger_end_if_needed(state)
        self._advance_turn(state)

    def is_game_over(self, state: UndersightState) -> bool:
        return bool(state.end_triggered and state.round_turns_remaining == 0)

    def should_finish_round(self, state: UndersightState) -> bool:
        return state.end_triggered and state.round_turns_remaining != 0

    def score(self, state: UndersightState) -> dict:
        scores = {}
        for player in state.players:
            scores[player.player_id] = (
                player.vp
                + player.gems // 2
                + player.anomalies // 2
                + player.influence // 4
            )

        def tiebreak(player_id: int) -> tuple[int, int, int, int]:
            player = state.players[player_id]
            return (
                scores[player_id],
                player.influence,
                len(self._controlled_dice(state, player_id)),
                sum(1 for slot in state.tableau.values() if slot.owner == player_id),
            )

        best = max(tiebreak(player.player_id) for player in state.players)
        winners = [player.player_id for player in state.players if tiebreak(player.player_id) == best]
        return {"scores": scores, "winners": winners}

    def visible_state_for(self, state: UndersightState, player_id: int) -> VisibleState:
        visible_players = tuple(
            VisiblePlayer(
                player.player_id,
                player.department.id,
                len(player.hand),
                len(player.deck),
                len(player.discard),
                player.gems,
                player.influence,
                player.anomalies,
                player.waivers,
                player.vp,
            )
            for player in state.players
        )
        visible_tableau = tuple(
            VisibleTableauCard(
                slot.card,
                slot.position,
                slot.owner,
                slot.spillover_tokens,
                slot.tilted_next_time,
                tuple(sorted((die for die in state.dice.values() if die.card_id == card_id), key=lambda d: d.die_id)),
            )
            for card_id, slot in sorted(state.tableau.items(), key=lambda item: item[1].position)
        )
        return VisibleState(
            viewer_id=player_id,
            current_player=state.current_player,
            round_count=state.round_count,
            severance_count=state.severance_count,
            idle_dice_count=len(state.idle_dice),
            players=visible_players,
            tableau=visible_tableau,
            own_hand=tuple(state.players[player_id].hand),
            metrics_hint={"end_condition": state.end_condition},
        )

    def metrics(self, state: UndersightState) -> dict:
        scored = self.score(state)
        return {
            "seed": state.seed,
            "variant": state.variant.name,
            "winner": scored["winners"],
            "final_scores": scored["scores"],
            "vp": {p.player_id: p.vp for p in state.players},
            "gems": {p.player_id: p.gems for p in state.players},
            "influence": {p.player_id: p.influence for p in state.players},
            "anomalies": {p.player_id: p.anomalies for p in state.players},
            "waivers": {p.player_id: p.waivers for p in state.players},
            "active_dice": {p.player_id: len(self._controlled_dice(state, p.player_id)) for p in state.players},
            "installations": {
                p.player_id: sum(1 for slot in state.tableau.values() if slot.owner == p.player_id)
                for p in state.players
            },
            "idle_dice": len(state.idle_dice),
            "bound_dice": len(state.dice),
            "severance_count": state.severance_count,
            "spillover_tokens": sum(slot.spillover_tokens for slot in state.tableau.values()),
            "end_condition": state.end_condition,
            "first_player": state.first_player,
            "total_turns": state.turn_count,
            "round_count": state.round_count,
            "turns_by_player": {i: state.turn_counts[i] for i in range(len(state.players))},
            "action_counts": dict(state.action_counts),
            "action_counts_by_player": {
                player_id: dict(counts)
                for player_id, counts in sorted(state.action_counts_by_player.items())
            },
            **dict(state.metrics_data),
        }

    def _play_options(self, state: UndersightState, player_id: int) -> list[tuple[str | None, tuple[int, int] | None]]:
        options: list[tuple[str | None, tuple[int, int] | None]] = [(None, None)]
        player = state.players[player_id]
        for card in player.hand:
            if card.kind == CardKind.DIRECTIVE:
                options.append((card.id, None))
            elif card.kind == CardKind.INSTALLATION:
                for position in self._open_adjacent_positions(state):
                    if position[0] < 4 or player.waivers > 0:
                        options.append((card.id, position))
        return options

    def _allocation_options(self, state: UndersightState, player_id: int) -> list[str | None]:
        if not state.idle_dice:
            return [None]
        options = [None]
        for card_id in sorted(state.tableau):
            if self._can_allocate_to(state, player_id, card_id):
                options.append(card_id)
        return options

    def _minor_options(self, state: UndersightState, player_id: int) -> list[tuple[str, int, str | None]]:
        options = []
        player = state.players[player_id]
        cost = self._minor_cost(player)
        if player.influence >= cost:
            for die in self._controlled_dice(state, player_id):
                if die.value > 1:
                    options.append(("stabilize", die.die_id, None))
                for target_id in self._adjacent_card_ids(state, die.card_id):
                    if self._can_allocate_to(state, player_id, target_id, ignore_die_id=die.die_id):
                        options.append(("divert", die.die_id, target_id))
        return options

    def _is_legal_action(self, state: UndersightState, action: UndersightAction) -> bool:
        if action.player_id != state.current_player:
            return False
        if action.play_card_id is not None:
            if (action.play_card_id, action.play_position) not in self._play_options(state, action.player_id):
                return False
        if action.allocate_card_id is not None and not self._can_allocate_to(state, action.player_id, action.allocate_card_id):
            return False
        if len(set(action.discharge_die_ids)) != len(action.discharge_die_ids):
            return False
        if any(state.dice.get(die_id, None) is None or state.dice[die_id].owner != action.player_id for die_id in action.discharge_die_ids):
            return False
        if action.minor_action is None:
            return action.minor_die_id is None and action.minor_target_card_id is None
        if action.minor_die_id in action.discharge_die_ids:
            return False
        return (action.minor_action, action.minor_die_id, action.minor_target_card_id) in self._minor_options(state, action.player_id)

    def _play_card(self, state: UndersightState, action: UndersightAction) -> None:
        player = state.players[action.player_id]
        card = self._take_from_hand(player, action.play_card_id)
        if card.kind == CardKind.DIRECTIVE:
            self._gain(player, card.discharge_reward, card.reward_amount)
            player.discard.append(card)
            state.metrics_data["directives_played"] += 1
            return
        if card.kind != CardKind.INSTALLATION or action.play_position is None:
            raise ValueError("only Installations may be played to the tableau")
        if action.play_position[0] >= 4:
            player.waivers -= 1
        state.tableau[card.id] = TableauCard(card, action.play_position, owner=action.player_id)
        state.metrics_data["installations_played"] += 1

    def _allocate_die(self, state: UndersightState, player_id: int, card_id: str) -> None:
        die_id = state.idle_dice.pop(0)
        state.dice[die_id] = BoundDie(die_id, player_id, card_id, value=1)
        state.metrics_data["allocations"] += 1

    def _discharge_die(self, state: UndersightState, player_id: int, die_id: int) -> None:
        die = state.dice.pop(die_id)
        state.idle_dice.append(die.die_id)
        slot = state.tableau[die.card_id]
        player = state.players[player_id]
        self._gain(player, slot.card.discharge_reward, slot.card.reward_amount)
        if player.department.id == "extraction" and die.value == 8:
            player.vp += 1
        if slot.owner is not None and slot.owner != player_id and slot.owner not in slot.owner_bonus_claimed_round:
            owner = state.players[slot.owner]
            self._gain(owner, slot.card.owner_bonus, slot.card.owner_bonus_amount)
            slot.owner_bonus_claimed_round.add(slot.owner)
        if slot.card.creates_spillover:
            slot.spillover_tokens += 1
            state.metrics_data["spillovers_created"] += 1
            if player.department.id == "oversight":
                player.influence += 1
        state.metrics_data["discharges"] += 1

    def _minor_action(self, state: UndersightState, action: UndersightAction) -> None:
        player = state.players[action.player_id]
        cost = self._minor_cost(player)
        player.influence -= cost
        if player.department.id == "influence" and not player.reduced_minor_used:
            player.reduced_minor_used = True
        die = state.dice[action.minor_die_id]
        if action.minor_action == "stabilize":
            die.value -= 1
            state.metrics_data["stabilizes"] += 1
        elif action.minor_action == "divert":
            die.card_id = action.minor_target_card_id
            state.metrics_data["diverts"] += 1

    def _advance_turn(self, state: UndersightState) -> None:
        state.turn_counts[state.current_player] += 1
        state.turn_count += 1
        next_player = (state.current_player + 1) % len(state.players)
        if next_player == state.first_player:
            self._escalate_round(state)
            state.round_count += 1
            for slot in state.tableau.values():
                slot.owner_bonus_claimed_round.clear()
        if state.end_triggered and state.round_turns_remaining and state.round_turns_remaining > 0:
            state.round_turns_remaining -= 1
        state.current_player = next_player

    def _escalate_round(self, state: UndersightState) -> None:
        for die in list(state.dice.values()):
            slot = state.tableau[die.card_id]
            die.value += 1 + slot.card.escalation_bonus + self._adjacent_spillover_count(state, die.card_id)
            if die.value > 8:
                self._sever(state, die, slot)
            elif die.value >= 7:
                state.metrics_data["volatile_dice_seen"] += 1

    def _sever(self, state: UndersightState, die: BoundDie, slot: TableauCard) -> None:
        del state.dice[die.die_id]
        state.idle_dice.append(die.die_id)
        state.players[die.owner].vp -= 1
        state.severance_count += 1
        state.metrics_data["severances"] += 1
        if slot.spillover_tokens:
            slot.spillover_tokens -= 1
            state.metrics_data["spillovers_cleared_by_severance"] += 1
        self._trigger_end_if_needed(state)

    def _trigger_end_if_needed(self, state: UndersightState) -> None:
        if state.end_triggered:
            return
        condition = None
        if any(player.vp >= state.variant.vp_target for player in state.players):
            condition = "vp_target"
        elif state.severance_count >= state.variant.severance_limit:
            condition = "severance_limit"
        elif len(state.idle_dice) < state.variant.idle_dice_end_threshold:
            condition = "idle_dice_low"
        if condition is None:
            return
        state.end_triggered = True
        state.end_condition = condition
        next_player = (state.current_player + 1) % len(state.players)
        state.round_turns_remaining = ((state.first_player - next_player) % len(state.players)) + 1

    def _gain(self, player: PlayerState, reward: RewardKind | None, amount: int) -> None:
        if reward is None or amount == 0:
            return
        if reward == RewardKind.GEMS:
            player.gems += amount
        elif reward == RewardKind.INFLUENCE:
            player.influence += amount
        elif reward == RewardKind.ANOMALY:
            player.anomalies += amount
        elif reward == RewardKind.VP:
            player.vp += amount
        elif reward == RewardKind.WAIVER:
            player.waivers += amount

    def _take_from_hand(self, player: PlayerState, card_id: str | None):
        for card in player.hand:
            if card.id == card_id:
                player.hand.remove(card)
                return card
        raise ValueError(f"card {card_id} is not in player {player.player_id}'s hand")

    def _controlled_dice(self, state: UndersightState, player_id: int) -> list[BoundDie]:
        return sorted((die for die in state.dice.values() if die.owner == player_id), key=lambda die: die.die_id)

    def _can_allocate_to(
        self,
        state: UndersightState,
        player_id: int,
        card_id: str,
        ignore_die_id: int | None = None,
    ) -> bool:
        if card_id not in state.tableau:
            return False
        player = state.players[player_id]
        slot = state.tableau[card_id]
        if slot.position[0] >= 4 and player.waivers <= 0:
            return False
        controlled_here = sum(
            1
            for die in state.dice.values()
            if die.card_id == card_id and die.owner == player_id and die.die_id != ignore_die_id
        )
        return controlled_here < slot.card.binding_slots_per_player

    def _open_adjacent_positions(self, state: UndersightState) -> list[tuple[int, int]]:
        occupied = {slot.position for slot in state.tableau.values()}
        candidates = set()
        for depth, col in occupied:
            for candidate in ((depth + 1, col), (depth, col - 1), (depth, col + 1)):
                if candidate[0] >= 0 and candidate not in occupied:
                    candidates.add(candidate)
        return sorted(candidates)

    def _adjacent_card_ids(self, state: UndersightState, card_id: str) -> list[str]:
        position = state.tableau[card_id].position
        adjacent = []
        for other_id, slot in state.tableau.items():
            if other_id == card_id:
                continue
            if abs(slot.position[0] - position[0]) + abs(slot.position[1] - position[1]) == 1:
                adjacent.append(other_id)
        return sorted(adjacent)

    def _adjacent_spillover_count(self, state: UndersightState, card_id: str) -> int:
        return sum(state.tableau[other_id].spillover_tokens for other_id in self._adjacent_card_ids(state, card_id))

    def _minor_cost(self, player: PlayerState) -> int:
        if player.department.id == "influence" and not player.reduced_minor_used:
            return 0
        return 1
