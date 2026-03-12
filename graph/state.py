"""
PharmaIQ – LangGraph Shared State
The single source of truth that all eight agents read from and write to.
All fields are optional to support graceful partial updates per node.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field


# ── Sub-models (embedded in state) ────────────────────────────────────────────

class ColdChainAlert(BaseModel):
    alert_id: str
    store_id: str
    unit_id: str
    batch_ids: list[str]
    current_temp: float
    trend_c_per_min: float
    excursion_type: str  # MINOR | MODERATE | SEVERE | FREEZE
    drug_profiles: list[str]
    cumulative_excursion_minutes: float
    sentinel_recommendation: str
    critique_verdict: str | None = None
    compliance_verdict: str | None = None
    status: str = "PENDING"  # PENDING | VALIDATED | EXECUTING | RESOLVED


class QuarantineAction(BaseModel):
    quarantine_id: str
    store_id: str
    batch_ids: list[str]
    reason: str
    authority_level: str
    approved_by: str | None = None
    executed_at: str | None = None
    status: str = "PENDING"


class DemandForecast(BaseModel):
    store_id: str
    sku_id: str
    sku_name: str
    baseline_units: float
    scenario_weighted_units: float
    scenarios: list[dict[str, Any]]
    confidence: float
    data_sources: list[str]
    recheck_triggers: list[str]
    forecast_horizon_days: int = 7


class EpidemicSignal(BaseModel):
    signal_id: str
    zone_id: str
    disease: str
    probability: float           # 0.0–1.0
    confidence: str              # LOW | MEDIUM | HIGH
    affected_stores: list[str]
    expected_demand_multiplier: float
    data_sources: list[dict[str, Any]]
    lead_time_days: int
    status: str = "ACTIVE"      # ACTIVE | CONFIRMED | RESOLVED | FALSE_ALARM


class InventoryItem(BaseModel):
    store_id: str
    sku_id: str
    batch_id: str
    quantity: int
    expiry_date: str             # ISO date string
    unit_cost_inr: float
    days_of_stock: float
    lifecycle_state: str         # HEALTHY | AT_RISK | INTERVENTION_* | CONDEMNED


class ExpiryRiskItem(BaseModel):
    store_id: str
    sku_id: str
    batch_id: str
    expiry_date: str
    days_to_expiry: int
    days_of_stock_at_current_velocity: float
    days_of_stock_at_forecast_velocity: float
    risk_score: float            # 0.0–1.0 (>0.9 = guaranteed write-off without action)
    recommended_intervention: str
    estimated_loss_lakh: float


class StaffingGap(BaseModel):
    store_id: str
    gap_type: str                # SCHEDULE_H | UNDERSTAFFED | OVERTIME_BREACH
    start_time: str
    end_time: str
    severity: str                # LOW | MEDIUM | HIGH | CRITICAL
    recommended_action: str
    aegis_confidence: float


class PendingEscalation(BaseModel):
    escalation_id: str
    action_type: str = ""
    description: str = ""
    requiring_agent: str = ""
    urgency: str = "URGENT"
    deadline_utc: str = ""
    status: str = "PENDING_HUMAN"   # PENDING_HUMAN | APPROVED | REJECTED | ESCALATED
    reviewed_by: str | None = None
    decision_at: str | None = None
    # Legacy / extended fields
    domain: str = ""
    action: str = ""
    agent: str = ""
    authority_level: str = ""
    context_summary: str = ""
    full_reasoning: str = ""
    estimated_cost_lakh: float | None = None
    created_at: str = ""
    ack_deadline_minutes: int = 60


class CritiqueVerdict(BaseModel):
    verdict_id: str
    proposal_id: str
    proposal_type: str
    agent_source: str
    outcome: str                 # VALIDATED | CHALLENGED | DOWNGRADED | REJECTED
    overall_score: float = 5.0
    confidence_adjustment: float = 0.0
    dimension_results: dict[str, Any] = Field(default_factory=dict)
    required_modifications: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ComplianceVerdict(BaseModel):
    verdict_id: str
    proposal_id: str
    proposal_type: str
    agent_source: str
    outcome: str                 # COMPLIANT | CONDITIONALLY_COMPLIANT | NON_COMPLIANT
    documentation_required: list[str] = Field(default_factory=list)
    documentation_generated: dict[str, Any] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    reporting_obligations: list[str] = Field(default_factory=list)
    regulatory_basis: list[str] = Field(default_factory=list)
    compliance_confidence: float = 0.8
    reasoning: str = ""


class ChronicleContext(BaseModel):
    """Historical context injected by CHRONICLE into the current reasoning cycle."""
    relevant_patterns: list[dict[str, Any]] = Field(default_factory=list)
    recent_accuracy_metrics: dict[str, float] = Field(default_factory=dict)
    similar_past_decisions: list[dict[str, Any]] = Field(default_factory=list)
    calibration_adjustments: dict[str, float] = Field(default_factory=dict)
    data_quality_warnings: list[str] = Field(default_factory=list)
    red_team_alerts: list[str] = Field(default_factory=list)


# ── Master state ───────────────────────────────────────────────────────────────

class PharmaIQState(BaseModel):
    """
    Complete LangGraph state object for PharmaIQ.

    Every field defaults to None/empty to allow partial updates from any node.
    CHRONICLE and NEXUS synthesise the full state picture.
    """

    # ── Cycle identity ─────────────────────────────────────────────────────────
    cycle_id: str | None = None
    cycle_type: str | None = None   # REALTIME | MORNING | MIDDAY | COMPLIANCE | EXPIRY | WEEKLY | RED_TEAM
    signal_type: str | None = None  # SignalType value captured at ingestion
    triggered_by: str | None = None
    timestamp_utc: str | None = None
    raw_event: dict[str, Any] = Field(default_factory=dict)

    # ── Store / Zone context ───────────────────────────────────────────────────
    store_id: str | None = None
    zone_id: str | None = None
    store_tier: str | None = None   # TIER1 | TIER2
    data_quality_score: float | None = None  # 0.0–1.0

    # ── Cold chain state (SENTINEL) ────────────────────────────────────────────
    cold_chain_alerts: list[ColdChainAlert] = Field(default_factory=list)
    quarantine_actions: list[QuarantineAction] = Field(default_factory=list)
    cold_chain_risk_level: Literal["normal", "watch", "elevated", "critical"] = "normal"
    iot_coverage_pct: float = 1.0   # 1.0 = full IoT, 0 = manual logs only

    # ── Demand intelligence state (PULSE) ─────────────────────────────────────
    demand_forecasts: list[DemandForecast] = Field(default_factory=list)
    epidemic_signals: list[EpidemicSignal] = Field(default_factory=list)
    demand_anomalies: list[dict[str, Any]] = Field(default_factory=list)
    epidemic_confidence: float = 0.0

    # ── Inventory / expiry state (MERIDIAN) ───────────────────────────────────
    inventory_positions: list[InventoryItem] = Field(default_factory=list)
    expiry_risk_items: list[ExpiryRiskItem] = Field(default_factory=list)
    pending_orders: list[dict[str, Any]] = Field(default_factory=list)
    stockout_risks: list[dict[str, Any]] = Field(default_factory=list)
    inter_store_transfer_proposals: list[dict[str, Any]] = Field(default_factory=list)

    # ── Staffing state (AEGIS) ─────────────────────────────────────────────────
    schedule_status: dict[str, Any] = Field(default_factory=dict)
    compliance_gaps: list[StaffingGap] = Field(default_factory=list)
    staffing_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    overtime_budget_remaining_lakh: float | None = None
    contingency_schedules: list[dict[str, Any]] = Field(default_factory=list)

    # ── CRITIQUE / COMPLIANCE validation state (Tier 2) ───────────────────────
    critique_verdicts: list[CritiqueVerdict] = Field(default_factory=list)
    compliance_verdicts: list[ComplianceVerdict] = Field(default_factory=list)
    pending_rechallenges: list[dict[str, Any]] = Field(default_factory=list)

    # ── NEXUS decision state (Tier 3) ─────────────────────────────────────────
    nexus_priority_decisions: list[dict[str, Any]] = Field(default_factory=list)
    resource_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    approved_actions: list[dict[str, Any]] = Field(default_factory=list)
    pending_escalations: list[PendingEscalation] = Field(default_factory=list)

    # ── CHRONICLE memory state (Tier 3) ───────────────────────────────────────
    chronicle_context: ChronicleContext | None = None
    decisions_for_outcome_tracking: list[dict[str, Any]] = Field(default_factory=list)
    calibration_updates: list[dict[str, Any]] = Field(default_factory=list)

    # ── Execution state ────────────────────────────────────────────────────────
    executed_actions: list[dict[str, Any]] = Field(default_factory=list)
    execution_results: list[dict[str, Any]] = Field(default_factory=list)
    execution_errors: list[dict[str, Any]] = Field(default_factory=list)

    # ── Audit / reasoning chain (LangGraph message accumulator) ───────────────
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # ── Routing signals (set by nodes to control graph flow) ──────────────────
    route_to_critique: bool = False
    route_to_compliance: bool = False
    route_to_nexus: bool = False
    route_to_human_escalation: bool = False
    route_to_execution: bool = False
    cycle_complete: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

