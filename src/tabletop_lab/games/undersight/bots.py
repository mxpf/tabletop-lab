from __future__ import annotations

from typing import Sequence

from tabletop_lab.engine.bots import Bot

from .actions import UndersightAction
from .cards import RewardKind
from .state import VisibleState


class RandomBot(Bot):
    name = "RandomBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[UndersightAction], rng):
        return rng.choice(list(legal_actions))


class GreedyBot(Bot):
    name = "GreedyBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[UndersightAction], rng):
        return max(
            legal_actions,
            key=lambda action: (
                self._score_play(visible_state, action),
                bool(action.discharge_die_ids),
                bool(action.allocate_card_id),
            ),
        )

    def _score_play(self, visible_state: VisibleState, action: UndersightAction) -> int:
        score = 0
        if action.play_card_id:
            own = {card.id: card for card in visible_state.own_hand}
            card = own.get(action.play_card_id)
            if card and card.discharge_reward == RewardKind.VP:
                score += 3
            elif card:
                score += 1
        if action.discharge_die_ids:
            score += 2
        return score


class SafetyBot(Bot):
    name = "SafetyBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[UndersightAction], rng):
        own = visible_state.viewer_id
        volatile = {
            die.die_id
            for slot in visible_state.tableau
            for die in slot.dice
            if die.owner == own and die.value >= 7
        }
        discharging = [action for action in legal_actions if any(die_id in volatile for die_id in action.discharge_die_ids)]
        if discharging:
            return rng.choice(discharging)
        stabilizing = [action for action in legal_actions if action.minor_action == "stabilize"]
        if stabilizing:
            return rng.choice(stabilizing)
        return rng.choice(list(legal_actions))


BOT_REGISTRY = {
    "random": RandomBot,
    "greedy": GreedyBot,
    "safety": SafetyBot,
}
