# Tabletop Lab Simulator Implementation Task

Game name: Undersight

Description:
Players compete to mine, refine, and exploit magical gems within a dangerous industrial bureaucracy.

Stored rules text:
```text
Objective

Players compete to mine, refine, and exploit magical gems within a dangerous industrial bureaucracy. Score the most VP before the mine shuts down.

Components

You need:

34 d8 dice
Installation cards
Directive cards
Starter Zone cards
Spillover tokens
Gem, Influence, Anomaly, VP, and Waiver markers
Optional Department cards

Setup

Place Base Camp at the top center of the shared tableau.

Shuffle the Starter Zone deck and place 3–5 Starter Zones around Base Camp, depending on player count.

Each player chooses a Department.

Each player begins with a personal deck/hand of Installation and Directive cards.

Place all 34 d8s in the shared Idle Dice Pool.

Tableau and Depth

The mine is a shared card tableau organized by depth.

Row 0: Base Camp
Row 1: Shallow Depth
Row 2: Mid Depth
Row 3: Deep
Row 4+: Forbidden Depths

There is no fixed lateral limit. Players may expand left or right as the mine grows.

Depth affects danger and reward. Deeper locations tend to produce better effects but cause faster escalation.

Forbidden Depths require Excavation Waivers to access.

Binding Dice

On your turn, you allocate one die from the Idle Pool to a valid Zone or Installation.

Dice begin at value 1 unless a card says otherwise.

Each card has player-specific binding slots. The slot where a die is placed determines who controls that die.

You control the dice you allocate, even if they are on another player’s Installation.

Turn Structure

On your turn:
	1.	Play Phase
Play one Installation to the tableau or one Directive for an instant effect.
	2.	Allocation Phase
Allocate one Idle die to a valid card.
	3.	Discharge Phase
You may discharge any number of your dice from cards where they are bound.
	4.	Minor Action Phase
You may take one minor action, such as stabilizing or diverting a die, if allowed by the rules or card effects.
	5.	Wrap-Up Phase
Resolve triggered effects from cards.

Escalation

At the end of each round, after every player has taken a turn, all bound dice escalate.

Normally, each die increases by +1.

Cards, depth, and Spillovers may cause dice to escalate faster.

Dice showing 7 or 8 are Volatile.

If a die would go above 8, it causes a Severance.

Severance

When a die Severs:

Remove it from the card and return it to the Idle Dice Pool.
The die’s owner loses 1 VP.
Resolve any Severance or Spillover effects on the card.
Increase the group Severance count by 1.

Discharge

To discharge a die, remove one of your bound dice from a card and return it to the Idle Pool.

You gain the card’s discharge reward.

Discharging usually creates a Spillover.

Some cards reward the player using the card, while also giving a bonus to the Installation’s owner.

Owner-triggered passive bonuses may only be claimed once per round per Installation.

Spillovers

Spillovers are lingering side effects created by discharges.

They may affect adjacent cards, increase escalation, restrict allocation, or create special conditions.

Spillover effects normally apply only to orthogonally adjacent cards unless a card says otherwise.

Some “next time” effects are tracked by tilting the affected card until resolved.

Resources

Gems are the main extraction resource.
Influence is bureaucratic currency used by cards and some actions.
Anomaly Tokens represent dangerous rare findings.
Excavation Waivers allow access to Forbidden Depths.

Most special uses of Influence are printed directly on cards, though some basic actions may have standard costs.

Departments

Each player has a Department with a small asymmetry: usually one passive ability and one once-per-game active ability.

Current Departments include:

Zoning & Permits Division — controls placement, reserves zones, and can temporarily shut down a zone.

Division of Extraction & Asset Recovery — gains extra VP from value-8 discharges and can burst-discharge Volatile dice.

Hazard & Oversight Liaison Office — profits from Spillovers and can move Spillover tokens.

Department of Anomalous Resource Studies — stores more Anomaly Tokens and can convert them into VP.

Office of Influence & Expedience — reduces Influence costs and can take an extra turn.

Game End

The game ends at the end of the round when any one of these happens:

A player reaches 20 VP.
The group triggers 7 Severances.
The Idle Dice Pool has fewer than 4 dice remaining.

Final Scoring

At game end, score remaining resources:

2 Gems = 1 VP
2 Anomaly Tokens = 1 VP
4 Influence = 1 VP

Most VP wins.

Ties are broken by:
	1.	Most remaining Influence
	2.	Most active dice on the board
	3.	Most Installations placed
```

Existing Tabletop Lab architecture:
- Reusable engine code lives in `src/tabletop_lab/engine`.
- Black Ledger is the reference game module in `src/tabletop_lab/games/black_ledger`.
- CLI scripts live in `scripts/`.
- Tests live under `tests/`.
- New games should live under `src/tabletop_lab/games/undersight` with game-owned dataclasses for cards, state, actions, variants, bots, rules, and metrics.

Required files:
- `src/tabletop_lab/games/undersight/__init__.py`
- `src/tabletop_lab/games/undersight/cards.py`
- `src/tabletop_lab/games/undersight/actions.py`
- `src/tabletop_lab/games/undersight/state.py`
- `src/tabletop_lab/games/undersight/rules.py`
- `src/tabletop_lab/games/undersight/bots.py`
- `src/tabletop_lab/games/undersight/variants.py`
- `src/tabletop_lab/games/undersight/metrics.py`
- Focused pytest tests under `tests/undersight/`

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
