from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def summarize_results(results: list[Any]) -> dict[str, Any]:
    wins = Counter()
    bot_wins = Counter()
    bot_games = Counter()
    first_player_wins = Counter()
    first_player_games = Counter()
    end_conditions = Counter()
    scores = Counter()
    closed = Counter()
    loose = Counter()
    ledger_won = Counter()
    turns = Counter()
    action_counts = Counter()
    totals = Counter()
    actions_by_player: dict[int, Counter[str]] = defaultdict(Counter)
    total_turns = 0
    for result in results:
        share = 1 / len(result.winners)
        for winner in result.winners:
            wins[winner] += share
            bot_wins[result.bot_lineup[winner]] += share
        for bot in result.bot_lineup:
            bot_games[bot] += 1
        first_player = result.metrics["first_player"]
        first_player_games[first_player] += 1
        if first_player in result.winners:
            first_player_wins[first_player] += 1
        end_conditions[result.metrics["end_condition"]] += 1
        total_turns += result.metrics["total_turns"]
        action_counts.update(result.metrics["action_counts"])
        for key in (
            "claim_wins",
            "burn_count",
            "call_attempts",
            "call_successes",
            "call_failures",
            "count_actions",
            "furnace_resolutions",
            "furnace_wins",
            "furnace_empty_discards",
            "furnace_tie_discards",
            "manual_claim_tie_discards",
        ):
            totals[key] += result.metrics.get(key, 0)
        for player, value in result.metrics["final_scores"].items():
            scores[int(player)] += value
        for player, value in result.metrics["closed_accounts"].items():
            closed[int(player)] += value
        for player, value in result.metrics["loose_cards"].items():
            loose[int(player)] += value
        for player, value in result.metrics["ledger_cards_won"].items():
            ledger_won[int(player)] += value
        for player, value in result.metrics["turns_by_player"].items():
            turns[int(player)] += value
        for player, counts in result.metrics["action_counts_by_player"].items():
            actions_by_player[int(player)].update(counts)
    player_ids = sorted(scores)
    return {
        "games": len(results),
        "win_rates": {player: wins[player] / len(results) for player in sorted(wins)},
        "win_rates_by_bot": {
            bot: bot_wins[bot] / bot_games[bot]
            for bot in sorted(bot_games)
        },
        "first_player_win_rates_by_seat": {
            player: first_player_wins[player] / first_player_games[player]
            for player in sorted(first_player_games)
        },
        "end_condition_rates": {k: v / len(results) for k, v in end_conditions.items()},
        "average_turns": total_turns / len(results) if results else 0,
        "average_final_scores": {player: scores[player] / len(results) for player in player_ids},
        "average_closed_accounts": {player: closed[player] / len(results) for player in player_ids},
        "average_closed_accounts_total": sum(closed.values()) / len(results) if results else 0,
        "average_loose_cards": {player: loose[player] / len(results) for player in player_ids},
        "average_loose_cards_total": sum(loose.values()) / len(results) if results else 0,
        "average_ledger_cards_won": {player: ledger_won[player] / len(results) for player in player_ids},
        "average_turn_count_by_player": {player: turns[player] / len(results) for player in player_ids},
        "action_counts": dict(action_counts),
        "action_counts_by_player": {
            player: dict(actions_by_player[player])
            for player in player_ids
        },
        "claim_count": action_counts["Claim"],
        "claim_wins": totals["claim_wins"],
        "burn_count": totals["burn_count"],
        "call_attempts": totals["call_attempts"],
        "call_success_rate": (
            totals["call_successes"] / totals["call_attempts"]
            if totals["call_attempts"]
            else 0
        ),
        "count_actions": totals["count_actions"],
        "furnace_resolutions": totals["furnace_resolutions"],
        "furnace_wins": totals["furnace_wins"],
        "furnace_empty_discards": totals["furnace_empty_discards"],
        "furnace_tie_discards": totals["furnace_tie_discards"],
    }
