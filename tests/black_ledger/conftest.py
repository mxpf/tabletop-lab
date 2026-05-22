from __future__ import annotations

import random

import pytest

from tabletop_lab.games.black_ledger.rules import BlackLedgerRules
from tabletop_lab.games.black_ledger.variants import get_variant


@pytest.fixture
def rules() -> BlackLedgerRules:
    return BlackLedgerRules()


@pytest.fixture
def state(rules):
    return rules.setup(random.Random(7), get_variant("base_3p"))


def stake_ids(player, values):
    ids = []
    for value in values:
        card = next(card for card in player.hand if card.value == value and card.id not in ids)
        ids.append(card.id)
    return tuple(ids)
