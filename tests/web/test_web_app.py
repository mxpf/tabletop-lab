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
    assert 'href="#game-library"' in home.text
    assert 'href="/games/new"' in home.text
    assert 'href="/games/1#run-simulation"' in home.text
    assert 'href="/games/1#run-history"' in home.text
    assert 'href="/games/1/compare#compare-runs"' in home.text
    assert "Black Ledger" in home.text

    detail = client.get("/games/1")
    assert detail.status_code == 200
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
