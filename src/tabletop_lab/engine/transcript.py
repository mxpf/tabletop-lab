from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Transcript:
    entries: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.entries.append(message)

    def __str__(self) -> str:
        return "\n".join(self.entries)
