from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import re
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


class RunManager:
    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tabletop-run")
        self._active: dict[int, Future] = {}

    def start_black_ledger_run(
        self,
        *,
        game_id: int,
        variant_name: str,
        bot_names: list[str],
        number_of_games: int,
        seed: int | None,
        progress_every: int,
        max_turns: int = 200,
    ) -> int:
        _validate_black_ledger_run(game_id, variant_name, bot_names, number_of_games, progress_every)
        run = database.create_simulation_run(
            game_id=game_id,
            variant_name=variant_name,
            bot_lineup=bot_names,
            number_of_games=number_of_games,
            seed=seed,
        )
        future = self._executor.submit(
            _run_black_ledger_worker,
            run_id=run.id,
            variant_name=variant_name,
            bot_names=bot_names,
            number_of_games=number_of_games,
            seed=seed,
            progress_every=progress_every,
            max_turns=max_turns,
        )
        self._active[run.id] = future
        future.add_done_callback(lambda _: self._active.pop(run.id, None))
        return run.id

    def is_active(self, run_id: int) -> bool:
        future = self._active.get(run_id)
        return bool(future and not future.done())


RUN_MANAGER = RunManager()


class CodexSafetyError(RuntimeError):
    pass


class CodexJobManager:
    def __init__(self, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="codex-job")
        self._active: dict[int, Future] = {}

    def start_job(self, game_id: int) -> int:
        game = database.get_game(game_id)
        if is_game_simulatable(game):
            raise CodexSafetyError("This game already has a simulator module.")
        safety = check_codex_safety(game)
        job = database.create_codex_job(
            game_id=game.id,
            branch_name=safety["branch_name"],
            prompt_path=safety["prompt_path"],
        )
        future = self._executor.submit(_run_codex_job_worker, job.id)
        self._active[job.id] = future
        future.add_done_callback(lambda _: self._active.pop(job.id, None))
        return job.id


CODEX_JOB_MANAGER = CodexJobManager()


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


def is_game_simulatable(game) -> bool:
    return game.id == database.BUILT_IN_BLACK_LEDGER_ID


def game_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "game"


def prompt_path_for_game(game) -> Path:
    return PROJECT_ROOT / "codex_tasks" / f"{game_slug(game.name)}_simulator_prompt.md"


def branch_name_for_game(game) -> str:
    base = f"codex/{game_slug(game.name)}-simulator"
    if not branch_exists(base):
        return base
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate = f"{base}-{timestamp}"
    suffix = 2
    while branch_exists(candidate):
        candidate = f"{base}-{timestamp}-{suffix}"
        suffix += 1
    return candidate


def generate_implementation_prompt(game) -> str:
    module_name = game_slug(game.name).replace("-", "_")
    return f"""# Tabletop Lab Simulator Implementation Task

Game name: {game.name}

Description:
{game.description or "(No description provided.)"}

Stored rules text:
```text
{game.rules_text or "(No stored rules text yet.)"}
```

Existing Tabletop Lab architecture:
- Reusable engine code lives in `src/tabletop_lab/engine`.
- Black Ledger is the reference game module in `src/tabletop_lab/games/black_ledger`.
- CLI scripts live in `scripts/`.
- Tests live under `tests/`.
- New games should live under `src/tabletop_lab/games/{module_name}` with game-owned dataclasses for cards, state, actions, variants, bots, rules, and metrics.

Required files:
- `src/tabletop_lab/games/{module_name}/__init__.py`
- `src/tabletop_lab/games/{module_name}/cards.py`
- `src/tabletop_lab/games/{module_name}/actions.py`
- `src/tabletop_lab/games/{module_name}/state.py`
- `src/tabletop_lab/games/{module_name}/rules.py`
- `src/tabletop_lab/games/{module_name}/bots.py`
- `src/tabletop_lab/games/{module_name}/variants.py`
- `src/tabletop_lab/games/{module_name}/metrics.py`
- Focused pytest tests under `tests/{module_name}/`

Instructions:
1. Audit the rules for ambiguity before coding.
2. Do not silently guess unclear rules. If implementation requires an assumption, record it clearly in comments and in a TODO/assumptions note.
3. Preserve the existing Black Ledger simulator and CLI behavior.
4. Follow the existing engine interfaces and Black Ledger module style where practical.
5. Keep hidden information explicit.
6. Keep simulations deterministic by seed.
7. Add tests for setup, legal actions, action resolution, scoring, end conditions, and seed replay.
8. Run `pytest` after implementation and fix failures related to your changes.
9. Report assumptions, TODOs, changed files, and test results.

Do not merge branches or commit automatically. The user will review generated files before committing.
"""


def check_codex_safety(game) -> dict[str, str]:
    if is_game_simulatable(game):
        raise CodexSafetyError("This game already has a simulator module.")
    git_status = run_command(["git", "status", "--porcelain"]).stdout
    if git_status.strip():
        raise CodexSafetyError("Git working tree must be clean before starting a Codex simulator job.")
    if shutil.which("codex") is None:
        raise CodexSafetyError("Codex CLI was not found on PATH. Install and authenticate Codex CLI first.")
    branch_name = branch_name_for_game(game)
    return {
        "branch_name": branch_name,
        "prompt_path": str(prompt_path_for_game(game)),
    }


def branch_exists(branch_name: str) -> bool:
    result = run_command(["git", "rev-parse", "--verify", branch_name], check=False)
    return result.returncode == 0


def start_codex_job(game_id: int) -> int:
    return CODEX_JOB_MANAGER.start_job(game_id)


def codex_job_status(job_id: int) -> dict[str, Any]:
    job = database.get_codex_job(job_id)
    return {
        "id": job.id,
        "game_id": job.game_id,
        "status": job.status,
        "branch_name": job.branch_name,
        "prompt_path": job.prompt_path,
        "log_text": job.log_text,
        "test_output": job.test_output,
        "git_status_output": job.git_status_output,
        "changed_files": job.changed_files_json,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "detail_url": f"/codex-jobs/{job.id}",
    }


def run_command(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


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
    return RUN_MANAGER.start_black_ledger_run(
        game_id=game_id,
        variant_name=variant_name,
        bot_names=bot_names,
        number_of_games=number_of_games,
        seed=seed,
        progress_every=progress_every,
        max_turns=max_turns,
    )


def _validate_black_ledger_run(
    game_id: int,
    variant_name: str,
    bot_names: list[str],
    number_of_games: int,
    progress_every: int,
) -> None:
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


def run_status(run_id: int) -> dict[str, Any]:
    run = database.get_run(run_id)
    elapsed = _elapsed_for_run(run)
    completed = run.progress_completed
    total = run.progress_total
    games_per_second = completed / elapsed if elapsed > 0 else 0.0
    remaining = total - completed
    eta = remaining / games_per_second if games_per_second > 0 and run.status in {"queued", "running"} else 0.0
    percent = (completed / total * 100) if total else 0.0
    return {
        "id": run.id,
        "status": run.status,
        "progress_completed": completed,
        "progress_total": total,
        "completed": completed,
        "total": total,
        "percent": percent,
        "elapsed_seconds": elapsed,
        "eta_seconds": eta,
        "games_per_second": games_per_second,
        "error_message": run.error_message,
        "detail_url": f"/runs/{run.id}",
    }


def _elapsed_for_run(run) -> float:
    if run.status in {"complete", "failed"}:
        return run.elapsed_seconds or 0.0
    if run.started_at:
        started = datetime.fromisoformat(run.started_at)
        return max(time.time() - started.timestamp(), run.elapsed_seconds or 0.0)
    return run.elapsed_seconds or 0.0


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


def _run_codex_job_worker(job_id: int) -> None:
    try:
        job = database.get_codex_job(job_id)
        game = database.get_game(job.game_id)
        database.mark_codex_job_running(job_id)
        _log_codex(job_id, f"Starting Codex simulator job for {game.name}\n")
        _log_codex(job_id, f"Creating branch {job.branch_name}\n")
        branch_result = run_command(["git", "checkout", "-b", job.branch_name])
        _log_command(job_id, "git checkout", branch_result)
        if branch_result.returncode != 0:
            _fail_codex_with_current_state(job_id, "Failed to create git branch.")
            return

        prompt = generate_implementation_prompt(game)
        prompt_path = Path(job.prompt_path)
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        _log_codex(job_id, f"Wrote prompt to {prompt_path}\n")

        _log_codex(job_id, "Running Codex CLI\n")
        codex_result = run_command(["codex", "exec", prompt])
        _log_command(job_id, "codex exec", codex_result)
        if codex_result.returncode != 0:
            test_output, git_status, changed_files = _collect_codex_after_state(job_id, run_pytest=False)
            database.fail_codex_job(
                job_id,
                error_message="Codex CLI failed.",
                test_output=test_output,
                git_status_output=git_status,
                changed_files=changed_files,
            )
            return

        test_output, git_status, changed_files = _collect_codex_after_state(job_id, run_pytest=True)
        if "PYTEST_EXIT_CODE=0" in test_output:
            database.complete_codex_job(
                job_id,
                test_output=test_output,
                git_status_output=git_status,
                changed_files=changed_files,
            )
        else:
            database.fail_codex_job(
                job_id,
                error_message="pytest failed after Codex completed.",
                test_output=test_output,
                git_status_output=git_status,
                changed_files=changed_files,
            )
    except Exception as exc:  # noqa: BLE001 - background job must persist the failure.
        _fail_codex_with_current_state(job_id, str(exc))


def _collect_codex_after_state(job_id: int, *, run_pytest: bool) -> tuple[str, str, list[str]]:
    test_output = ""
    if run_pytest:
        _log_codex(job_id, "Running pytest\n")
        pytest_result = run_command(["pytest"])
        test_output = _format_command_output(pytest_result) + f"\nPYTEST_EXIT_CODE={pytest_result.returncode}\n"
        database.append_codex_job_log(job_id, test_output)
    git_status_result = run_command(["git", "status", "--short"], check=False)
    diff_result = run_command(["git", "diff", "--name-only", "HEAD"], check=False)
    git_status = _format_command_output(git_status_result)
    changed_files = _changed_files_from_git_outputs(diff_result.stdout, git_status_result.stdout)
    return test_output, git_status, changed_files


def _fail_codex_with_current_state(job_id: int, message: str) -> None:
    test_output, git_status, changed_files = _collect_codex_after_state(job_id, run_pytest=False)
    database.fail_codex_job(
        job_id,
        error_message=message,
        test_output=test_output,
        git_status_output=git_status,
        changed_files=changed_files,
    )


def _log_codex(job_id: int, text: str) -> None:
    database.append_codex_job_log(job_id, text)


def _log_command(job_id: int, label: str, result: subprocess.CompletedProcess) -> None:
    database.append_codex_job_log(
        job_id,
        f"\n$ {label}\n{_format_command_output(result)}\n",
    )


def _format_command_output(result: subprocess.CompletedProcess) -> str:
    parts = []
    if result.stdout:
        parts.append(result.stdout)
    if result.stderr:
        parts.append(result.stderr)
    parts.append(f"EXIT_CODE={result.returncode}")
    return "\n".join(parts)


def _changed_files_from_git_outputs(diff_output: str, status_output: str) -> list[str]:
    files = []
    for line in diff_output.splitlines():
        if line.strip():
            files.append(line.strip())
    for line in status_output.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(set(files))
