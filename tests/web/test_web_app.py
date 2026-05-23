from __future__ import annotations

import importlib
import subprocess
import time
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from tabletop_lab.web import database


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("TABLETOP_LAB_DB", str(tmp_path / "tabletop_lab.sqlite"))
    import tabletop_lab.web.app as web_app

    web_app = importlib.reload(web_app)
    return TestClient(web_app.create_app())


def test_homepage_and_black_ledger_detail_render(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    home = client.get("/")
    assert home.status_code == 200
    assert "Create or select a game" not in home.text
    assert "Watch progress" not in home.text
    assert 'href="/games/new"' in home.text
    assert 'href="/games/1#run-simulation"' in home.text
    assert 'href="/games/1#run-history"' in home.text
    assert 'href="/games/1/compare#compare-runs"' in home.text
    assert "Black Ledger" in home.text

    detail = client.get("/games/1")
    assert detail.status_code == 200
    assert "Use this panel to run automated playtests for Black Ledger" in detail.text
    assert "Rules configuration to test." in detail.text
    assert "Bot strategy assigned to this seat." in detail.text
    assert "Number of simulated games to run." in detail.text
    assert "Optional. Use the same seed to reproduce a run." in detail.text
    assert "How often the progress display updates." in detail.text
    assert "Completed simulations are saved here" in detail.text
    assert "No runs yet. Start a simulation above to create the first saved test." in detail.text
    assert "Edit Rules" in detail.text
    assert "Paste or Upload Rules" not in detail.text
    assert "Run Simulation" in detail.text
    assert "five_numerals_starting_ledger_3" in detail.text


def test_new_game_page_has_pdf_upload(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    response = client.get("/games/new")

    assert response.status_code == 200
    assert "Add Rules" in response.text
    assert "Paste rules text" in response.text
    assert "Upload rules PDF" in response.text
    assert 'type="file"' in response.text
    assert 'name="pdf_file"' in response.text
    assert "We'll extract text from the PDF" in response.text


def test_edit_rules_page_clarifies_existing_game_update(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    response = client.get("/games/1/upload-rules")

    assert response.status_code == 200
    assert "Edit Rules for Black Ledger" in response.text
    assert "Saving here replaces the rules text shown on the Black Ledger page" in response.text
    assert "Paste Revised Rules" in response.text
    assert "this text will replace the current stored rules for this game" in response.text
    assert "Upload Rules PDF" in response.text
    assert "Extracting text will place the extracted text into the rules text area before saving" in response.text
    assert "Note: Black Ledger has a coded simulation module" in response.text
    assert "It does not automatically change the simulator behavior" in response.text
    assert 'href="/games/new"' in response.text
    assert "Create a new game instead" in response.text


def test_create_game_from_browser(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    response = client.post(
        "/games",
        data={
            "name": "Fog Market",
            "description": "Auction test.",
            "rules_text": "Bid, reveal, score.",
            "notes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Fog Market" in response.text
    assert "Bid, reveal, score." in response.text


def test_non_simulatable_game_shows_codex_workflow(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    response = client.post(
        "/games",
        data={
            "name": "Undersight",
            "description": "Hidden-map deduction.",
            "rules_text": "Explore, infer, score.",
            "notes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Make this game simulatable" in response.text
    assert "Generate Codex Prompt" in response.text
    assert "Create Simulator Branch with Codex" in response.text
    assert "Experimental local developer tool" in response.text


def test_black_ledger_does_not_show_codex_create_button(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    response = client.get("/games/1")

    assert response.status_code == 200
    assert "Create Simulator Branch with Codex" not in response.text


def test_implementation_prompt_page(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    game = database.create_game(
        name="Undersight",
        description="Hidden-map deduction.",
        rules_text="Explore, infer, score.",
        source_type="manual",
        db_path=tmp_path / "tabletop_lab.sqlite",
    )

    response = client.get(f"/games/{game.id}/implementation-prompt")

    assert response.status_code == 200
    assert "Codex Prompt for Undersight" in response.text
    assert "Instruction" in response.text or "Instructions" in response.text
    assert "Do not silently guess unclear rules" in response.text
    assert "Explore, infer, score." in response.text


def test_create_game_from_pdf_upload(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    def fake_extract(file_obj, filename):
        assert filename == "rules.pdf"
        return "Extracted PDF rules text.", str(tmp_path / "rules.pdf")

    monkeypatch.setattr(web_app.services, "extract_pdf_text", fake_extract)

    response = client.post(
        "/games",
        data={
            "name": "PDF Game",
            "description": "From uploaded rules.",
            "rules_text": "",
            "notes": "",
        },
        files={"pdf_file": ("rules.pdf", b"fake pdf bytes", "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "PDF Game" in response.text
    assert "Extracted PDF rules text." in response.text


def test_create_game_from_failed_pdf_extraction_shows_error(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    def fake_extract(file_obj, filename):
        raise ValueError("encrypted PDF")

    monkeypatch.setattr(web_app.services, "extract_pdf_text", fake_extract)

    response = client.post(
        "/games",
        data={
            "name": "Broken PDF",
            "description": "",
            "rules_text": "",
            "notes": "",
        },
        files={"pdf_file": ("rules.pdf", b"fake pdf bytes", "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 400
    assert "Could not extract text from that PDF" in response.text
    assert "encrypted PDF" in response.text
    assert "Broken PDF" not in client.get("/").text


def test_edit_rules_pdf_extraction_previews_before_saving(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    original_rules = database.get_game(1, tmp_path / "tabletop_lab.sqlite").rules_text

    def fake_extract(file_obj, filename):
        return "Extracted replacement rules.", str(tmp_path / "rules.pdf")

    monkeypatch.setattr(web_app.services, "extract_pdf_text", fake_extract)

    response = client.post(
        "/games/1/upload-rules",
        files={"pdf_file": ("rules.pdf", b"fake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 200
    assert "Extracted PDF text has been placed in the rules text area for review" in response.text
    assert "Extracted replacement rules." in response.text
    assert database.get_game(1, tmp_path / "tabletop_lab.sqlite").rules_text == original_rules

    saved = client.post(
        "/games/1/rules",
        data={
            "rules_text": "Extracted replacement rules.",
            "source_type": "pdf",
            "source_path": str(tmp_path / "rules.pdf"),
        },
        follow_redirects=True,
    )

    assert saved.status_code == 200
    assert "Extracted replacement rules." in saved.text


def test_start_small_black_ledger_run_and_poll(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    response = client.post(
        "/runs/start",
        data={
            "game_id": "1",
            "variant_name": "base_3p",
            "player0_bot": "random",
            "player1_bot": "builder",
            "player2_bot": "greedy",
            "number_of_games": "2",
            "seed": "7",
            "progress_every": "1",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/games/1?active_run_id=")
    run_id = int(parse_qs(urlparse(location).query)["active_run_id"][0])
    status = {}
    for _ in range(50):
        status = client.get(f"/runs/{run_id}/status").json()
        if status["status"] == "complete":
            break
        time.sleep(0.05)

    assert status["status"] == "complete"
    assert status["completed"] == 2
    game_page = client.get(f"/games/1?active_run_id={run_id}")
    assert "Current Run" in game_page.text
    assert "Open run detail" in game_page.text
    assert 'class="status-badge complete"' in game_page.text
    assert "Average Turns" in client.get(f"/runs/{run_id}").text


def test_run_detail_status_badge_is_passive(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    db_path = tmp_path / "tabletop_lab.sqlite"
    run = database.create_simulation_run(
        game_id=1,
        variant_name="base_3p",
        bot_lineup=["random", "builder", "greedy"],
        number_of_games=1,
        seed=1,
        db_path=db_path,
    )
    database.complete_run(
        run.id,
        summary={"games": 1, "average_turns": 1, "end_condition_rates": {}, "average_closed_accounts_total": 0},
        elapsed_seconds=0.1,
        db_path=db_path,
    )

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert 'class="status-badge complete"' in response.text
    assert ">complete</span>" in response.text
    assert '<a class="status-badge' not in response.text
    assert '<button class="status-badge' not in response.text
    assert "Back to Black Ledger" in response.text


def test_start_run_json_returns_quickly_and_creates_one_run(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    start = time.perf_counter()
    response = client.post(
        "/runs/start",
        data={
            "game_id": "1",
            "variant_name": "base_3p",
            "player0_bot": "random",
            "player1_bot": "builder",
            "player2_bot": "greedy",
            "number_of_games": "20",
            "seed": "9",
            "progress_every": "5",
        },
        headers={"Accept": "application/json"},
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 202
    assert elapsed < 0.5
    payload = response.json()
    assert payload["run_id"]
    assert payload["status_url"] == f"/runs/{payload['run_id']}/status"
    runs = database.list_runs_for_game(1, tmp_path / "tabletop_lab.sqlite")
    assert len(runs) == 1


def test_status_endpoint_reports_progress_fields(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    response = client.post(
        "/runs/start",
        data={
            "game_id": "1",
            "variant_name": "base_3p",
            "player0_bot": "random",
            "player1_bot": "builder",
            "player2_bot": "greedy",
            "number_of_games": "3",
            "seed": "10",
            "progress_every": "1",
        },
        headers={"Accept": "application/json"},
    )
    run_id = response.json()["run_id"]

    status = {}
    for _ in range(50):
        status = client.get(f"/runs/{run_id}/status").json()
        if status["status"] == "complete":
            break
        time.sleep(0.05)

    assert status["status"] == "complete"
    assert status["progress_completed"] == 3
    assert status["progress_total"] == 3
    assert status["percent"] == 100
    assert status["elapsed_seconds"] >= 0
    assert status["games_per_second"] >= 0
    assert status["eta_seconds"] == 0
    assert status["detail_url"] == f"/runs/{run_id}"


def test_failed_background_run_stores_error(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    run_id = web_app.services.start_black_ledger_run(
        game_id=1,
        variant_name="base_3p",
        bot_names=["random", "builder", "greedy"],
        number_of_games=1,
        seed=1,
        progress_every=1,
        max_turns=0,
    )

    status = {}
    for _ in range(50):
        status = client.get(f"/runs/{run_id}/status").json()
        if status["status"] == "failed":
            break
        time.sleep(0.05)

    assert status["status"] == "failed"
    assert "exceeded max_turns=0" in status["error_message"]


def completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def test_codex_job_refuses_dirty_git(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    game = database.create_game(
        name="Undersight",
        rules_text="Rules.",
        source_type="manual",
        db_path=tmp_path / "tabletop_lab.sqlite",
    )

    monkeypatch.setattr(web_app.services.shutil, "which", lambda name: "/usr/local/bin/codex")

    def fake_run_command(args, check=False):
        if args == ["git", "status", "--porcelain"]:
            return completed(args, stdout=" M README.md\n")
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return completed(args, returncode=1)
        return completed(args)

    monkeypatch.setattr(web_app.services, "run_command", fake_run_command)

    response = client.post(f"/games/{game.id}/codex-jobs")

    assert response.status_code == 400
    assert "Git working tree must be clean" in response.text


def test_codex_job_refuses_missing_codex(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    game = database.create_game(
        name="Undersight",
        rules_text="Rules.",
        source_type="manual",
        db_path=tmp_path / "tabletop_lab.sqlite",
    )

    monkeypatch.setattr(web_app.services.shutil, "which", lambda name: None)

    def fake_run_command(args, check=False):
        if args == ["git", "status", "--porcelain"]:
            return completed(args, stdout="")
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return completed(args, returncode=1)
        return completed(args)

    monkeypatch.setattr(web_app.services, "run_command", fake_run_command)

    response = client.post(f"/games/{game.id}/codex-jobs")

    assert response.status_code == 400
    assert "Codex CLI was not found" in response.text


def test_codex_job_runs_with_mocks_and_persists_outputs(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    import tabletop_lab.web.app as web_app

    game = database.create_game(
        name="Undersight",
        description="Hidden-map deduction.",
        rules_text="Explore, infer, score.",
        source_type="manual",
        db_path=tmp_path / "tabletop_lab.sqlite",
    )
    calls = []
    monkeypatch.setattr(web_app.services, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(web_app.services.shutil, "which", lambda name: "/usr/local/bin/codex")

    def fake_run_command(args, check=False):
        calls.append(args)
        if args == ["git", "status", "--porcelain"]:
            return completed(args, stdout="")
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return completed(args, returncode=1)
        if args[:3] == ["git", "checkout", "-b"]:
            return completed(args, stdout="Switched to a new branch\n")
        if args[:2] == ["codex", "exec"]:
            return completed(args, stdout="Codex generated simulator files.\n")
        if args == ["pytest"]:
            return completed(args, stdout="63 passed\n")
        if args == ["git", "status", "--short"]:
            return completed(args, stdout="?? src/tabletop_lab/games/undersight/rules.py\n")
        if args == ["git", "diff", "--name-only", "HEAD"]:
            return completed(args, stdout="src/tabletop_lab/games/undersight/rules.py\n")
        return completed(args)

    monkeypatch.setattr(web_app.services, "run_command", fake_run_command)

    response = client.post(f"/games/{game.id}/codex-jobs", follow_redirects=False)

    assert response.status_code == 303
    job_id = int(response.headers["location"].split("/")[-1])
    status = {}
    for _ in range(50):
        status = client.get(f"/codex-jobs/{job_id}/status").json()
        if status["status"] == "complete":
            break
        time.sleep(0.05)

    assert status["status"] == "complete"
    assert status["branch_name"] == "codex/undersight-simulator"
    assert status["prompt_path"].endswith("codex_tasks/undersight_simulator_prompt.md")
    assert "Codex generated simulator files." in status["log_text"]
    assert "63 passed" in status["test_output"]
    assert "src/tabletop_lab/games/undersight/rules.py" in status["changed_files"]
    assert (tmp_path / "codex_tasks" / "undersight_simulator_prompt.md").exists()
    assert ["git", "checkout", "-b", "codex/undersight-simulator"] in calls
    assert any(call[:2] == ["codex", "exec"] for call in calls)

    detail = client.get(f"/codex-jobs/{job_id}")
    assert "Review the generated files in your editor" in detail.text
    assert "Codex generated simulator files." in detail.text
