"""
PharmaIQ – Drug Stability Profiles
WHO PQS-aligned cold chain temperature stability data for key pharmaceutical
categories stored in MedChain's refrigeration network.

This data is version-controlled and manually verified before activation.
It is NOT auto-updated from any external feed.

Reference standards:
  - WHO PQS Performance, Quality and Safety standards
  - CDSCO Schedule C cold chain guidelines
  - ICH Q1A(R2) Stability Testing of New Drug Substances and Products
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class ExcursionType(str, Enum):
    MINOR = "MINOR"        # 2–8°C breach, short duration — log & monitor
    MODERATE = "MODERATE"  # 8–15°C, prolonged — stability data required
    SEVERE = "SEVERE"      # >15°C any duration or <0°C — quarantine
    FREEZE = "FREEZE"      # <0°C — irreversible damage (insulin, some vaccines)


@dataclass(frozen=True)
class StabilityProfile:
    """Drug-specific cold chain stability parameters."""

    drug_category: str
    normal_min_temp: float          # °C
    normal_max_temp: float          # °C
    minor_excursion_max_temp: float         # Max °C for a minor excursion
    minor_excursion_max_minutes: int        # Max duration (minutes) before reclassifying
    moderate_excursion_max_temp: float      # Max °C for a moderate excursion
    moderate_excursion_max_minutes: int     # Max cumulative minutes allowed
    cumulative_excursion_max_minutes: int   # Total lifetime excursion budget (minutes)
    freeze_sensitive: bool                  # True = <0°C causes irreversible damage
    patient_notification_required: bool     # If compromised batch was dispensed
    who_pqs_reference: str = ""
    notes: str = ""


# ── Stability profile registry ─────────────────────────────────────────────────
DRUG_STABILITY_PROFILES: dict[str, StabilityProfile] = {

    # ── Vaccines ───────────────────────────────────────────────────────────────
    "hepatitis_b_vaccine": StabilityProfile(
        drug_category="Vaccine",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=30,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=240,
        cumulative_excursion_max_minutes=120,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="WHO/IVB/14.07",
        notes="Freeze damage non-reversible; shake test required post-exposure <0°C",
    ),
    "dpt_vaccine": StabilityProfile(
        drug_category="Vaccine",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=30,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=120,
        cumulative_excursion_max_minutes=60,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="WHO/IVB/14.07",
        notes="DPT/DTP highly freeze-sensitive; single freeze event = quarantine",
    ),
    "ipv_vaccine": StabilityProfile(
        drug_category="Vaccine",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=30,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=180,
        cumulative_excursion_max_minutes=90,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="WHO/IVB/14.07",
        notes="",
    ),
    "oral_polio_vaccine": StabilityProfile(
        drug_category="Vaccine",
        normal_min_temp=-20.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=30,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=60,
        cumulative_excursion_max_minutes=30,
        freeze_sensitive=False,
        patient_notification_required=True,
        who_pqs_reference="WHO/IVB/14.07",
        notes="OPV is freeze-tolerant; heat-labile VVM indicator must be checked",
    ),
    "covid_mrna_vaccine": StabilityProfile(
        drug_category="Vaccine",
        normal_min_temp=-70.0,
        normal_max_temp=-60.0,
        minor_excursion_max_temp=-50.0,
        minor_excursion_max_minutes=15,
        moderate_excursion_max_temp=2.0,
        moderate_excursion_max_minutes=120,
        cumulative_excursion_max_minutes=30,
        freeze_sensitive=False,
        patient_notification_required=True,
        who_pqs_reference="WHO Emergency Use Listing",
        notes="Ultra-cold chain required; standard pharmacy fridges are NOT suitable",
    ),

    # ── Insulin ────────────────────────────────────────────────────────────────
    "insulin_regular": StabilityProfile(
        drug_category="Biologic - Insulin",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=60,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=240,
        cumulative_excursion_max_minutes=240,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="IDF Insulin Storage Guidelines",
        notes="Opened vials stable at room temp (25°C) for 28 days; unopened must be refrigerated",
    ),
    "insulin_analogue_long_acting": StabilityProfile(
        drug_category="Biologic - Insulin",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=60,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=180,
        cumulative_excursion_max_minutes=180,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="IDF Insulin Storage Guidelines",
        notes="",
    ),

    # ── Biologics ──────────────────────────────────────────────────────────────
    "adalimumab": StabilityProfile(
        drug_category="Biologic - Monoclonal Antibody",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=10.0,
        minor_excursion_max_minutes=15,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=60,
        cumulative_excursion_max_minutes=60,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="EMA/CHMP/274278/2016",
        notes="High-value biologic; any excursion requires manufacturer consultation",
    ),
    "erythropoietin": StabilityProfile(
        drug_category="Biologic - Hormone",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=10.0,
        minor_excursion_max_minutes=30,
        moderate_excursion_max_temp=12.0,
        moderate_excursion_max_minutes=120,
        cumulative_excursion_max_minutes=90,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="",
        notes="",
    ),

    # ── Eye Drops / Ophthalmic ─────────────────────────────────────────────────
    "latanoprost_eye_drops": StabilityProfile(
        drug_category="Ophthalmic - Prostaglandin Analogue",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=12.0,
        minor_excursion_max_minutes=60,
        moderate_excursion_max_temp=15.0,
        moderate_excursion_max_minutes=180,
        cumulative_excursion_max_minutes=120,
        freeze_sensitive=False,
        patient_notification_required=False,
        who_pqs_reference="",
        notes="Once opened, stable at 25°C for 4 weeks",
    ),

    # ── Default / Unknown ──────────────────────────────────────────────────────
    "default_cold_chain": StabilityProfile(
        drug_category="Unknown / Default",
        normal_min_temp=2.0,
        normal_max_temp=8.0,
        minor_excursion_max_temp=8.5,
        minor_excursion_max_minutes=15,
        moderate_excursion_max_temp=12.0,
        moderate_excursion_max_minutes=60,
        cumulative_excursion_max_minutes=30,
        freeze_sensitive=True,
        patient_notification_required=True,
        who_pqs_reference="",
        notes="Conservative defaults applied when drug-specific profile is unavailable. "
              "Always default to strictest profile when data is missing.",
    ),
}


def get_stability_profile(drug_id: str) -> StabilityProfile:
    """
    Return the stability profile for a drug.
    Falls back to 'default_cold_chain' (strictest) if drug is unknown.
    """
    return DRUG_STABILITY_PROFILES.get(drug_id.lower(), DRUG_STABILITY_PROFILES["default_cold_chain"])


def classify_excursion(
    drug_id: str,
    current_temp: float,
    duration_minutes: float,
    cumulative_excursion_minutes: float,
) -> ExcursionType:
    """
    Classify an excursion event given drug profile and observed temperatures.
    Returns the most severe applicable ExcursionType.
    """
    profile = get_stability_profile(drug_id)

    # Freeze check
    if current_temp < 0.0 and profile.freeze_sensitive:
        return ExcursionType.FREEZE

    # Severe: above moderate threshold, any duration
    if current_temp > profile.moderate_excursion_max_temp:
        return ExcursionType.SEVERE

    # Severe: cumulative budget exhausted
    if cumulative_excursion_minutes >= profile.cumulative_excursion_max_minutes:
        return ExcursionType.SEVERE

    # Moderate: at or above minor threshold and duration exceeded
    if current_temp >= profile.minor_excursion_max_temp:
        if duration_minutes >= profile.minor_excursion_max_minutes:
            return ExcursionType.MODERATE
        return ExcursionType.MINOR

    # Above normal max — but within minor threshold
    if current_temp > profile.normal_max_temp:
        return ExcursionType.MINOR

    # Within normal range — not an excursion (caller should not reach this)
    return ExcursionType.MINOR
