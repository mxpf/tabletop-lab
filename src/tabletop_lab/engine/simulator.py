from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .bots import Bot
from .transcript import Transcript


@dataclass
class GameResult:
    seed: int
    variant_name: str
    bot_lineup: list[str]
    winners: list[int]
    scores: dict[int, int]
    metrics: dict[str, Any]
    transcript: Transcript | None = None
    state: Any = None


class Simulator:
    def run_game(
        self,
        rules,
        bots: Sequence[Bot],
        variant,
        seed: int | None = None,
        transcript: bool = False,
        max_turns: int | None = None,
        debug: bool = False,
    ) -> GameResult:
        seed = random.randrange(2**63) if seed is None else seed
        rng = random.Random(seed)
        state = rules.setup(rng, variant)
        state.seed = seed
        if len(bots) != len(state.players):
            raise ValueError(f"expected {len(state.players)} bots, got {len(bots)}")
        log = Transcript() if transcript else None

        while not rules.is_game_over(state):
            if max_turns is not None and state.turn_count >= max_turns:
                raise RuntimeError(f"game exceeded max_turns={max_turns} for seed {seed}")
            if hasattr(rules, "begin_turn"):
                rules.begin_turn(state)
            player_id = state.current_player
            legal = list(rules.legal_actions(state, player_id))
            if not legal:
                raise RuntimeError(f"player {player_id} has no legal actions")
            action = bots[player_id].choose_action(rules.visible_state_for(state, player_id), legal, rng)
            if action not in legal:
                raise ValueError(f"{bots[player_id].name} chose illegal action {action}")
            if log and not debug:
                log.add(f"T{state.turn_count + 1} P{player_id}: {action}")
            debug_snapshot = rules.debug_snapshot(state) if log and debug and hasattr(rules, "debug_snapshot") else None
            rules.apply_action(state, action, rng)
            if log and debug:
                if hasattr(rules, "debug_summary"):
                    log.add(rules.debug_summary(state, player_id, action, debug_snapshot))
                else:
                    log.add(f"T{state.turn_count} P{player_id}: {action}")

        scored = rules.score(state)
        return GameResult(
            seed=seed,
            variant_name=variant.name,
            bot_lineup=[bot.name for bot in bots],
            winners=scored["winners"],
            scores=scored["scores"],
            metrics=rules.metrics(state),
            transcript=log,
            state=state,
        )

    def run_many(
        self,
        rules,
        bot_factory: Callable[[], Sequence[Bot]],
        variant,
        n: int,
        seed: int | None = None,
        max_turns: int | None = None,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> list[GameResult]:
        master = random.Random(seed)
        start = time.perf_counter()
        results = []
        for completed in range(1, n + 1):
            results.append(
                self.run_game(
                    rules,
                    bot_factory(),
                    variant,
                    seed=master.randrange(2**63),
                    max_turns=max_turns,
                )
            )
            if progress_callback:
                progress_callback(completed, n, time.perf_counter() - start)
        return results
