from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GameRecord:
    id: int
    name: str
    description: str
    created_at: str
    updated_at: str
    rules_text: str
    source_type: str
    notes: str = ""
    source_path: str | None = None
    archived_at: str | None = None


@dataclass(frozen=True)
class SimulationRunRecord:
    id: int
    game_id: int
    variant_name: str
    bot_lineup: list[str]
    number_of_games: int
    seed: int | None
    status: str
    progress_completed: int
    progress_total: int
    started_at: str | None
    completed_at: str | None
    elapsed_seconds: float | None
    summary_json: dict[str, Any] | None
    error_message: str | None


@dataclass(frozen=True)
class CodexJobRecord:
    id: int
    game_id: int
    status: str
    branch_name: str
    prompt_path: str
    log_text: str
    test_output: str
    git_status_output: str
    changed_files_json: list[str]
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
