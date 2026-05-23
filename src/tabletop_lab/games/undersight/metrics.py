from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def summarize_results(results: list[Any]) -> dict[str, Any]:
    wins = Counter()
    bot_wins = Counter()
    bot_games = Counter()
    end_conditions = Counter()
    turns = 0
    severances = 0
    spillovers = 0
    final_scores = Counter()
    actions = Counter()
    actions_by_player: dict[int, Counter[str]] = defaultdict(Counter)
    for result in results:
        share = 1 / len(result.winners)
        for winner in result.winners:
            wins[winner] += share
            bot_wins[result.bot_lineup[winner]] += share
        for bot in result.bot_lineup:
            bot_games[bot] += 1
        end_conditions[result.metrics["end_condition"]] += 1
        turns += result.metrics["total_turns"]
        severances += result.metrics["severance_count"]
        spillovers += result.metrics.get("spillovers_created", 0)
        actions.update(result.metrics["action_counts"])
        for player, score in result.metrics["final_scores"].items():
            final_scores[int(player)] += score
        for player, counts in result.metrics["action_counts_by_player"].items():
            actions_by_player[int(player)].update(counts)
    player_ids = sorted(final_scores)
    return {
        "games": len(results),
        "win_rates": {player: wins[player] / len(results) for player in sorted(wins)} if results else {},
        "win_rates_by_bot": {bot: bot_wins[bot] / bot_games[bot] for bot in sorted(bot_games)},
        "end_condition_rates": {key: value / len(results) for key, value in end_conditions.items()} if results else {},
        "average_turns": turns / len(results) if results else 0,
        "average_severances": severances / len(results) if results else 0,
        "average_spillovers_created": spillovers / len(results) if results else 0,
        "average_final_scores": {player: final_scores[player] / len(results) for player in player_ids} if results else {},
        "action_counts": dict(actions),
        "action_counts_by_player": {player: dict(actions_by_player[player]) for player in player_ids},
    }
