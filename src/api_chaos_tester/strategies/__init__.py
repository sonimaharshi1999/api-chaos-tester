# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Chaos testing strategies package.
Each strategy generates test cases targeting a specific class of
potential API vulnerabilities or edge-case behaviors.
"""

from api_chaos_tester.strategies.base import BaseStrategy
from api_chaos_tester.strategies.boundary import BoundaryValueStrategy
from api_chaos_tester.strategies.null_injection import NullInjectionStrategy
from api_chaos_tester.strategies.type_confusion import TypeConfusionStrategy
from api_chaos_tester.strategies.unicode_stress import UnicodeStressStrategy
from api_chaos_tester.strategies.special_chars import SpecialCharacterStrategy
from api_chaos_tester.strategies.overflow import OverflowStrategy

ALL_STRATEGIES: list[type[BaseStrategy]] = [
    BoundaryValueStrategy,
    TypeConfusionStrategy,
    NullInjectionStrategy,
    UnicodeStressStrategy,
    SpecialCharacterStrategy,
    OverflowStrategy,
]

__all__ = [
    "BaseStrategy",
    "BoundaryValueStrategy",
    "TypeConfusionStrategy",
    "NullInjectionStrategy",
    "UnicodeStressStrategy",
    "SpecialCharacterStrategy",
    "OverflowStrategy",
    "ALL_STRATEGIES",
]
