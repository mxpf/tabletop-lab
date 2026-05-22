from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import database, services


WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
templates.env.filters["json_pretty"] = lambda value: json.dumps(value, indent=2, sort_keys=True)


def create_app() -> FastAPI:
    database.initialize_database()
    app = FastAPI(title="Tabletop Lab")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "games": database.list_games(),
                "title": "Tabletop Lab",
            },
        )

    @app.get("/help", response_class=HTMLResponse)
    def help_page(request: Request):
        return templates.TemplateResponse("help.html", {"request": request, "title": "Help"})

    @app.get("/games/new", response_class=HTMLResponse)
    def new_game(request: Request):
        return templates.TemplateResponse("new_game.html", {"request": request, "title": "New Game"})

    @app.post("/games")
    def create_game(
        name: Annotated[str, Form()],
        description: Annotated[str, Form()] = "",
        rules_text: Annotated[str, Form()] = "",
        notes: Annotated[str, Form()] = "",
    ):
        game = database.create_game(
            name=name.strip(),
            description=description.strip(),
            rules_text=rules_text.strip(),
            notes=notes.strip(),
            source_type="manual",
        )
        return RedirectResponse(f"/games/{game.id}", status_code=303)

    @app.get("/games/{game_id}", response_class=HTMLResponse)
    def game_detail(request: Request, game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        runs = database.list_runs_for_game(game_id)
        return templates.TemplateResponse(
            "game_detail.html",
            {
                "request": request,
                "title": game.name,
                "game": game,
                "runs": runs,
                "is_black_ledger": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
                "variants": services.available_black_ledger_variants(),
                "bots": services.available_bots(),
            },
        )

    @app.get("/games/{game_id}/upload-rules", response_class=HTMLResponse)
    def upload_rules(request: Request, game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        return templates.TemplateResponse(
            "upload_rules.html",
            {"request": request, "title": "Upload Rules", "game": game, "preview": None},
        )

    @app.post("/games/{game_id}/rules")
    def save_pasted_rules(
        game_id: int,
        rules_text: Annotated[str, Form()],
    ):
        database.update_game_rules(game_id, rules_text=rules_text.strip(), source_type="manual")
        return RedirectResponse(f"/games/{game_id}", status_code=303)

    @app.post("/games/{game_id}/upload-rules", response_class=HTMLResponse)
    async def upload_rules_pdf(request: Request, game_id: int, pdf_file: UploadFile = File(...)):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        if not pdf_file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="please upload a PDF file")
        text, path = services.extract_pdf_text(pdf_file.file, pdf_file.filename)
        database.update_game_rules(game_id, rules_text=text, source_type="pdf", source_path=path)
        updated = database.get_game(game_id)
        return templates.TemplateResponse(
            "upload_rules.html",
            {
                "request": request,
                "title": "Upload Rules",
                "game": updated,
                "preview": text[:4000],
            },
        )

    @app.post("/runs/start")
    def start_run(
        game_id: Annotated[int, Form()],
        variant_name: Annotated[str, Form()],
        player0_bot: Annotated[str, Form()],
        player1_bot: Annotated[str, Form()],
        player2_bot: Annotated[str, Form()],
        number_of_games: Annotated[int, Form()],
        seed: Annotated[str, Form()] = "",
        progress_every: Annotated[int, Form()] = 25,
    ):
        try:
            run_id = services.start_black_ledger_run(
                game_id=game_id,
                variant_name=variant_name,
                bot_names=[player0_bot, player1_bot, player2_bot],
                number_of_games=number_of_games,
                seed=int(seed) if seed.strip() else None,
                progress_every=progress_every,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(f"/runs/{run_id}", status_code=303)

    @app.get("/runs/{run_id}/status")
    def run_status(run_id: int):
        try:
            return JSONResponse(services.run_status(run_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(request: Request, run_id: int):
        try:
            run = database.get_run(run_id)
            game = database.get_game(run.game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        return templates.TemplateResponse(
            "run_detail.html",
            {"request": request, "title": f"Run {run.id}", "run": run, "game": game},
        )

    @app.get("/games/{game_id}/compare", response_class=HTMLResponse)
    def compare_runs(request: Request, game_id: int, run_id: Optional[List[int]] = Query(default=None)):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        completed = [
            run
            for run in database.list_runs_for_game(game_id)
            if run.status == "complete"
        ]
        selected = database.list_runs(run_id or []) if run_id else []
        rows = services.comparison_rows(selected)
        return templates.TemplateResponse(
            "compare_runs.html",
            {
                "request": request,
                "title": "Compare Runs",
                "game": game,
                "completed_runs": completed,
                "selected_ids": set(run_id or []),
                "rows": rows,
            },
        )

    return app


app = create_app()
