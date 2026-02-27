"""Unit tests for the disqualifier ranker."""

import pytest

from docu_flow.pipeline.ranker import rank_disqualifiers, _score
from docu_flow.schemas.criteria import (
    CriterionType,
    DisqualificationPower,
    EligibilityCriterion,
    ExtractedCriteria,
    ExtractionMetadata,
)


def _make_criterion(text: str, ctype: CriterionType = CriterionType.EXCLUSION, **kwargs) -> EligibilityCriterion:
    return EligibilityCriterion(id="test_001", criterion_type=ctype, text=text, **kwargs)


def _make_extracted(criteria: list[EligibilityCriterion]) -> ExtractedCriteria:
    return ExtractedCriteria(
        criteria=criteria,
        metadata=ExtractionMetadata(
            model_used="test",
            extraction_confidence=1.0,
            section_found=True,
        ),
    )


class TestScoring:
    def test_pregnancy_scores_high(self):
        c = _make_criterion("Patients who are pregnant or breastfeeding are excluded.")
        assert _score(c) >= 3.0

    def test_ambiguous_penalised(self):
        c = _make_criterion("Clinically significant cardiac disease.", is_ambiguous=True)
        c_no_ambig = _make_criterion("Clinically significant cardiac disease.", is_ambiguous=False)
        assert _score(c) < _score(c_no_ambig)

    def test_numeric_threshold_adds_score(self):
        c_thresh = _make_criterion("eGFR < 30 mL/min", has_numeric_threshold=True)
        c_no_thresh = _make_criterion("eGFR < 30 mL/min", has_numeric_threshold=False)
        assert _score(c_thresh) > _score(c_no_thresh)

    def test_inclusion_can_be_scored(self):
        c = _make_criterion("Age 18 or older", ctype=CriterionType.INCLUSION)
        # Score function doesn't check type; ranking only applies to exclusions
        score = _score(c)
        assert isinstance(score, float)


class TestRankDisqualifiers:
    def test_top_n_capped(self):
        criteria = [
            _make_criterion(f"Exclusion criterion {i}") for i in range(20)
        ]
        extracted = _make_extracted(criteria)
        result = rank_disqualifiers(extracted, top_n=8)
        assert len(result.top_disqualifiers) == 8

    def test_only_exclusions_ranked(self):
        criteria = [
            _make_criterion("Prior malignancy", ctype=CriterionType.EXCLUSION),
            _make_criterion("Age >= 18", ctype=CriterionType.INCLUSION),
        ]
        extracted = _make_extracted(criteria)
        result = rank_disqualifiers(extracted, top_n=8)
        for c in result.top_disqualifiers:
            assert c.criterion_type == CriterionType.EXCLUSION

    def test_high_power_criteria_ranked_first(self):
        criteria = [
            _make_criterion("Subject prefers coffee over tea."),
            _make_criterion("Active hepatitis B infection or positive HBsAg."),
            _make_criterion("Pregnant or lactating women."),
        ]
        extracted = _make_extracted(criteria)
        result = rank_disqualifiers(extracted, top_n=3)
        top_texts = [c.text for c in result.top_disqualifiers]
        # Pregnancy and HBV should outrank the coffee criterion
        assert top_texts[0] != "Subject prefers coffee over tea."
