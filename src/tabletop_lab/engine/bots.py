from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence


class Bot(ABC):
    name = "Bot"

    @abstractmethod
    def choose_action(self, visible_state: Any, legal_actions: Sequence[Any], rng) -> Any:
        raise NotImplementedError
