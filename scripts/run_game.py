from __future__ import annotations

import argparse
import json

from tabletop_lab.engine import Simulator
from tabletop_lab.games.black_ledger import BOT_REGISTRY, BlackLedgerRules, get_variant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one Black Ledger game.")
    parser.add_argument("--game", default="black_ledger", choices=["black_ledger"])
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--variant", default="base_3p")
    parser.add_argument("--bots", default="random,builder,greedy")
    parser.add_argument("--transcript", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bots = [BOT_REGISTRY[name.strip()]() for name in args.bots.split(",")]
    result = Simulator().run_game(
        BlackLedgerRules(),
        bots,
        get_variant(args.variant),
        seed=args.seed,
        transcript=args.transcript or args.debug,
        debug=args.debug,
    )
    print(json.dumps(result.metrics, indent=2, sort_keys=True))
    if result.transcript:
        print("\nTranscript")
        print(result.transcript)


if __name__ == "__main__":
    main()
