from __future__ import annotations

from tabletop_lab.web import database


def test_database_initialization_preloads_black_ledger(tmp_path):
    db_path = tmp_path / "tabletop_lab.sqlite"

    database.initialize_database(db_path)

    games = database.list_games(db_path)
    assert [game.name for game in games] == ["Black Ledger"]
    assert games[0].source_type == "built_in"


def test_create_game_and_store_pasted_rules(tmp_path):
    db_path = tmp_path / "tabletop_lab.sqlite"
    database.initialize_database(db_path)

    game = database.create_game(
        name="Tiny Duel",
        description="A tiny test game.",
        rules_text="Draw one card. Highest card wins.",
        source_type="manual",
        db_path=db_path,
    )

    fetched = database.get_game(game.id, db_path=db_path)
    assert fetched.name == "Tiny Duel"
    assert "Highest card wins" in fetched.rules_text
    assert fetched.source_type == "manual"


def test_simulation_run_lifecycle(tmp_path):
    db_path = tmp_path / "tabletop_lab.sqlite"
    database.initialize_database(db_path)

    run = database.create_simulation_run(
        game_id=database.BUILT_IN_BLACK_LEDGER_ID,
        variant_name="base_3p",
        bot_lineup=["random", "builder", "greedy"],
        number_of_games=10,
        seed=5,
        db_path=db_path,
    )
    assert run.status == "queued"

    database.mark_run_running(run.id, db_path=db_path)
    database.update_run_progress(run.id, 4, 10, 0.5, db_path=db_path)
    running = database.get_run(run.id, db_path=db_path)
    assert running.status == "running"
    assert running.progress_completed == 4

    database.complete_run(
        run.id,
        summary={"games": 10, "average_turns": 12.5},
        elapsed_seconds=1.25,
        db_path=db_path,
    )
    complete = database.get_run(run.id, db_path=db_path)
    assert complete.status == "complete"
    assert complete.progress_completed == 10
    assert complete.summary_json["average_turns"] == 12.5


def test_failed_run_records_error_message(tmp_path):
    db_path = tmp_path / "tabletop_lab.sqlite"
    database.initialize_database(db_path)
    run = database.create_simulation_run(
        game_id=database.BUILT_IN_BLACK_LEDGER_ID,
        variant_name="base_3p",
        bot_lineup=["random", "builder", "greedy"],
        number_of_games=1,
        seed=None,
        db_path=db_path,
    )

    database.fail_run(run.id, error_message="boom", elapsed_seconds=0.1, db_path=db_path)

    failed = database.get_run(run.id, db_path=db_path)
    assert failed.status == "failed"
    assert failed.error_message == "boom"

