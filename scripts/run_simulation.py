from __future__ import annotations

import argparse
import csv
import json
import sys

from tabletop_lab.engine import Simulator
from tabletop_lab.games.black_ledger import (
    BOT_REGISTRY as BLACK_LEDGER_BOTS,
    BlackLedgerRules,
    get_variant as get_black_ledger_variant,
)
from tabletop_lab.games.black_ledger.metrics import summarize_results as summarize_black_ledger_results
from tabletop_lab.games.undersight import (
    BOT_REGISTRY as UNDERSIGHT_BOTS,
    UndersightRules,
    get_variant as get_undersight_variant,
)
from tabletop_lab.games.undersight.metrics import summarize_results as summarize_undersight_results


GAMES = {
    "black_ledger": (
        BlackLedgerRules,
        BLACK_LEDGER_BOTS,
        get_black_ledger_variant,
        summarize_black_ledger_results,
    ),
    "undersight": (
        UndersightRules,
        UNDERSIGHT_BOTS,
        get_undersight_variant,
        summarize_undersight_results,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run many tabletop games.")
    parser.add_argument("--game", default="black_ledger", choices=sorted(GAMES))
    parser.add_argument("-n", "--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--variant", default="base_3p")
    parser.add_argument("--bots", default="random,builder,greedy")
    parser.add_argument("--max-turns", type=int, default=200)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--csv", default=None)
    parser.add_argument("--json", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.progress_every < 1:
        raise SystemExit("--progress-every must be at least 1")
    if args.max_turns is not None and args.max_turns < 1:
        raise SystemExit("--max-turns must be at least 1")
    names = [name.strip() for name in args.bots.split(",")]
    rules_cls, bot_registry, get_variant, summarize_results = GAMES[args.game]

    def factory():
        return [bot_registry[name]() for name in names]

    def progress(completed: int, total: int, elapsed: float) -> None:
        if not args.progress:
            return
        if completed != total and completed % args.progress_every != 0:
            return
        games_per_sec = completed / elapsed if elapsed > 0 else 0
        print(
            f"progress: {completed}/{total} games, {games_per_sec:.1f} games/sec",
            file=sys.stderr,
            flush=True,
        )

    results = Simulator().run_many(
        rules_cls(),
        factory,
        get_variant(args.variant),
        args.games,
        seed=args.seed,
        max_turns=args.max_turns,
        progress_callback=progress if args.progress else None,
    )
    summary = summarize_results(results)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump([r.metrics for r in results], handle, indent=2, sort_keys=True)
    if args.csv:
        rows = [flatten(r.metrics) for r in results]
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(rows[0]) if rows else [])
            writer.writeheader()
            writer.writerows(rows)


def flatten(row: dict) -> dict:
    flat = {}
    for key, value in row.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                flat[f"{key}_{subkey}"] = subvalue
        else:
            flat[key] = value
    return flat


if __name__ == "__main__":
    main()
