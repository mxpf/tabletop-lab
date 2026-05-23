from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Callable

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


@dataclass(frozen=True)
class GameCliConfig:
    rules_cls: type
    bot_registry: dict
    get_variant: Callable
    default_bots: str


GAMES = {
    "black_ledger": GameCliConfig(
        BlackLedgerRules,
        BLACK_LEDGER_BOTS,
        get_black_ledger_variant,
        "random,builder,greedy",
    ),
    "undersight": GameCliConfig(
        UndersightRules,
        UNDERSIGHT_BOTS,
        get_undersight_variant,
        "random,greedy,safety",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one tabletop game.")
    parser.add_argument("--game", default="black_ledger", choices=sorted(GAMES))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--variant", default="base_3p")
    parser.add_argument("--bots", default=None)
    parser.add_argument("--transcript", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GAMES[args.game]
    bot_lineup = args.bots or config.default_bots
    bots = [config.bot_registry[name.strip()]() for name in bot_lineup.split(",")]
    result = Simulator().run_game(
        config.rules_cls(),
        bots,
        config.get_variant(args.variant),
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
