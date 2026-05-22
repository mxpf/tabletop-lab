from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


@dataclass
class Zone(Generic[T]):
    name: str
    public: bool = True
    cards: list[T] = field(default_factory=list)

    def add(self, card: T) -> None:
        self.cards.append(card)

    def extend(self, cards: Iterable[T]) -> None:
        self.cards.extend(cards)

    def remove(self, card: T) -> T:
        self.cards.remove(card)
        return card

    def pop_top(self) -> T:
        if not self.cards:
            raise ValueError(f"{self.name} is empty")
        return self.cards.pop()

    def pop_left(self) -> T:
        if not self.cards:
            raise ValueError(f"{self.name} is empty")
        return self.cards.pop(0)

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self) -> Iterator[T]:
        return iter(self.cards)


@dataclass
class Deck(Zone[T]):
    public: bool = False

    def shuffle(self, rng) -> None:
        rng.shuffle(self.cards)

    def draw(self, n: int = 1) -> list[T]:
        if n < 0:
            raise ValueError("cannot draw a negative number of cards")
        if n > len(self.cards):
            raise ValueError(f"cannot draw {n} from {self.name}; only {len(self.cards)} remain")
        return [self.pop_top() for _ in range(n)]
