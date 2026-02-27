"""Schemas for eligibility criteria and screening decisions."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CriterionType(StrEnum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"


class DisqualificationPower(StrEnum):
    """Estimated fraction of general population this criterion would eliminate."""
    VERY_HIGH = "very_high"   # >30% eliminated
    HIGH = "high"             # 10–30%
    MEDIUM = "medium"         # 3–10%
    LOW = "low"               # <3%
    UNKNOWN = "unknown"


class EligibilityCriterion(BaseModel):
    id: str = Field(description="Stable identifier, e.g. 'exc_001'")
    criterion_type: CriterionType
    text: str = Field(description="Verbatim criterion text from the protocol")
    source_page: int | None = None
    source_section: str | None = None
    disqualification_power: DisqualificationPower = DisqualificationPower.UNKNOWN
    # Structured fields parsed from criterion text
    has_temporal_condition: bool = False   # "within 4 weeks"
    has_numeric_threshold: bool = False    # "eGFR >= 30"
    has_conditional_logic: bool = False    # "unless HbA1c < 7"
    is_ambiguous: bool = False             # "clinically significant"
    notes: str = ""


class ExtractionMetadata(BaseModel):
    model_used: str
    protocol_version: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    section_found: bool
    section_name: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ExtractedCriteria(BaseModel):
    protocol_title: str | None = None
    sponsor: str | None = None
    phase: str | None = None
    therapeutic_area: str | None = None
    criteria: list[EligibilityCriterion]
    top_disqualifiers: list[EligibilityCriterion] = Field(
        default_factory=list,
        description="Top 8 ranked exclusion criteria by disqualification power",
    )
    metadata: ExtractionMetadata

    def inclusion_criteria(self) -> list[EligibilityCriterion]:
        return [c for c in self.criteria if c.criterion_type == CriterionType.INCLUSION]

    def exclusion_criteria(self) -> list[EligibilityCriterion]:
        return [c for c in self.criteria if c.criterion_type == CriterionType.EXCLUSION]


# ---------------------------------------------------------------------------
# Screening schemas
# ---------------------------------------------------------------------------

class ScreeningDecision(StrEnum):
    DISQUALIFIED = "disqualified"
    PASSED_PRESCREEN = "passed_prescreen"   # passed top-8, needs full review
    ESCALATE = "escalate"                   # low confidence, human needed


class FailedCriterion(BaseModel):
    criterion: EligibilityCriterion
    reason: str


class ScreeningRequest(BaseModel):
    """Patient data submitted for screening against a protocol."""
    patient_id: str
    protocol_id: str
    patient_data: dict[str, Any] = Field(
        description="Free-form patient attributes (age, diagnoses, labs, medications, etc.)"
    )


class ScreeningResult(BaseModel):
    patient_id: str
    protocol_id: str
    decision: ScreeningDecision
    confidence: float = Field(ge=0.0, le=1.0)
    failed_criteria: list[FailedCriterion] = Field(default_factory=list)
    passed_criteria_count: int = 0
    escalation_reason: str | None = None
    model_used: str | None = None
