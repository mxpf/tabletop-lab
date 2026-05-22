from __future__ import annotations

from collections import Counter
from typing import Sequence

from tabletop_lab.engine.bots import Bot

from .actions import BlackLedgerAction, CallAction, ClaimAction, CountAction, CoverAction, CoverIntent
from .cards import ACCOUNTS
from .state import VisibleState


class RandomBot(Bot):
    name = "RandomBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[BlackLedgerAction], rng):
        return rng.choice(list(legal_actions))


class BuilderBot(Bot):
    name = "BuilderBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[BlackLedgerAction], rng):
        needed_accounts = self._needed_accounts(visible_state)
        claims = _staked_claims(visible_state, legal_actions)
        for action in claims:
            if visible_state.line[action.line_index].card.account in needed_accounts:
                return action
        covers = [a for a in legal_actions if isinstance(a, (CoverAction, CoverIntent))]
        for action in covers:
            if visible_state.line[action.line_index].card.account in needed_accounts:
                return self._smallest_cover([action] + [c for c in covers if c.line_index == action.line_index])
        return _prefer_staked_claim_cover_count_burn(visible_state, legal_actions, rng)

    def _needed_accounts(self, visible_state: VisibleState) -> set[str]:
        player = visible_state.players[visible_state.viewer_id]
        counts = Counter(card.account for card in player.tableau)
        return {account for account, count in counts.items() if count >= 2}

    def _smallest_cover(self, covers: list[CoverAction | CoverIntent]) -> CoverAction | CoverIntent:
        return min(covers, key=lambda a: len(getattr(a, "stake_ids", ())))


class DenialBot(Bot):
    name = "DenialBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[BlackLedgerAction], rng):
        opponent_needs = set()
        for player in visible_state.players:
            if player.player_id == visible_state.viewer_id:
                continue
            counts = Counter(card.account for card in player.tableau)
            opponent_needs.update(account for account, count in counts.items() if count >= 2)
        claims = _claim_actions(legal_actions)
        for action in claims:
            if visible_state.line[action.line_index].card.account in opponent_needs:
                return action
        calls = [a for a in legal_actions if isinstance(a, CallAction)]
        if calls and rng.random() < 0.35:
            return rng.choice(calls)
        return _prefer_staked_claim_cover_count_burn(visible_state, legal_actions, rng)


class BlufferBot(Bot):
    name = "BlufferBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[BlackLedgerAction], rng):
        if visible_state.players[visible_state.viewer_id].heat and _counts(legal_actions):
            return _counts(legal_actions)[0]
        calls = [a for a in legal_actions if isinstance(a, CallAction)]
        if calls and rng.random() < 0.45:
            return rng.choice(calls)
        covers = [a for a in legal_actions if isinstance(a, (CoverAction, CoverIntent))]
        if covers and rng.random() < 0.65:
            return min(covers, key=lambda a: len(getattr(a, "stake_ids", ())))
        return _prefer_staked_claim_cover_count_burn(visible_state, legal_actions, rng)


class ConservativeBot(Bot):
    name = "ConservativeBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[BlackLedgerAction], rng):
        claims = _staked_claims(visible_state, legal_actions)
        own = visible_state.viewer_id
        safe_claims = []
        for action in claims:
            slot = visible_state.line[action.line_index]
            own_face_up = sum(sum(c.face_up_values) for c in slot.commitments if c.owner == own)
            visible_opp = max((sum(c.face_up_values) for c in slot.commitments if c.owner != own), default=0)
            if own_face_up >= visible_opp:
                safe_claims.append(action)
        if safe_claims:
            return rng.choice(safe_claims)
        if _counts(legal_actions):
            return _counts(legal_actions)[0]
        return _prefer_staked_claim_cover_count_burn(visible_state, legal_actions, rng)


class GreedyBot(Bot):
    name = "GreedyBot"

    def choose_action(self, visible_state: VisibleState, legal_actions: Sequence[BlackLedgerAction], rng):
        claims = _staked_claims(visible_state, legal_actions)
        if claims:
            return max(claims, key=lambda a: ACCOUNTS[visible_state.line[a.line_index].card.account])
        covers = [a for a in legal_actions if isinstance(a, (CoverAction, CoverIntent))]
        if covers:
            return max(covers, key=lambda a: ACCOUNTS[visible_state.line[a.line_index].card.account])
        return rng.choice(list(legal_actions))


def _counts(actions: Sequence[BlackLedgerAction]) -> list[CountAction]:
    return [a for a in actions if isinstance(a, CountAction)]


def _claim_actions(actions: Sequence[BlackLedgerAction]) -> list[ClaimAction]:
    return [a for a in actions if isinstance(a, ClaimAction)]


def _staked_claims(visible_state: VisibleState, actions: Sequence[BlackLedgerAction]) -> list[ClaimAction]:
    return [
        action
        for action in _claim_actions(actions)
        if visible_state.line[action.line_index].commitments
    ]


def _burn_claims(visible_state: VisibleState, actions: Sequence[BlackLedgerAction]) -> list[ClaimAction]:
    return [
        action
        for action in _claim_actions(actions)
        if not visible_state.line[action.line_index].commitments
    ]


def _prefer_staked_claim_cover_count_burn(
    visible_state: VisibleState, actions: Sequence[BlackLedgerAction], rng
):
    claims = _staked_claims(visible_state, actions)
    if claims:
        return rng.choice(claims)
    covers = [a for a in actions if isinstance(a, (CoverAction, CoverIntent))]
    if covers:
        return rng.choice(covers)
    if _counts(actions):
        return _counts(actions)[0]
    burns = _burn_claims(visible_state, actions)
    if burns:
        return rng.choice(burns)
    return rng.choice(list(actions))


BOT_REGISTRY = {
    "random": RandomBot,
    "builder": BuilderBot,
    "denial": DenialBot,
    "bluffer": BlufferBot,
    "conservative": ConservativeBot,
    "greedy": GreedyBot,
}
