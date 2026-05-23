from __future__ import annotations

import argparse
import json

from tabletop_lab.engine import Simulator
from tabletop_lab.games.black_ledger import (
    BOT_REGISTRY as BLACK_LEDGER_BOTS,
    BlackLedgerRules,
    get_variant as get_black_ledger_variant,
)
from tabletop_lab.games.undersight import (
    BOT_REGISTRY as UNDERSIGHT_BOTS,
    UndersightRules,
    get_variant as get_undersight_variant,
)


GAMES = {
    "black_ledger": (BlackLedgerRules, BLACK_LEDGER_BOTS, get_black_ledger_variant),
    "undersight": (UndersightRules, UNDERSIGHT_BOTS, get_undersight_variant),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one tabletop game.")
    parser.add_argument("--game", default="black_ledger", choices=sorted(GAMES))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--variant", default="base_3p")
    parser.add_argument("--bots", default="random,builder,greedy")
    parser.add_argument("--transcript", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rules_cls, bot_registry, get_variant = GAMES[args.game]
    bots = [bot_registry[name.strip()]() for name in args.bots.split(",")]
    result = Simulator().run_game(
        rules_cls(),
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
