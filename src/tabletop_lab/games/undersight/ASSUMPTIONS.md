# Undersight Simulator Assumptions

The stored rules define the core loop but do not include full card text for
Installations, Directives, Starter Zones, Departments, minor actions, or all
Spillover variants. This implementation therefore models a deterministic starter
card set that is sufficient to exercise the economy, tableau, dice binding,
escalation, Severance, and final scoring systems.

Current assumptions and TODOs:

- A turn may skip the Play, Allocation, Discharge, and Minor Action phases when
  no useful option is available. The rules say "play one" and "allocate one",
  but a simulator needs a legal no-op for exhausted hands and blocked dice pools.
- Starter card rewards in `cards.py` are provisional simulator data, not claimed
  canonical Undersight card text.
- Generated legal actions expose zero or one die discharge to keep bot action
  spaces small. `UndersightAction` and `apply_action` still support discharging
  multiple dice for direct tests and future smarter bots.
- Spillovers are modeled as tokens on the source card. Each orthogonally
  adjacent Spillover token adds +1 round escalation to dice on adjacent cards.
  "Next time" tilted-card effects are represented in state but no starter card
  currently emits them.
- Forbidden Depths are positions with depth >= 4. Playing or allocating there
  requires one Excavation Waiver; playing a card consumes one Waiver.
- Owner passive bonuses are claimed once per round per Installation, keyed by
  Installation owner.
- Department abilities are only implemented where the stored text includes a
  usable rule: Extraction gets +1 VP for value-8 discharges, Oversight gains
  +1 Influence when creating a Spillover, and Influence gets one free minor
  action. Other department abilities remain TODOs in `cards.py`.
