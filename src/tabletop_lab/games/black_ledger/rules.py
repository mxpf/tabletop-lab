from __future__ import annotations

from collections import Counter, defaultdict
from tabletop_lab.engine.rules import GameRules

from .actions import BlackLedgerAction, CallAction, ClaimAction, CountAction, CoverAction, CoverIntent
from .cards import ACCOUNTS, LedgerCard, StakeCard, build_ledger_deck, build_stake_hand
from .state import (
    BlackLedgerState,
    Commitment,
    LineSlot,
    PlayerState,
    VisibleCommitment,
    VisibleLineSlot,
    VisiblePlayer,
    VisibleState,
)
from .variants import BlackLedgerVariant


class BlackLedgerRules(GameRules):
    def setup(self, rng, variant: BlackLedgerVariant) -> BlackLedgerState:
        deck = build_ledger_deck(variant.numerals)
        rng.shuffle(deck)
        players = [PlayerState(i, build_stake_hand(i)) for i in range(variant.player_count)]
        for player in players:
            player.tableau.extend(deck.pop() for _ in range(variant.starting_ledger_cards))
        line = [LineSlot(deck.pop()) for _ in range(variant.starting_line_cards)]
        first = rng.randrange(variant.player_count)
        return BlackLedgerState(
            variant=variant,
            players=players,
            deck=deck,
            line=line,
            current_player=first,
            first_player=first,
            metrics_data=Counter(),
            action_counts_by_player={i: Counter() for i in range(variant.player_count)},
        )

    def begin_turn(self, state: BlackLedgerState) -> None:
        if state.metrics_data.get("turn_started"):
            return
        state.last_revealed = None
        if state.deck:
            state.last_revealed = state.deck.pop()
            state.line.append(LineSlot(state.last_revealed))
        self._trigger_end_if_needed(state)
        state.metrics_data["turn_started"] = 1

    def legal_actions(self, state: BlackLedgerState, player_id: int) -> list[BlackLedgerAction]:
        if player_id != state.current_player:
            return []
        self.begin_turn(state)
        player = state.players[player_id]
        actions: list[BlackLedgerAction] = [CountAction(player_id)]

        for slot_index, slot in enumerate(state.line):
            if player.hand:
                actions.append(CoverIntent(player_id, slot_index))

            if slot.commitments or self._is_burnable(state, slot_index):
                actions.append(ClaimAction(player_id, slot_index))

            owners_with_hidden = {
                commitment.owner
                for commitment in slot.commitments
                if commitment.owner != player_id and not commitment.face_up
            }
            for owner in sorted(owners_with_hidden):
                actions.append(CallAction(player_id, slot_index, owner))

        return actions

    def apply_action(self, state: BlackLedgerState, action: BlackLedgerAction, rng) -> None:
        self.begin_turn(state)
        if not self._is_legal_action(state, action):
            raise ValueError(f"illegal action: {action}")
        state.action_counts[action.action_type] += 1
        state.action_counts_by_player[action.player_id][action.action_type] += 1
        state.metrics_data[f"{action.action_type.lower()}_count"] += 1

        if isinstance(action, CoverIntent):
            self._cover_intent(state, action, rng)
        elif isinstance(action, CoverAction):
            self._cover(state, action)
        elif isinstance(action, ClaimAction):
            self._claim_or_burn(state, action)
        elif isinstance(action, CallAction):
            self._call(state, action)
        elif isinstance(action, CountAction):
            self._count(state, action)
        else:
            raise TypeError(f"unsupported action {action}")

        self._furnace_if_needed(state)
        self._auto_close_all(state)
        self._trigger_end_if_needed(state)
        self._advance_turn(state)

    def is_game_over(self, state: BlackLedgerState) -> bool:
        return bool(state.end_triggered and state.round_turns_remaining == 0)

    def should_finish_round(self, state: BlackLedgerState) -> bool:
        return state.end_triggered and state.round_turns_remaining != 0

    def score(self, state: BlackLedgerState) -> dict:
        scores = {}
        closed_counts = {}
        loose_counts = {}
        for player in state.players:
            closed_score = sum(ACCOUNTS[account] for account in player.closed_accounts)
            loose_score = len(player.tableau) * state.variant.loose_card_points
            scores[player.player_id] = closed_score + loose_score + self._heat_penalty(player.heat)
            closed_counts[player.player_id] = len(player.closed_accounts)
            loose_counts[player.player_id] = len(player.tableau)

        def tiebreak(player_id: int) -> tuple[int, int, int, int]:
            player = state.players[player_id]
            return (scores[player_id], -player.heat, len(player.closed_accounts), len(player.hand))

        best = max(tiebreak(player.player_id) for player in state.players)
        winners = [player.player_id for player in state.players if tiebreak(player.player_id) == best]
        return {
            "scores": scores,
            "winners": winners,
            "closed_accounts": closed_counts,
            "loose_cards": loose_counts,
        }

    def visible_state_for(self, state: BlackLedgerState, player_id: int) -> VisibleState:
        line = []
        for index, slot in enumerate(state.line):
            by_owner: dict[int, list[Commitment]] = defaultdict(list)
            for commitment in slot.commitments:
                by_owner[commitment.owner].append(commitment)
            visible_commitments = []
            for owner, commitments in sorted(by_owner.items()):
                face_up_values = tuple(c.stake.value for c in commitments if c.face_up or owner == player_id)
                hidden_count = sum(1 for c in commitments if not c.face_up and owner != player_id)
                visible_commitments.append(
                    VisibleCommitment(owner, len(commitments), face_up_values, hidden_count)
                )
            line.append(VisibleLineSlot(slot.card, index, tuple(visible_commitments)))

        players = tuple(
            VisiblePlayer(
                p.player_id,
                len(p.hand),
                len(p.spent),
                tuple(p.tableau),
                tuple(sorted(p.closed_accounts)),
                p.heat,
            )
            for p in state.players
        )
        viewer = state.players[player_id]
        return VisibleState(
            viewer_id=player_id,
            current_player=state.current_player,
            line=tuple(line),
            players=players,
            own_hand_values=tuple(card.value for card in viewer.hand),
            own_spent_values=tuple(card.value for card in viewer.spent),
            deck_count=len(state.deck),
            discard_count=len(state.discard),
            furnace_count=len(state.furnace),
        )

    def metrics(self, state: BlackLedgerState) -> dict:
        scored = self.score(state)
        first_won = state.first_player in scored["winners"]
        counters = Counter(
            {
                "claim_wins": 0,
                "burn_count": 0,
                "call_attempts": 0,
                "call_successes": 0,
                "call_failures": 0,
                "furnace_resolutions": 0,
                "furnace_wins": 0,
                "furnace_empty_discards": 0,
                "furnace_tie_discards": 0,
                "manual_claim_tie_discards": 0,
            }
        )
        counters.update(state.metrics_data)
        return {
            "seed": state.seed,
            "variant": state.variant.name,
            "winner": scored["winners"],
            "final_scores": scored["scores"],
            "closed_accounts": scored["closed_accounts"],
            "loose_cards": scored["loose_cards"],
            "heat": {p.player_id: p.heat for p in state.players},
            "action_counts": dict(state.action_counts),
            "action_counts_by_player": {
                player_id: dict(counts)
                for player_id, counts in sorted(state.action_counts_by_player.items())
            },
            "cover_count": state.action_counts["Cover"],
            "claim_count": state.action_counts["Claim"],
            "count_actions": state.action_counts["Count"],
            "total_turns": state.turn_count,
            "turns_by_player": {i: state.turn_counts[i] for i in range(len(state.players))},
            "ledger_cards_won": {i: state.ledger_won_counts[i] for i in range(len(state.players))},
            "claim_wins_by_player": {i: state.claim_win_counts[i] for i in range(len(state.players))},
            "furnace_wins_by_player": {i: state.furnace_win_counts[i] for i in range(len(state.players))},
            "ledger_cards_total": {
                p.player_id: len(p.tableau) + sum(len(cards) for cards in p.closed_accounts.values())
                for p in state.players
            },
            "end_condition": state.end_condition,
            "first_player": state.first_player,
            "first_player_win_or_tie": first_won,
            **dict(counters),
        }

    def _cover(self, state: BlackLedgerState, action: CoverAction) -> None:
        player = state.players[action.player_id]
        chosen = [self._take_stake_from_hand(player, stake_id) for stake_id in action.stake_ids]
        for stake in chosen:
            state.line[action.line_index].commitments.append(Commitment(action.player_id, stake))

    def _cover_intent(self, state: BlackLedgerState, action: CoverIntent, rng) -> None:
        player = state.players[action.player_id]
        count = rng.randint(1, min(3, len(player.hand)))
        chosen = rng.sample(player.hand, count)
        self._cover(state, CoverAction(action.player_id, action.line_index, tuple(stake.id for stake in chosen)))

    def _is_legal_action(self, state: BlackLedgerState, action: BlackLedgerAction) -> bool:
        if action.player_id != state.current_player:
            return False
        if isinstance(action, CountAction):
            return True
        if isinstance(action, CoverIntent):
            return self._is_legal_cover_intent(state, action)
        if isinstance(action, CoverAction):
            return self._is_legal_cover(state, action)
        if isinstance(action, ClaimAction):
            return self._is_legal_claim(state, action)
        if isinstance(action, CallAction):
            return self._is_legal_call(state, action)
        return False

    def _is_legal_cover_intent(self, state: BlackLedgerState, action: CoverIntent) -> bool:
        return (
            0 <= action.line_index < len(state.line)
            and bool(state.players[action.player_id].hand)
        )

    def _is_legal_cover(self, state: BlackLedgerState, action: CoverAction) -> bool:
        if not 0 <= action.line_index < len(state.line):
            return False
        if not 1 <= len(action.stake_ids) <= 3:
            return False
        if len(set(action.stake_ids)) != len(action.stake_ids):
            return False
        hand_ids = {stake.id for stake in state.players[action.player_id].hand}
        return all(stake_id in hand_ids for stake_id in action.stake_ids)

    def _is_legal_claim(self, state: BlackLedgerState, action: ClaimAction) -> bool:
        if not 0 <= action.line_index < len(state.line):
            return False
        slot = state.line[action.line_index]
        return bool(slot.commitments or self._is_burnable(state, action.line_index))

    def _is_legal_call(self, state: BlackLedgerState, action: CallAction) -> bool:
        if not 0 <= action.line_index < len(state.line):
            return False
        if action.target_player == action.player_id:
            return False
        if not 0 <= action.target_player < len(state.players):
            return False
        return any(
            commitment.owner == action.target_player and not commitment.face_up
            for commitment in state.line[action.line_index].commitments
        )

    def _claim_or_burn(self, state: BlackLedgerState, action: ClaimAction) -> None:
        slot = state.line[action.line_index]
        if not slot.commitments:
            if not self._is_burnable(state, action.line_index):
                raise ValueError("cannot burn one of the three newest unstaked cards")
            state.discard.append(slot.card)
            del state.line[action.line_index]
            state.metrics_data["burn_count"] += 1
            return

        winner, tied = self._resolve_staked_card(state, action.line_index)
        if winner is None:
            state.metrics_data["manual_claim_tie_discards"] += 1
            return
        state.metrics_data["claim_wins"] += 1
        state.claim_win_counts[winner] += 1
        if winner == action.player_id and state.variant.clean_claim_bonus:
            self._clean_claim_bonus(state.players[winner])

    def _call(self, state: BlackLedgerState, action: CallAction) -> None:
        slot = state.line[action.line_index]
        called = [c for c in slot.commitments if c.owner == action.target_player and not c.face_up]
        if not called:
            raise ValueError("Call target has no face-down Stake under that card")
        total = sum(c.stake.value for c in called)
        state.metrics_data["call_attempts"] += 1
        caller = state.players[action.player_id]
        target = state.players[action.target_player]
        if total <= state.variant.call_success_max:
            state.metrics_data["call_successes"] += 1
            target.heat += 1
            if caller.heat > 0:
                caller.heat -= 1
                target.heat += 1
            for commitment in list(called):
                target.spent.append(commitment.stake)
                slot.commitments.remove(commitment)
        else:
            state.metrics_data["call_failures"] += 1
            caller.heat += 1
            for commitment in called:
                commitment.face_up = True

    def _count(self, state: BlackLedgerState, action: CountAction) -> None:
        player = state.players[action.player_id]
        player.hand.extend(player.spent)
        player.spent.clear()

    def _furnace_if_needed(self, state: BlackLedgerState) -> None:
        while len(state.line) >= state.variant.furnace_limit:
            state.metrics_data["furnace_resolutions"] += 1
            slot = state.line[0]
            if not slot.commitments:
                state.discard.append(slot.card)
                state.furnace.append(slot.card)
                del state.line[0]
                state.metrics_data["furnace_empty_discards"] += 1
                continue
            winner, tied = self._resolve_staked_card(state, 0, furnace=True)
            if winner is None and tied:
                state.metrics_data["furnace_tie_discards"] += 1
            elif winner is not None:
                state.metrics_data["furnace_wins"] += 1
                state.furnace_win_counts[winner] += 1

    def _resolve_staked_card(
        self, state: BlackLedgerState, line_index: int, furnace: bool = False
    ) -> tuple[int | None, bool]:
        slot = state.line[line_index]
        totals: Counter[int] = Counter()
        for commitment in slot.commitments:
            totals[commitment.owner] += commitment.stake.value
            state.players[commitment.owner].spent.append(commitment.stake)
        high = max(totals.values())
        leaders = [owner for owner, total in totals.items() if total == high]
        card = slot.card
        del state.line[line_index]
        if len(leaders) != 1:
            state.discard.append(card)
            if furnace:
                state.furnace.append(card)
            return None, True
        state.players[leaders[0]].tableau.append(card)
        state.ledger_won_counts[leaders[0]] += 1
        if furnace:
            state.furnace.append(card)
        return leaders[0], False

    def _auto_close_all(self, state: BlackLedgerState) -> None:
        for player in state.players:
            changed = True
            while changed:
                changed = False
                by_account: dict[str, list[LedgerCard]] = defaultdict(list)
                for card in player.tableau:
                    if card.account not in player.closed_accounts:
                        by_account[card.account].append(card)
                for account, cards in by_account.items():
                    unique: dict[str, LedgerCard] = {}
                    for card in cards:
                        unique.setdefault(card.numeral, card)
                    if len(unique) >= state.variant.numerals_to_close:
                        closing = list(unique.values())[: state.variant.numerals_to_close]
                        for card in closing:
                            player.tableau.remove(card)
                        player.closed_accounts[account] = closing
                        changed = True
                        break

    def _trigger_end_if_needed(self, state: BlackLedgerState) -> None:
        if state.end_triggered:
            return
        account_end = (
            state.variant.accounts_to_end is not None
            and any(len(p.closed_accounts) >= state.variant.accounts_to_end for p in state.players)
        )
        deck_end = not state.deck
        if not account_end and not deck_end:
            return
        state.end_triggered = True
        state.end_condition = "closed_accounts" if account_end else "deck_empty"
        next_player = (state.current_player + 1) % len(state.players)
        # This is set before the triggering player's turn advances. Store one
        # extra count so the current completed turn is not mistaken for a
        # future equalizing turn.
        state.round_turns_remaining = ((state.first_player - next_player) % len(state.players)) + 1

    def _advance_turn(self, state: BlackLedgerState) -> None:
        state.turn_counts[state.current_player] += 1
        state.turn_count += 1
        if state.end_triggered and state.round_turns_remaining and state.round_turns_remaining > 0:
            state.round_turns_remaining -= 1
        state.current_player = (state.current_player + 1) % len(state.players)
        state.metrics_data["turn_started"] = 0

    def debug_snapshot(self, state: BlackLedgerState) -> dict:
        return {
            "ledger_won": dict(state.ledger_won_counts),
            "closed": {
                player.player_id: set(player.closed_accounts)
                for player in state.players
            },
            "total_ledger": {
                player.player_id: len(player.tableau) + sum(len(cards) for cards in player.closed_accounts.values())
                for player in state.players
            },
        }

    def debug_summary(
        self,
        state: BlackLedgerState,
        player_id: int,
        action: BlackLedgerAction,
        before: dict | None = None,
    ) -> str:
        revealed = str(state.last_revealed) if state.last_revealed else "none"
        before = before or self.debug_snapshot(state)
        won = [
            f"P{pid}+{state.ledger_won_counts[pid] - before['ledger_won'].get(pid, 0)}"
            for pid in range(len(state.players))
            if state.ledger_won_counts[pid] - before["ledger_won"].get(pid, 0)
        ]
        closed_events = []
        for player in state.players:
            old_closed = before["closed"].get(player.player_id, set())
            newly_closed = sorted(set(player.closed_accounts) - old_closed)
            if newly_closed:
                closed_events.append(f"P{player.player_id}:{','.join(newly_closed)}")
        line = " | ".join(
            f"{idx}:{slot.card}({self._commitment_debug(slot)})"
            for idx, slot in enumerate(state.line)
        ) or "empty"
        player_parts = []
        for player in state.players:
            closed_count = len(player.closed_accounts)
            loose = len(player.tableau)
            total_cards = loose + sum(len(cards) for cards in player.closed_accounts.values())
            player_parts.append(
                f"P{player.player_id}: loose={loose} closed={closed_count} total_ledger={total_cards} "
                f"heat={player.heat} hand={len(player.hand)} spent={len(player.spent)}"
            )
        end = state.end_condition or "none"
        return (
            f"T{state.turn_count} P{player_id} revealed={revealed} action={action}\n"
            f"  cards_won: {', '.join(won) if won else 'none'}; accounts_closed: {', '.join(closed_events) if closed_events else 'none'}\n"
            f"  line: {line}\n"
            f"  players: {'; '.join(player_parts)}\n"
            f"  end_condition={end}"
        )

    def _commitment_debug(self, slot: LineSlot) -> str:
        if not slot.commitments:
            return "no stakes"
        by_owner: dict[int, list[str]] = defaultdict(list)
        for commitment in slot.commitments:
            value = str(commitment.stake.value) if commitment.face_up else "?"
            by_owner[commitment.owner].append(value)
        return ", ".join(f"P{owner}=[{','.join(values)}]" for owner, values in sorted(by_owner.items()))

    def _is_burnable(self, state: BlackLedgerState, line_index: int) -> bool:
        return line_index < max(0, len(state.line) - 3)

    def _take_stake_from_hand(self, player: PlayerState, stake_id: str) -> StakeCard:
        for stake in player.hand:
            if stake.id == stake_id:
                player.hand.remove(stake)
                return stake
        raise ValueError(f"Stake card {stake_id} is not in player {player.player_id}'s hand")

    def _clean_claim_bonus(self, player: PlayerState) -> None:
        returned = sorted(player.spent, key=lambda c: c.value)[:2]
        for stake in returned:
            player.spent.remove(stake)
            player.hand.append(stake)

    def _heat_penalty(self, heat: int) -> int:
        if heat >= 5:
            return -12
        if heat >= 3:
            return -5
        return 0
