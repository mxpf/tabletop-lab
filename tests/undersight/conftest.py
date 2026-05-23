from __future__ import annotations

import random

import pytest

from tabletop_lab.games.undersight.rules import UndersightRules
from tabletop_lab.games.undersight.variants import get_variant


@pytest.fixture
def rules() -> UndersightRules:
    return UndersightRules()


@pytest.fixture
def state(rules):
    return rules.setup(random.Random(7), get_variant("base_3p"))
