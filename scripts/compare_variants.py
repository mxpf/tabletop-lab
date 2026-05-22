from __future__ import annotations

import argparse
import json
import sys

from tabletop_lab.engine import Simulator
from tabletop_lab.games.black_ledger import BOT_REGISTRY, BlackLedgerRules, get_variant
from tabletop_lab.games.black_ledger.metrics import summarize_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Black Ledger variants.")
    parser.add_argument("variants", nargs="*", default=["base_3p", "furnace_5", "furnace_7"])
    parser.add_argument("-n", "--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--bots", default="random,builder,greedy")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--json", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.progress_every < 1:
        raise SystemExit("--progress-every must be at least 1")
    names = [name.strip() for name in args.bots.split(",")]

    def factory():
        return [BOT_REGISTRY[name]() for name in names]

    sim = Simulator()
    summaries = {}
    for variant_name in args.variants:
        def progress(completed: int, total: int, elapsed: float, variant: str = variant_name) -> None:
            if completed != total and completed % args.progress_every != 0:
                return
            games_per_sec = completed / elapsed if elapsed > 0 else 0
            print(
                f"progress {variant}: {completed}/{total} games, {games_per_sec:.1f} games/sec",
                file=sys.stderr,
                flush=True,
            )

        results = sim.run_many(
            BlackLedgerRules(),
            factory,
            get_variant(variant_name),
            args.games,
            seed=args.seed,
            progress_callback=progress if args.progress else None,
        )
        summary = summarize_results(results)
        summaries[variant_name] = {
            "end_condition_rates": summary["end_condition_rates"],
            "average_closed_accounts": summary["average_closed_accounts"],
            "average_loose_cards": summary["average_loose_cards"],
            "average_final_scores": summary["average_final_scores"],
            "win_rates_by_seat": summary["win_rates"],
            "win_rates_by_bot": summary["win_rates_by_bot"],
            "first_player_win_rates_by_seat": summary["first_player_win_rates_by_seat"],
            "average_turns": summary["average_turns"],
            "average_closed_accounts_total": summary["average_closed_accounts_total"],
            "average_loose_cards_total": summary["average_loose_cards_total"],
            "average_ledger_cards_won": summary["average_ledger_cards_won"],
            "action_counts": summary["action_counts"],
            "action_counts_by_player": summary["action_counts_by_player"],
            "claim_count": summary["claim_count"],
            "claim_wins": summary["claim_wins"],
            "burn_count": summary["burn_count"],
            "call_attempts": summary["call_attempts"],
            "call_success_rate": summary["call_success_rate"],
            "count_actions": summary["count_actions"],
            "furnace_resolutions": summary["furnace_resolutions"],
            "furnace_wins": summary["furnace_wins"],
            "furnace_empty_discards": summary["furnace_empty_discards"],
            "furnace_tie_discards": summary["furnace_tie_discards"],
        }
    print_table(summaries)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(summaries, handle, indent=2, sort_keys=True)
    else:
        print("\nJSON")
        print(json.dumps(summaries, indent=2, sort_keys=True))


def print_table(summaries: dict) -> None:
    headers = [
        "variant",
        "turns",
        "end rates",
        "closed total",
        "loose total",
        "scores P0/P1/P2",
        "wins seat P0/P1/P2",
        "wins bot R/B/G",
        "ledger won P0/P1/P2",
        "actions",
        "claim/win",
        "burn",
        "call/success",
        "count",
        "furnace W/E/T",
        "first seat P0/P1/P2",
    ]
    rows = []
    for variant, summary in summaries.items():
        rows.append(
            [
                variant,
                f"{summary['average_turns']:.2f}",
                compact_rates(summary["end_condition_rates"]),
                f"{summary['average_closed_accounts_total']:.2f}",
                f"{summary['average_loose_cards_total']:.2f}",
                player_triplet(summary["average_final_scores"]),
                player_triplet(summary["win_rates_by_seat"]),
                bot_triplet(summary["win_rates_by_bot"]),
                player_triplet(summary["average_ledger_cards_won"]),
                compact_counts(summary["action_counts"]),
                f"{summary['claim_count']}/{summary['claim_wins']}",
                str(summary["burn_count"]),
                f"{summary['call_attempts']}/{summary['call_success_rate']:.1%}",
                str(summary["count_actions"]),
                f"{summary['furnace_wins']}/{summary['furnace_empty_discards']}/{summary['furnace_tie_discards']}",
                player_triplet(summary["first_player_win_rates_by_seat"]),
            ]
        )
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)))


def player_triplet(values: dict) -> str:
    return "/".join(f"{values.get(player, values.get(str(player), 0)):.3g}" for player in (0, 1, 2))


def bot_triplet(values: dict) -> str:
    return "/".join(f"{values.get(bot, 0):.3g}" for bot in ("RandomBot", "BuilderBot", "GreedyBot"))


def compact_rates(values: dict) -> str:
    return ",".join(f"{key}:{value:.2f}" for key, value in sorted(values.items()))


def compact_counts(values: dict) -> str:
    return ",".join(f"{key}:{value}" for key, value in sorted(values.items()))


if __name__ == "__main__":
    main()
