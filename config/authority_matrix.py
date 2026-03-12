"""
PharmaIQ – Authority Matrix
Defines which actions require automated execution, human notification,
human approval, or are human-only.

Directly encodes the design mandate from the case study:
  AUTO           → system executes without any human interaction
  HUMAN_INFORMED → system executes AND notifies relevant human
  HUMAN_REQUIRED → system recommends; a human must explicitly approve
  HUMAN_ONLY     → system provides data/context only; no recommendation
"""

from __future__ import annotations

from enum import Enum


class AuthorityLevel(str, Enum):
    AUTO = "AUTO"
    HUMAN_INFORMED = "HUMAN_INFORMED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    HUMAN_ONLY = "HUMAN_ONLY"


# ── Priority hierarchy (lower number = higher priority) ────────────────────────
class Priority(int, Enum):
    PATIENT_SAFETY = 1
    REGULATORY_COMPLIANCE = 2
    COMMERCIAL_FORECAST = 3
    OPERATIONAL_EFFICIENCY = 4


# ── Authority matrix keyed by (domain, action) ────────────────────────────────
# Each entry: (AuthorityLevel, Priority, human_acknowledgement_minutes)

AUTHORITY_MATRIX: dict[tuple[str, str], tuple[AuthorityLevel, Priority, int]] = {
    # ── Cold Chain ─────────────────────────────────────────────────────────────
    ("cold_chain", "excursion_alert_severe"):       (AuthorityLevel.AUTO,           Priority.PATIENT_SAFETY,        0),
    ("cold_chain", "minor_excursion_alert"):        (AuthorityLevel.AUTO,           Priority.PATIENT_SAFETY,        0),
    ("cold_chain", "batch_quarantine_severe"):      (AuthorityLevel.AUTO,           Priority.PATIENT_SAFETY,        0),
    ("cold_chain", "quarantine"):                   (AuthorityLevel.AUTO,           Priority.PATIENT_SAFETY,        0),
    ("cold_chain", "batch_quarantine_moderate"):    (AuthorityLevel.HUMAN_INFORMED, Priority.PATIENT_SAFETY,        60),
    ("cold_chain", "batch_quarantine_minor"):       (AuthorityLevel.HUMAN_INFORMED, Priority.PATIENT_SAFETY,        240),
    ("cold_chain", "maintenance_request"):          (AuthorityLevel.AUTO,           Priority.OPERATIONAL_EFFICIENCY, 0),
    ("cold_chain", "unit_replacement_escalation"):  (AuthorityLevel.HUMAN_REQUIRED, Priority.OPERATIONAL_EFFICIENCY, 1440),
    ("cold_chain", "patient_notification_dispensed"): (AuthorityLevel.HUMAN_REQUIRED, Priority.PATIENT_SAFETY,     30),
    ("cold_chain", "batch_destruction"):            (AuthorityLevel.HUMAN_REQUIRED, Priority.REGULATORY_COMPLIANCE, 120),
    ("cold_chain", "batch_destruction_order"):      (AuthorityLevel.HUMAN_REQUIRED, Priority.REGULATORY_COMPLIANCE, 120),
    ("cold_chain", "store_closure"):                (AuthorityLevel.HUMAN_ONLY,     Priority.REGULATORY_COMPLIANCE, 0),
    ("cold_chain", "cdsco_formal_notification"):    (AuthorityLevel.HUMAN_ONLY,     Priority.REGULATORY_COMPLIANCE, 0),

    # ── Demand / Procurement ───────────────────────────────────────────────────
    ("procurement", "order_up_to_2_5x"):            (AuthorityLevel.AUTO,           Priority.COMMERCIAL_FORECAST,  0),
    ("procurement", "standard_reorder"):            (AuthorityLevel.AUTO,           Priority.COMMERCIAL_FORECAST,  0),
    ("procurement", "order_2_5x_to_3x"):            (AuthorityLevel.HUMAN_INFORMED, Priority.COMMERCIAL_FORECAST,  60),
    ("procurement", "order_above_3x"):              (AuthorityLevel.HUMAN_REQUIRED, Priority.COMMERCIAL_FORECAST,  120),
    ("procurement", "emergency_large_order"):       (AuthorityLevel.HUMAN_REQUIRED, Priority.COMMERCIAL_FORECAST,  120),
    ("procurement", "new_supplier_onboarding"):     (AuthorityLevel.HUMAN_REQUIRED, Priority.COMMERCIAL_FORECAST,  2880),
    ("procurement", "distributor_switch"):          (AuthorityLevel.HUMAN_REQUIRED, Priority.COMMERCIAL_FORECAST,  1440),
    ("procurement", "epidemic_alert_public_health"): (AuthorityLevel.HUMAN_REQUIRED, Priority.REGULATORY_COMPLIANCE, 30),

    # ── Inventory / Expiry ─────────────────────────────────────────────────────
    ("inventory", "expiry_risk_alert"):             (AuthorityLevel.AUTO,           Priority.COMMERCIAL_FORECAST,  0),
    ("inventory", "inter_store_transfer_same_zone"): (AuthorityLevel.AUTO,          Priority.COMMERCIAL_FORECAST,  0),
    ("inventory", "inter_store_transfer_cross_zone"): (AuthorityLevel.HUMAN_INFORMED, Priority.COMMERCIAL_FORECAST, 120),
    ("inventory", "markdown_near_expiry"):          (AuthorityLevel.HUMAN_INFORMED, Priority.COMMERCIAL_FORECAST,  240),
    ("inventory", "recall_shelf_removal_standard"): (AuthorityLevel.AUTO,           Priority.REGULATORY_COMPLIANCE, 0),

    # ── Staffing ───────────────────────────────────────────────────────────────
    ("staffing", "routine_schedule_optimisation"):  (AuthorityLevel.AUTO,           Priority.OPERATIONAL_EFFICIENCY, 0),
    ("staffing", "compliance_notification"):        (AuthorityLevel.AUTO,           Priority.REGULATORY_COMPLIANCE,  0),
    ("staffing", "shift_gap_notification"):         (AuthorityLevel.AUTO,           Priority.REGULATORY_COMPLIANCE,  0),
    ("staffing", "overtime_schedule_change"):       (AuthorityLevel.HUMAN_INFORMED, Priority.OPERATIONAL_EFFICIENCY, 60),
    ("staffing", "cross_zone_redeployment"):        (AuthorityLevel.HUMAN_REQUIRED, Priority.REGULATORY_COMPLIANCE, 30),
    ("staffing", "emergency_redeployment_zone"):    (AuthorityLevel.HUMAN_REQUIRED, Priority.REGULATORY_COMPLIANCE, 30),
    ("staffing", "compliance_escalation_schedule_h"): (AuthorityLevel.HUMAN_REQUIRED, Priority.REGULATORY_COMPLIANCE, 15),
    ("staffing", "formal_cdsco_notification"):      (AuthorityLevel.HUMAN_ONLY,     Priority.REGULATORY_COMPLIANCE, 0),

    # ── Regulatory / Legal ─────────────────────────────────────────────────────
    ("regulatory", "store_closure_recommendation"): (AuthorityLevel.HUMAN_ONLY,    Priority.REGULATORY_COMPLIANCE, 0),
    ("regulatory", "legal_insurance_claim"):        (AuthorityLevel.HUMAN_ONLY,    Priority.REGULATORY_COMPLIANCE, 0),
    ("regulatory", "employee_disciplinary_action"): (AuthorityLevel.HUMAN_ONLY,    Priority.PATIENT_SAFETY,        0),
    ("regulatory", "public_safety_communication"):  (AuthorityLevel.HUMAN_ONLY,    Priority.PATIENT_SAFETY,        0),

    # ── System / Infrastructure ────────────────────────────────────────────────
    ("system", "high_cost_action_above_2lakh"):     (AuthorityLevel.HUMAN_REQUIRED, Priority.COMMERCIAL_FORECAST, 120),
}


def get_authority(domain: str, action: str) -> AuthorityLevel:
    """
    Look up authority level for a (domain, action) pair.
    Falls back to HUMAN_REQUIRED if the combination is not explicitly mapped.
    """
    key = (domain, action)
    entry = AUTHORITY_MATRIX.get(
        key,
        (AuthorityLevel.HUMAN_REQUIRED, Priority.OPERATIONAL_EFFICIENCY, 120),
    )
    return entry[0]


def get_authority_full(domain: str, action: str) -> tuple[AuthorityLevel, Priority, int]:
    """
    Full tuple (AuthorityLevel, Priority, ack_minutes) for a (domain, action) pair.
    """
    key = (domain, action)
    return AUTHORITY_MATRIX.get(
        key,
        (AuthorityLevel.HUMAN_REQUIRED, Priority.OPERATIONAL_EFFICIENCY, 120),
    )


def requires_human(domain: str, action: str) -> bool:
    """Returns True if the action requires any form of human involvement."""
    level = get_authority(domain, action)
    return level in (AuthorityLevel.HUMAN_INFORMED, AuthorityLevel.HUMAN_REQUIRED, AuthorityLevel.HUMAN_ONLY)


def can_auto_execute(domain: str, action: str) -> bool:
    """Returns True only for fully automated actions."""
    level = get_authority(domain, action)
    return level == AuthorityLevel.AUTO
