from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from tabletop_lab.engine import Simulator
from tabletop_lab.games.black_ledger import BOT_REGISTRY, VARIANTS, BlackLedgerRules, get_variant
from tabletop_lab.games.black_ledger.metrics import summarize_results

from . import database


BOT_LABELS = {
    "random": "RandomBot",
    "builder": "BuilderBot",
    "greedy": "GreedyBot",
    "denial": "DenialBot",
    "bluffer": "BlufferBot",
    "conservative": "ConservativeBot",
}


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_UPLOAD_DIR = PROJECT_ROOT / "uploads"


def available_black_ledger_variants() -> list[str]:
    preferred = [
        "five_numerals_starting_ledger_3",
        "five_num_start3_loose1",
        "five_num_start3_loose2",
        "five_num_start3_loose3",
        "base_3p",
    ]
    ordered = [name for name in preferred if name in VARIANTS]
    ordered.extend(name for name in sorted(VARIANTS) if name not in ordered)
    return ordered


def available_bots() -> dict[str, str]:
    return {name: BOT_LABELS.get(name, name) for name in BOT_REGISTRY}


def start_black_ledger_run(
    *,
    game_id: int,
    variant_name: str,
    bot_names: list[str],
    number_of_games: int,
    seed: int | None,
    progress_every: int,
    max_turns: int = 200,
) -> int:
    if game_id != database.BUILT_IN_BLACK_LEDGER_ID:
        raise ValueError("only the built-in Black Ledger game can run simulations right now")
    if variant_name not in VARIANTS:
        raise ValueError(f"unknown variant: {variant_name}")
    if len(bot_names) != 3:
        raise ValueError("Black Ledger requires exactly three bots")
    unknown = [name for name in bot_names if name not in BOT_REGISTRY]
    if unknown:
        raise ValueError(f"unknown bot(s): {', '.join(unknown)}")
    if number_of_games < 1:
        raise ValueError("number of games must be at least 1")
    if progress_every < 1:
        raise ValueError("progress interval must be at least 1")

    run = database.create_simulation_run(
        game_id=game_id,
        variant_name=variant_name,
        bot_lineup=bot_names,
        number_of_games=number_of_games,
        seed=seed,
    )
    thread = threading.Thread(
        target=_run_black_ledger_worker,
        kwargs={
            "run_id": run.id,
            "variant_name": variant_name,
            "bot_names": bot_names,
            "number_of_games": number_of_games,
            "seed": seed,
            "progress_every": progress_every,
            "max_turns": max_turns,
        },
        daemon=True,
    )
    thread.start()
    return run.id


def run_status(run_id: int) -> dict[str, Any]:
    run = database.get_run(run_id)
    elapsed = run.elapsed_seconds or 0.0
    if run.status == "running" and run.started_at:
        elapsed = max(elapsed, 0.0)
    completed = run.progress_completed
    total = run.progress_total
    games_per_second = completed / elapsed if elapsed > 0 else 0.0
    remaining = total - completed
    eta = remaining / games_per_second if games_per_second > 0 and run.status in {"queued", "running"} else 0.0
    percent = (completed / total * 100) if total else 0.0
    return {
        "id": run.id,
        "status": run.status,
        "completed": completed,
        "total": total,
        "percent": percent,
        "elapsed_seconds": elapsed,
        "eta_seconds": eta,
        "games_per_second": games_per_second,
        "error_message": run.error_message,
        "detail_url": f"/runs/{run.id}",
    }


def extract_pdf_text(source_file, filename: str) -> tuple[str, str]:
    from pypdf import PdfReader

    upload_dir = Path(DEFAULT_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=upload_dir) as tmp:
        shutil.copyfileobj(source_file, tmp)
        stored_path = Path(tmp.name)

    reader = PdfReader(str(stored_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip(), str(stored_path)


def comparison_rows(runs) -> list[dict[str, Any]]:
    rows = []
    for run in runs:
        summary = run.summary_json or {}
        end_rates = summary.get("end_condition_rates", {})
        rows.append(
            {
                "id": run.id,
                "variant": run.variant_name,
                "bots": ", ".join(run.bot_lineup),
                "games": run.number_of_games,
                "average_turns": summary.get("average_turns", 0),
                "closed_end_rate": end_rates.get("closed_accounts", 0),
                "deck_end_rate": end_rates.get("deck_empty", 0),
                "closed_total": summary.get("average_closed_accounts_total", 0),
                "average_scores": summary.get("average_final_scores", {}),
                "win_rates": summary.get("win_rates", {}),
                "claim_count": summary.get("claim_count", 0),
                "call_success_rate": summary.get("call_success_rate", 0),
                "burn_count": summary.get("burn_count", 0),
                "furnace_resolutions": summary.get("furnace_resolutions", 0),
                "furnace_wins": summary.get("furnace_wins", 0),
                "furnace_empty_discards": summary.get("furnace_empty_discards", 0),
                "furnace_tie_discards": summary.get("furnace_tie_discards", 0),
            }
        )
    return rows


def _run_black_ledger_worker(
    *,
    run_id: int,
    variant_name: str,
    bot_names: list[str],
    number_of_games: int,
    seed: int | None,
    progress_every: int,
    max_turns: int,
) -> None:
    start = time.perf_counter()
    try:
        database.mark_run_running(run_id)

        def factory():
            return [BOT_REGISTRY[name]() for name in bot_names]

        def progress(completed: int, total: int, elapsed: float) -> None:
            if completed == total or completed % progress_every == 0:
                database.update_run_progress(run_id, completed, total, elapsed)

        results = Simulator().run_many(
            BlackLedgerRules(),
            factory,
            get_variant(variant_name),
            number_of_games,
            seed=seed,
            max_turns=max_turns,
            progress_callback=progress,
        )
        elapsed = time.perf_counter() - start
        summary = summarize_results(results)
        database.complete_run(run_id, summary=summary, elapsed_seconds=elapsed)
    except Exception as exc:  # noqa: BLE001 - this records background failures for the UI.
        elapsed = time.perf_counter() - start
        database.fail_run(run_id, error_message=str(exc), elapsed_seconds=elapsed)
