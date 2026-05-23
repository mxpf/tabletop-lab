import json
import subprocess
import sys


def test_run_game_cli_supports_undersight():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_game.py",
            "--game",
            "undersight",
            "--variant",
            "quick_2p",
            "--bots",
            "random,random",
            "--seed",
            "123",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    metrics = json.loads(completed.stdout)
    assert metrics["variant"] == "quick_2p"
    assert sorted(metrics["final_scores"]) == ["0", "1"]


def test_run_simulation_cli_keeps_black_ledger_default():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_simulation.py",
            "--games",
            "1",
            "--seed",
            "123",
            "--max-turns",
            "100",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["games"] == 1
    assert "average_closed_accounts_total" in summary
