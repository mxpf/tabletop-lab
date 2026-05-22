from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence


class GameRules(ABC):
    @abstractmethod
    def setup(self, rng, variant: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def legal_actions(self, state: Any, player_id: int) -> Sequence[Any]:
        raise NotImplementedError

    @abstractmethod
    def apply_action(self, state: Any, action: Any, rng) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_game_over(self, state: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    def should_finish_round(self, state: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    def score(self, state: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def visible_state_for(self, state: Any, player_id: int) -> Any:
        raise NotImplementedError
