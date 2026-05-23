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
    def index(request: Request, show_archived: bool = Query(default=False)):
        black_ledger_id = database.BUILT_IN_BLACK_LEDGER_ID
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "games": database.list_games(include_archived=show_archived),
                "title": "Tabletop Lab",
                "black_ledger_id": black_ledger_id,
                "show_archived": show_archived,
            },
        )

    @app.get("/help", response_class=HTMLResponse)
    def help_page(request: Request):
        return templates.TemplateResponse("help.html", {"request": request, "title": "Help"})

    @app.get("/games/new", response_class=HTMLResponse)
    def new_game(request: Request):
        return templates.TemplateResponse(
            "new_game.html",
            {"request": request, "title": "New Game", "error": None},
        )

    @app.post("/games")
    async def create_game(
        request: Request,
        name: Annotated[str, Form()],
        description: Annotated[str, Form()] = "",
        rules_text: Annotated[str, Form()] = "",
        notes: Annotated[str, Form()] = "",
        confirm_duplicate: Annotated[str, Form()] = "",
        pdf_file: Optional[UploadFile] = File(default=None),
    ):
        duplicate_matches = database.find_games_by_name(name)
        if duplicate_matches and not confirm_duplicate:
            return templates.TemplateResponse(
                "new_game.html",
                {
                    "request": request,
                    "title": "New Game",
                    "error": None,
                    "duplicate_matches": duplicate_matches,
                    "form_values": {
                        "name": name,
                        "description": description,
                        "rules_text": rules_text,
                        "notes": notes,
                    },
                },
                status_code=200,
            )
        source_type = "manual"
        source_path = None
        final_rules_text = rules_text.strip()
        if not final_rules_text and pdf_file and pdf_file.filename:
            if not pdf_file.filename.lower().endswith(".pdf"):
                return templates.TemplateResponse(
                    "new_game.html",
                    {
                        "request": request,
                        "title": "New Game",
                        "error": "Please upload a PDF file.",
                    },
                    status_code=400,
                )
            try:
                final_rules_text, source_path = services.extract_pdf_text(pdf_file.file, pdf_file.filename)
            except Exception as exc:  # noqa: BLE001 - show extraction failure clearly in the UI.
                return templates.TemplateResponse(
                    "new_game.html",
                    {
                        "request": request,
                        "title": "New Game",
                        "error": f"Could not extract text from that PDF: {exc}",
                    },
                    status_code=400,
                )
            if not final_rules_text:
                return templates.TemplateResponse(
                    "new_game.html",
                    {
                        "request": request,
                        "title": "New Game",
                        "error": "The PDF did not contain extractable text.",
                    },
                    status_code=400,
                )
            source_type = "pdf"
        game = database.create_game(
            name=name.strip(),
            description=description.strip(),
            rules_text=final_rules_text,
            notes=notes.strip(),
            source_type=source_type,
            source_path=source_path,
        )
        return RedirectResponse(f"/games/{game.id}", status_code=303)

    @app.get("/games/{game_id}/edit", response_class=HTMLResponse)
    def edit_game_details(request: Request, game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        return templates.TemplateResponse(
            "edit_game.html",
            {
                "request": request,
                "title": f"Edit {game.name}",
                "game": game,
                "is_built_in": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
            },
        )

    @app.post("/games/{game_id}/details")
    def update_game_details(
        game_id: int,
        name: Annotated[str, Form()],
        description: Annotated[str, Form()] = "",
        notes: Annotated[str, Form()] = "",
        source_type: Annotated[str, Form()] = "manual",
    ):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        allowed_sources = {"manual", "pdf", "built_in"}
        if source_type not in allowed_sources:
            raise HTTPException(status_code=400, detail="invalid source type")
        if game.id == database.BUILT_IN_BLACK_LEDGER_ID:
            source_type = "built_in"
        database.update_game_details(
            game_id,
            name=name.strip(),
            description=description.strip(),
            notes=notes.strip(),
            source_type=source_type,
        )
        return RedirectResponse(f"/games/{game_id}", status_code=303)

    @app.post("/games/{game_id}/archive")
    def archive_game(game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        if game.id == database.BUILT_IN_BLACK_LEDGER_ID:
            raise HTTPException(status_code=400, detail="built-in games cannot be archived")
        database.archive_game(game_id)
        return RedirectResponse("/", status_code=303)

    @app.post("/games/{game_id}/unarchive")
    def unarchive_game(game_id: int):
        try:
            database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        database.unarchive_game(game_id)
        return RedirectResponse(f"/games/{game_id}", status_code=303)

    @app.post("/games/{game_id}/delete")
    def delete_game(
        game_id: int,
        confirm_name: Annotated[str, Form()] = "",
    ):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        if game.id == database.BUILT_IN_BLACK_LEDGER_ID:
            raise HTTPException(status_code=400, detail="built-in games cannot be deleted")
        if confirm_name != game.name:
            raise HTTPException(status_code=400, detail="type the game name to confirm deletion")
        database.delete_game(game_id)
        return RedirectResponse("/", status_code=303)

    @app.get("/games/{game_id}", response_class=HTMLResponse)
    def game_detail(request: Request, game_id: int, active_run_id: Optional[int] = Query(default=None)):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        runs = database.list_runs_for_game(game_id)
        active_run = None
        if active_run_id is not None:
            try:
                active_run = database.get_run(active_run_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="run not found") from exc
            if active_run.game_id != game_id:
                raise HTTPException(status_code=404, detail="run not found for this game")
        return templates.TemplateResponse(
            "game_detail.html",
            {
                "request": request,
                "title": game.name,
                "game": game,
                "runs": runs,
                "active_run": active_run,
                "is_black_ledger": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
                "is_simulatable": services.is_game_simulatable(game),
                "codex_jobs": database.list_codex_jobs_for_game(game.id),
                "variants": services.available_black_ledger_variants(),
                "bots": services.available_bots(),
            },
        )

    @app.get("/games/{game_id}/implementation-prompt", response_class=HTMLResponse)
    def implementation_prompt(request: Request, game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        prompt = services.generate_implementation_prompt(game)
        return templates.TemplateResponse(
            "implementation_prompt.html",
            {
                "request": request,
                "title": f"Codex Prompt for {game.name}",
                "game": game,
                "prompt": prompt,
            },
        )

    @app.get("/games/{game_id}/codex-jobs/new", response_class=HTMLResponse)
    def new_codex_job(request: Request, game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        if services.is_game_simulatable(game):
            raise HTTPException(status_code=400, detail="this game is already simulatable")
        branch_name = services.branch_name_for_game(game)
        prompt_path = services.prompt_path_for_game(game)
        return templates.TemplateResponse(
            "codex_job_confirm.html",
            {
                "request": request,
                "title": "Create Simulator Branch with Codex",
                "game": game,
                "branch_name": branch_name,
                "prompt_path": prompt_path,
            },
        )

    @app.post("/games/{game_id}/codex-jobs")
    def start_codex_job(game_id: int):
        try:
            job_id = services.start_codex_job(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        except services.CodexSafetyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(f"/codex-jobs/{job_id}", status_code=303)

    @app.get("/codex-jobs/{job_id}", response_class=HTMLResponse)
    def codex_job_detail(request: Request, job_id: int):
        try:
            job = database.get_codex_job(job_id)
            game = database.get_game(job.game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="codex job not found") from exc
        return templates.TemplateResponse(
            "codex_job_detail.html",
            {"request": request, "title": f"Codex Job {job.id}", "job": job, "game": game},
        )

    @app.get("/codex-jobs/{job_id}/status")
    def codex_job_status(job_id: int):
        try:
            return JSONResponse(services.codex_job_status(job_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="codex job not found") from exc

    @app.get("/games/{game_id}/upload-rules", response_class=HTMLResponse)
    def upload_rules(request: Request, game_id: int):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        return templates.TemplateResponse(
            "upload_rules.html",
            {
                "request": request,
                "title": f"Edit Rules for {game.name}",
                "game": game,
                "edit_rules_text": game.rules_text,
                "is_built_in": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
                "source_type": game.source_type,
                "source_path": game.source_path or "",
                "extracted": False,
            },
        )

    @app.post("/games/{game_id}/rules")
    def save_pasted_rules(
        game_id: int,
        rules_text: Annotated[str, Form()],
        source_type: Annotated[str, Form()] = "manual",
        source_path: Annotated[str, Form()] = "",
    ):
        if source_type not in {"manual", "pdf"}:
            source_type = "manual"
        database.update_game_rules(
            game_id,
            rules_text=rules_text.strip(),
            source_type=source_type,
            source_path=source_path or None,
        )
        return RedirectResponse(f"/games/{game_id}", status_code=303)

    @app.post("/games/{game_id}/upload-rules", response_class=HTMLResponse)
    async def upload_rules_pdf(request: Request, game_id: int, pdf_file: UploadFile = File(...)):
        try:
            game = database.get_game(game_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="game not found") from exc
        if not pdf_file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="please upload a PDF file")
        try:
            text, path = services.extract_pdf_text(pdf_file.file, pdf_file.filename)
        except Exception as exc:  # noqa: BLE001 - show extraction failure clearly in the UI.
            return templates.TemplateResponse(
                "upload_rules.html",
                {
                    "request": request,
                    "title": f"Edit Rules for {game.name}",
                    "game": game,
                    "edit_rules_text": game.rules_text,
                    "is_built_in": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
                    "source_type": game.source_type,
                    "source_path": game.source_path or "",
                    "extracted": False,
                    "error": f"Could not extract text from that PDF: {exc}",
                },
                status_code=400,
            )
        if not text:
            return templates.TemplateResponse(
                "upload_rules.html",
                {
                    "request": request,
                    "title": f"Edit Rules for {game.name}",
                    "game": game,
                    "edit_rules_text": game.rules_text,
                    "is_built_in": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
                    "source_type": game.source_type,
                    "source_path": game.source_path or "",
                    "extracted": False,
                    "error": "The PDF did not contain extractable text.",
                },
                status_code=400,
            )
        return templates.TemplateResponse(
            "upload_rules.html",
            {
                "request": request,
                "title": f"Edit Rules for {game.name}",
                "game": game,
                "edit_rules_text": text,
                "is_built_in": game.id == database.BUILT_IN_BLACK_LEDGER_ID,
                "source_type": "pdf",
                "source_path": path,
                "extracted": True,
            },
        )

    @app.post("/runs/start")
    def start_run(
        request: Request,
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
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(
                {
                    "run_id": run_id,
                    "status_url": f"/runs/{run_id}/status",
                    "game_url": f"/games/{game_id}?active_run_id={run_id}#current-run",
                    "detail_url": f"/runs/{run_id}",
                },
                status_code=202,
            )
        return RedirectResponse(f"/games/{game_id}?active_run_id={run_id}#current-run", status_code=303)

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
