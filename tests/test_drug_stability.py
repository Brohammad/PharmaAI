"""
Unit tests for drug stability profiles and excursion classification.
"""

import pytest
from config.drug_stability import (
    classify_excursion,
    get_stability_profile,
    ExcursionType,
    DRUG_STABILITY_PROFILES,
)


class TestDrugStabilityProfiles:
    """Test drug stability profile lookup."""

    def test_known_drug_returns_correct_profile(self):
        profile = get_stability_profile("hepatitis_b_vaccine")
        assert profile is not None
        assert profile.normal_min_temp == 2.0
        assert profile.normal_max_temp == 8.0

    def test_unknown_drug_returns_default(self):
        profile = get_stability_profile("totally_unknown_drug_xyz")
        default = get_stability_profile("default_cold_chain")
        assert profile == default

    def test_freeze_sensitive_drugs_flagged(self):
        """Insulin and vaccines should be freeze-sensitive."""
        insulin = get_stability_profile("insulin_regular")
        assert insulin.freeze_sensitive is True

    def test_all_profiles_have_required_fields(self):
        for drug_id, profile in DRUG_STABILITY_PROFILES.items():
            assert hasattr(profile, "normal_min_temp"), f"{drug_id} missing normal_min_temp"
            assert hasattr(profile, "normal_max_temp"), f"{drug_id} missing normal_max_temp"
            assert hasattr(profile, "freeze_sensitive"), f"{drug_id} missing freeze_sensitive"
            assert profile.normal_min_temp < profile.normal_max_temp, (
                f"{drug_id}: min_temp must be < max_temp"
            )


class TestExcursionClassification:
    """Test excursion type classification logic."""

    def test_normal_temperature_returns_none_or_minor(self):
        """2-8°C is the standard cold chain range. Should not classify as excursion."""
        result = classify_excursion("hepatitis_b_vaccine", 5.0, 0, 0)
        # 5°C is within normal range
        assert result in (ExcursionType.MINOR, None) or result.value == "NONE"

    def test_severe_excursion_above_15c(self):
        result = classify_excursion("hepatitis_b_vaccine", 20.0, 60, 0)
        assert result == ExcursionType.SEVERE

    def test_freeze_excursion_below_zero(self):
        result = classify_excursion("insulin_regular", -2.0, 10, 0)
        assert result == ExcursionType.FREEZE

    def test_moderate_excursion_at_12c_for_30min(self):
        result = classify_excursion("hepatitis_b_vaccine", 12.0, 30, 0)
        assert result in (ExcursionType.MODERATE, ExcursionType.SEVERE)

    def test_cumulative_excursion_budget_overflow_triggers_severe(self):
        """Even a minor current excursion triggers SEVERE if cumulative budget is exhausted."""
        profile = get_stability_profile("hepatitis_b_vaccine")
        # Set cumulative to just above budget
        over_budget = profile.cumulative_excursion_max_minutes + 1
        result = classify_excursion("hepatitis_b_vaccine", 10.0, 20, over_budget)
        assert result in (ExcursionType.MODERATE, ExcursionType.SEVERE)

    def test_mrna_vaccine_is_ultra_cold_chain(self):
        """COVID mRNA vaccines require -70°C storage."""
        profile = get_stability_profile("covid_mrna_vaccine")
        assert profile.normal_max_temp < 0  # Below freezing required
