from __future__ import annotations

import importlib
import time

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("TABLETOP_LAB_DB", str(tmp_path / "tabletop_lab.sqlite"))
    import tabletop_lab.web.app as web_app

    web_app = importlib.reload(web_app)
    return TestClient(web_app.create_app())


def test_homepage_and_black_ledger_detail_render(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    home = client.get("/")
    assert home.status_code == 200
    assert "Create or select a game" in home.text
    assert "Black Ledger" in home.text

    detail = client.get("/games/1")
    assert detail.status_code == 200
    assert "Run Simulation" in detail.text
    assert "five_numerals_starting_ledger_3" in detail.text


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
    run_id = int(response.headers["location"].split("/")[-1])
    status = {}
    for _ in range(50):
        status = client.get(f"/runs/{run_id}/status").json()
        if status["status"] == "complete":
            break
        time.sleep(0.05)

    assert status["status"] == "complete"
    assert status["completed"] == 2
    detail = client.get(f"/runs/{run_id}")
    assert "Average Turns" in detail.text
