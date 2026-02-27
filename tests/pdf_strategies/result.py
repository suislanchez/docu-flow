"""
Shared output schema for all PDF parsing strategies.

Every strategy adapter must return a StrategyResult. This makes the evaluator
and comparison table format-agnostic — it doesn't care how each strategy works
internally, only what it produced.

Ranking convention (matches UX):
  rank 8 = highest disqualification power (eliminates the most candidates)
  rank 1 = lowest within the top 8
  Together the top 8 should eliminate ~80% of candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CriterionResult:
    id: str
    criterion_type: str          # "inclusion" | "exclusion"
    text: str
    source_page: int | None = None
    has_temporal_condition: bool = False
    has_numeric_threshold: bool = False
    has_conditional_logic: bool = False
    is_ambiguous: bool = False


@dataclass
class RankedDisqualifier:
    rank: int                    # 8 = highest power, 1 = lowest within top 8
    criterion_id: str
    criterion_text: str
    disqualification_power: str  # "very_high" | "high" | "medium" | "low"
    reasoning: str = ""


@dataclass
class StrategyResult:
    strategy_name: str
    pdf_name: str

    # --- Section detection ---
    section_found: bool = False
    section_pages: list[int] = field(default_factory=list)
    section_name: str | None = None
    section_confidence: float = 0.0

    # --- Extraction ---
    total_criteria: int = 0
    inclusion_count: int = 0
    exclusion_count: int = 0
    criteria: list[CriterionResult] = field(default_factory=list)

    # --- Ranking ---
    top_8_disqualifiers: list[RankedDisqualifier] = field(default_factory=list)

    # --- Performance ---
    latency_seconds: float = 0.0
    estimated_cost_usd: float = 0.0

    # --- Status ---
    success: bool = False
    error: str | None = None
    raw_output_preview: str = ""  # first 500 chars of raw LLM/parser output

    def summary(self) -> str:
        status = "OK" if self.success else f"FAILED: {self.error}"
        return (
            f"[{self.strategy_name}] {status} | "
            f"section={'yes' if self.section_found else 'no'} | "
            f"criteria={self.total_criteria} | "
            f"top8={len(self.top_8_disqualifiers)} | "
            f"{self.latency_seconds:.1f}s | "
            f"${self.estimated_cost_usd:.4f}"
        )
