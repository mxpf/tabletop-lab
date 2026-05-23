"""Undersight game implementation."""

from .bots import BOT_REGISTRY
from .rules import UndersightRules
from .variants import VARIANTS, get_variant

__all__ = ["BOT_REGISTRY", "UndersightRules", "VARIANTS", "get_variant"]
