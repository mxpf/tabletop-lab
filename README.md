# Tabletop Lab

Tabletop Lab is a Python simulation framework and local browser app for small tabletop card and token games. It is built for game designers who want deterministic playtests, rule-variant comparisons, useful metrics, saved run history, and replayable games by seed.

The first included game is **Black Ledger**, a 3-player gambling-den card game of hidden Stakes, bluffing, denial, Heat, and closing Accounts before cards reach the Furnace.

## Install

```bash
cd tabletop-lab
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Tabletop Lab targets Python 3.11+ for normal development. The core simulator uses the standard library; the browser app uses FastAPI, Jinja2, Uvicorn, SQLite, and pypdf.

## Run the Local Web App

```bash
python3 scripts/run_web.py
```

Then open:

```text
http://127.0.0.1:8000
```

The app lets you:

- Create or select a game.
- Paste rules or upload a PDF.
- Run a Black Ledger simulation.
- Watch progress with games/sec and estimated time remaining.
- Review previous test runs saved in SQLite.
- Compare completed runs in a table.

Saved app data lives in `data/tabletop_lab.sqlite`. Uploaded PDFs are stored under `uploads/`. Both are ignored by git by default.

Pasted or uploaded rules are stored for reference. To simulate a new game, a game module still needs to be implemented in code.

## Experimental: Running Codex from the UI

For non-simulatable stored-rule games, the web app includes an experimental local developer workflow called **Create Simulator Branch with Codex**. This is intended for local development only.

Requirements:

- Codex CLI must be installed, available on `PATH`, and authenticated.
- The git working tree must be clean before starting.
- The game must not already have a simulator module.

What it does:

- Creates a branch named like `codex/<game-slug>-simulator`.
- Writes an implementation prompt to `codex_tasks/<game-slug>_simulator_prompt.md`.
- Runs `codex exec` with that prompt.
- Runs `pytest`.
- Captures logs, test output, git status, and changed files in SQLite.

This workflow can modify project files. Review all generated files in your editor before committing. The app will not commit, merge, or run arbitrary browser-provided shell commands.

If a job fails:

- Open the Codex job page and read the log, pytest output, and git status.
- Inspect the branch in your editor.
- Keep useful files and fix them manually, or switch back to your previous branch and delete the experimental branch.
- Restart the web app if a generated Python module needs to be imported by the running process.

## Run Tests

```bash
pytest
```

## Run One Black Ledger Game

```bash
python scripts/run_game.py --seed 42 --variant base_3p --bots random,builder,greedy --transcript
```

The seed fully determines the deck shuffle, first player, and bot choices.

## Run 10,000 Simulations

```bash
python scripts/run_simulation.py -n 10000 --seed 1 --variant base_3p --bots random,builder,greedy
```

Progress and safety controls:

```bash
python scripts/run_simulation.py --game black_ledger --variant base_3p --games 10000 --progress --progress-every 1000 --max-turns 200
```

Optional exports:

```bash
python scripts/run_simulation.py -n 10000 --csv results.csv --json results.json
```

On the current development machine, 1,000 `base_3p` games with the default bot lineup complete in about 1.3 seconds, roughly 840 games/sec:

```bash
time python scripts/run_simulation.py --game black_ledger --variant base_3p --games 1000 --progress --progress-every 100
```

## Compare Variants

```bash
python scripts/compare_variants.py base_3p furnace_5 furnace_7 call_success_0_to_1 -n 10000
```

The comparison table includes average score, average Closed Accounts, end condition rates, win rates, action frequencies, Call success rate, Burn frequency, Furnace outcomes, and first-player win/tie rate.

## Architecture

`src/tabletop_lab/engine` contains reusable primitives:

- `GameRules`: setup, legal actions, action application, scoring, visible-state projection.
- `Bot`: action selection from visible state and legal actions.
- `Simulator`: deterministic single-game and many-game runners.
- `Zone`, `Deck`, `Metrics`, `Transcript`, and base dataclasses.

`src/tabletop_lab/games/black_ledger` contains game-specific cards, state, actions, rules, bots, variants, and metrics helpers. Game modules are allowed to define their own concrete dataclasses so the engine stays small and readable.

## Add a New Game

1. Create `src/tabletop_lab/games/your_game/`.
2. Define card, state, action, variant, and bot dataclasses that fit your game.
3. Implement `GameRules`:
   - `setup`
   - `legal_actions`
   - `apply_action`
   - `is_game_over`
   - `should_finish_round`
   - `score`
   - `visible_state_for`
4. Keep hidden information explicit in state and hidden in `visible_state_for`.
5. Add deterministic tests for setup, legal actions, edge cases, scoring, and seed replay.
6. Add small scripts or reuse the Black Ledger scripts as templates.

Correctness matters more than abstraction. Prefer clear game-owned logic over generic machinery until a second game proves an abstraction is useful.

## Web App Architecture

`src/tabletop_lab/web` contains the local browser app:

- `app.py`: FastAPI routes and page rendering.
- `database.py`: SQLite schema and persistence helpers.
- `services.py`: Black Ledger run orchestration, PDF extraction, and comparison helpers.
- `templates/`: plain Jinja2 pages.
- `static/`: small CSS and JavaScript files.

The CLI scripts remain the fastest way to run large batches from a terminal. The web app is intended for interactive local playtest tracking and browsing prior results.
