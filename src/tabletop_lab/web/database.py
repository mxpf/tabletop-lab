from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import GameRecord, SimulationRunRecord


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "tabletop_lab.sqlite"
BUILT_IN_BLACK_LEDGER_ID = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_database_path() -> Path:
    return Path(os.environ.get("TABLETOP_LAB_DB", DEFAULT_DB_PATH))


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: str | Path | None = None) -> None:
    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                rules_text TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL CHECK (source_type IN ('manual', 'pdf', 'built_in')),
                notes TEXT NOT NULL DEFAULT '',
                source_path TEXT
            );

            CREATE TABLE IF NOT EXISTS simulation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                variant_name TEXT NOT NULL,
                bot_lineup TEXT NOT NULL,
                number_of_games INTEGER NOT NULL,
                seed INTEGER,
                status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'complete', 'failed')),
                progress_completed INTEGER NOT NULL DEFAULT 0,
                progress_total INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                completed_at TEXT,
                elapsed_seconds REAL,
                summary_json TEXT,
                error_message TEXT
            );
            """
        )
        preload_black_ledger(db)


def preload_black_ledger(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT id FROM games WHERE id = ?", (BUILT_IN_BLACK_LEDGER_ID,)).fetchone()
    if existing:
        return
    now = utc_now()
    db.execute(
        """
        INSERT INTO games (
            id, name, description, created_at, updated_at, rules_text, source_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            BUILT_IN_BLACK_LEDGER_ID,
            "Black Ledger",
            "A 3-player gambling-den card game of hidden Stakes, bluffing, denial, Heat, and closing Accounts.",
            now,
            now,
            _black_ledger_rules_text(),
            "built_in",
            "Built-in playable module.",
        ),
    )


def create_game(
    *,
    name: str,
    description: str = "",
    rules_text: str = "",
    source_type: str = "manual",
    notes: str = "",
    source_path: str | None = None,
    db_path: str | Path | None = None,
) -> GameRecord:
    now = utc_now()
    with connect(db_path) as db:
        cursor = db.execute(
            """
            INSERT INTO games (
                name, description, created_at, updated_at, rules_text, source_type, notes, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, now, now, rules_text, source_type, notes, source_path),
        )
        game_id = cursor.lastrowid
        db.commit()
    return get_game(game_id, db_path=db_path)


def list_games(db_path: str | Path | None = None) -> list[GameRecord]:
    with connect(db_path) as db:
        rows = db.execute("SELECT * FROM games ORDER BY id").fetchall()
    return [_game_from_row(row) for row in rows]


def get_game(game_id: int, db_path: str | Path | None = None) -> GameRecord:
    with connect(db_path) as db:
        row = db.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if not row:
        raise KeyError(f"game not found: {game_id}")
    return _game_from_row(row)


def update_game_rules(
    game_id: int,
    *,
    rules_text: str,
    source_type: str,
    source_path: str | None = None,
    db_path: str | Path | None = None,
) -> GameRecord:
    with connect(db_path) as db:
        db.execute(
            """
            UPDATE games
            SET rules_text = ?, source_type = ?, source_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (rules_text, source_type, source_path, utc_now(), game_id),
        )
    return get_game(game_id, db_path=db_path)


def create_simulation_run(
    *,
    game_id: int,
    variant_name: str,
    bot_lineup: Iterable[str],
    number_of_games: int,
    seed: int | None,
    db_path: str | Path | None = None,
) -> SimulationRunRecord:
    with connect(db_path) as db:
        cursor = db.execute(
            """
            INSERT INTO simulation_runs (
                game_id, variant_name, bot_lineup, number_of_games, seed, status,
                progress_completed, progress_total
            ) VALUES (?, ?, ?, ?, ?, 'queued', 0, ?)
            """,
            (game_id, variant_name, json.dumps(list(bot_lineup)), number_of_games, seed, number_of_games),
        )
        run_id = cursor.lastrowid
        db.commit()
    return get_run(run_id, db_path=db_path)


def mark_run_running(run_id: int, db_path: str | Path | None = None) -> None:
    with connect(db_path) as db:
        db.execute(
            "UPDATE simulation_runs SET status = 'running', started_at = ? WHERE id = ?",
            (utc_now(), run_id),
        )


def update_run_progress(
    run_id: int,
    completed: int,
    total: int,
    elapsed_seconds: float | None = None,
    db_path: str | Path | None = None,
) -> None:
    with connect(db_path) as db:
        db.execute(
            """
            UPDATE simulation_runs
            SET progress_completed = ?, progress_total = ?, elapsed_seconds = ?
            WHERE id = ?
            """,
            (completed, total, elapsed_seconds, run_id),
        )


def complete_run(
    run_id: int,
    *,
    summary: dict[str, Any],
    elapsed_seconds: float,
    db_path: str | Path | None = None,
) -> None:
    with connect(db_path) as db:
        total = db.execute(
            "SELECT progress_total FROM simulation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()["progress_total"]
        db.execute(
            """
            UPDATE simulation_runs
            SET status = 'complete',
                progress_completed = ?,
                completed_at = ?,
                elapsed_seconds = ?,
                summary_json = ?,
                error_message = NULL
            WHERE id = ?
            """,
            (total, utc_now(), elapsed_seconds, json.dumps(summary, sort_keys=True), run_id),
        )


def fail_run(
    run_id: int,
    *,
    error_message: str,
    elapsed_seconds: float | None = None,
    db_path: str | Path | None = None,
) -> None:
    with connect(db_path) as db:
        db.execute(
            """
            UPDATE simulation_runs
            SET status = 'failed',
                completed_at = ?,
                elapsed_seconds = ?,
                error_message = ?
            WHERE id = ?
            """,
            (utc_now(), elapsed_seconds, error_message, run_id),
        )


def get_run(run_id: int, db_path: str | Path | None = None) -> SimulationRunRecord:
    with connect(db_path) as db:
        row = db.execute("SELECT * FROM simulation_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        raise KeyError(f"run not found: {run_id}")
    return _run_from_row(row)


def list_runs_for_game(game_id: int, db_path: str | Path | None = None) -> list[SimulationRunRecord]:
    with connect(db_path) as db:
        rows = db.execute(
            "SELECT * FROM simulation_runs WHERE game_id = ? ORDER BY id DESC",
            (game_id,),
        ).fetchall()
    return [_run_from_row(row) for row in rows]


def list_runs(run_ids: Iterable[int], db_path: str | Path | None = None) -> list[SimulationRunRecord]:
    ids = list(run_ids)
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with connect(db_path) as db:
        rows = db.execute(
            f"SELECT * FROM simulation_runs WHERE id IN ({placeholders}) ORDER BY id",
            ids,
        ).fetchall()
    return [_run_from_row(row) for row in rows]


def _game_from_row(row: sqlite3.Row) -> GameRecord:
    return GameRecord(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        rules_text=row["rules_text"],
        source_type=row["source_type"],
        notes=row["notes"],
        source_path=row["source_path"],
    )


def _run_from_row(row: sqlite3.Row) -> SimulationRunRecord:
    summary = json.loads(row["summary_json"]) if row["summary_json"] else None
    return SimulationRunRecord(
        id=row["id"],
        game_id=row["game_id"],
        variant_name=row["variant_name"],
        bot_lineup=json.loads(row["bot_lineup"]),
        number_of_games=row["number_of_games"],
        seed=row["seed"],
        status=row["status"],
        progress_completed=row["progress_completed"],
        progress_total=row["progress_total"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        elapsed_seconds=row["elapsed_seconds"],
        summary_json=summary,
        error_message=row["error_message"],
    )


def _black_ledger_rules_text() -> str:
    return (
        "Black Ledger is a 3-player gambling-den card game of hidden Stakes, bluffing, "
        "denial, Heat, and closing Accounts before cards reach the Furnace. The built-in "
        "module supports deterministic simulations, variants, bots, metrics, and seed replay."
    )
