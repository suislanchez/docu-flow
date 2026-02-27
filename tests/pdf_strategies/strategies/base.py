"""Abstract base for all strategy adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from tests.pdf_strategies.result import StrategyResult


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, pdf_path: Path) -> StrategyResult:
        """Run the strategy on *pdf_path* and return a StrategyResult."""
        ...
