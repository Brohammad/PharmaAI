"""
Signal Ingestion and Routing Layer.

Classifies incoming signals and determines which Tier 1 agents to activate.
Acts as the entry point for ALL external events into the LangGraph workflow.

Signal taxonomy:
  cold_chain_alert      → SENTINEL (+ AEGIS for patient counselling)
  staffing_event        → AEGIS
  demand_anomaly        → PULSE + MERIDIAN
  epidemic_signal       → PULSE + AEGIS + MERIDIAN
  recall_notice         → SENTINEL + MERIDIAN + AEGIS (patient contact)
  scheduled_forecast    → depends on cycle type
  multi_domain          → all relevant agents
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from config.settings import settings
from graph.state import PharmaIQState
from utils.logger import get_logger

logger = get_logger("graph.ingestion")


class SignalType(str, Enum):
    COLD_CHAIN_ALERT = "cold_chain_alert"
    STAFFING_EVENT = "staffing_event"
    DEMAND_ANOMALY = "demand_anomaly"
    EPIDEMIC_SIGNAL = "epidemic_signal"
    RECALL_NOTICE = "recall_notice"
    SCHEDULED_FORECAST = "scheduled_forecast"
    MULTI_DOMAIN = "multi_domain"
    UNKNOWN = "unknown"


class CycleType(str, Enum):
    MORNING_FORECAST = "MORNING_FORECAST"         # 05:00 daily
    MIDDAY_REFORECAST = "MIDDAY_REFORECAST"       # 13:00 daily
    COMPLIANCE_SWEEP = "COMPLIANCE_SWEEP"          # Every 2 hours
    EXPIRY_REVIEW = "EXPIRY_REVIEW"               # 22:00 daily
    WEEKLY_BRIEF = "WEEKLY_BRIEF"                  # Monday 07:00
    REACTIVE_COLD_CHAIN = "REACTIVE_COLD_CHAIN"   # IoT triggered
    REACTIVE_EPIDEMIC = "REACTIVE_EPIDEMIC"        # IDSP/WHO triggered
    REACTIVE_STAFFING = "REACTIVE_STAFFING"        # HR event triggered
    REACTIVE_RECALL = "REACTIVE_RECALL"            # CDSCO triggered
    MANUAL_TRIGGER = "MANUAL_TRIGGER"              # API call


# Maps cycle type to which Tier 1 agents should be activated
CYCLE_AGENT_MAP: dict[str, list[str]] = {
    CycleType.MORNING_FORECAST: ["CHRONICLE_ENTRY", "SENTINEL", "PULSE", "MERIDIAN", "AEGIS"],
    CycleType.MIDDAY_REFORECAST: ["CHRONICLE_ENTRY", "PULSE", "MERIDIAN"],
    CycleType.COMPLIANCE_SWEEP: ["CHRONICLE_ENTRY", "AEGIS", "SENTINEL"],
    CycleType.EXPIRY_REVIEW: ["CHRONICLE_ENTRY", "MERIDIAN", "PULSE"],
    CycleType.WEEKLY_BRIEF: ["CHRONICLE_ENTRY", "SENTINEL", "PULSE", "AEGIS", "MERIDIAN"],
    CycleType.REACTIVE_COLD_CHAIN: ["CHRONICLE_ENTRY", "SENTINEL", "MERIDIAN"],
    CycleType.REACTIVE_EPIDEMIC: ["CHRONICLE_ENTRY", "PULSE", "AEGIS", "MERIDIAN"],
    CycleType.REACTIVE_STAFFING: ["CHRONICLE_ENTRY", "AEGIS"],
    CycleType.REACTIVE_RECALL: ["CHRONICLE_ENTRY", "SENTINEL", "MERIDIAN", "AEGIS"],
    CycleType.MANUAL_TRIGGER: ["CHRONICLE_ENTRY", "SENTINEL", "PULSE", "AEGIS", "MERIDIAN"],
}

# Significance thresholds — signals below these do NOT route to CRITIQUE
SIGNIFICANCE_THRESHOLDS = {
    SignalType.COLD_CHAIN_ALERT: 0.3,       # Even minor deviations should be noted
    SignalType.DEMAND_ANOMALY: 0.15,         # 15% deviation from forecast
    SignalType.EPIDEMIC_SIGNAL: 0.25,        # 25% confidence threshold
    SignalType.STAFFING_EVENT: 0.0,          # All staffing events are significant
    SignalType.RECALL_NOTICE: 0.0,           # All recalls are significant
    SignalType.SCHEDULED_FORECAST: 0.0,      # Scheduled cycles always proceed
    SignalType.MULTI_DOMAIN: 0.0,            # Multi-domain always proceeds
}


def classify_signal(raw_event: dict[str, Any]) -> SignalType:
    """
    Classify an incoming raw event into a SignalType.
    Uses keyword matching + field presence heuristics.
    """
    event_type = raw_event.get("event_type", "").lower()
    source = raw_event.get("source", "").lower()
    data = raw_event.get("data", {})

    # Explicit type field takes priority
    if "cold_chain" in event_type or "temperature" in event_type or "fridge" in event_type:
        return SignalType.COLD_CHAIN_ALERT
    if "scheduled" in event_type or "cron" in source or "cycle" in event_type:
        return SignalType.SCHEDULED_FORECAST
    if "staffing" in event_type or "pharmacist" in event_type or "schedule" in event_type:
        return SignalType.STAFFING_EVENT
    if "epidemic" in event_type or "outbreak" in event_type or "disease" in event_type:
        return SignalType.EPIDEMIC_SIGNAL
    if "recall" in event_type or "cdsco" in source:
        return SignalType.RECALL_NOTICE
    if "demand" in event_type or "sales" in event_type or "forecast" in event_type:
        return SignalType.DEMAND_ANOMALY

    # Multi-domain if multiple domain indicators present
    domains_present = sum([
        "cold_chain" in str(data),
        "demand" in str(data),
        "staff" in str(data),
        "expiry" in str(data),
    ])
    if domains_present >= 2:
        return SignalType.MULTI_DOMAIN

    return SignalType.UNKNOWN


def determine_cycle_type(
    signal_type: SignalType,
    raw_event: dict[str, Any],
    current_hour: int | None = None,
) -> CycleType:
    """Determine the CycleType for this invocation."""
    if signal_type == SignalType.COLD_CHAIN_ALERT:
        return CycleType.REACTIVE_COLD_CHAIN
    if signal_type == SignalType.EPIDEMIC_SIGNAL:
        return CycleType.REACTIVE_EPIDEMIC
    if signal_type == SignalType.STAFFING_EVENT:
        return CycleType.REACTIVE_STAFFING
    if signal_type == SignalType.RECALL_NOTICE:
        return CycleType.REACTIVE_RECALL

    # Scheduled — determine which cycle by hour
    if signal_type == SignalType.SCHEDULED_FORECAST:
        hour = current_hour or datetime.now(timezone.utc).hour
        if hour == settings.morning_forecast_hour:
            return CycleType.MORNING_FORECAST
        if hour == settings.midday_reforecast_hour:
            return CycleType.MIDDAY_REFORECAST
        if hour == settings.expiry_review_hour:
            return CycleType.EXPIRY_REVIEW
        if hour == settings.weekly_brief_hour:
            return CycleType.WEEKLY_BRIEF
        return CycleType.COMPLIANCE_SWEEP

    # Manual API trigger or unknown
    return CycleType.MANUAL_TRIGGER


def compute_signal_significance(
    signal_type: SignalType,
    raw_event: dict[str, Any],
) -> float:
    """
    Compute a 0.0–1.0 significance score for the signal.
    Signals below the threshold for their type will be dropped at the gate.
    """
    data = raw_event.get("data", {})

    if signal_type == SignalType.COLD_CHAIN_ALERT:
        temp = data.get("current_temp", 2.0)
        return min(abs(temp - 5.0) / 20.0, 1.0)  # Scale: 0 at 5°C, 1.0 at 25°C

    if signal_type == SignalType.DEMAND_ANOMALY:
        magnitude = data.get("magnitude_pct", 0.0)
        return min(magnitude, 1.0)

    if signal_type == SignalType.EPIDEMIC_SIGNAL:
        confidence = data.get("confidence", 0.0)
        return confidence

    # All other signal types are always significant
    return 1.0


def passes_significance_gate(
    signal_type: SignalType,
    significance: float,
) -> bool:
    """Gate: only route signals that exceed the threshold for their type."""
    threshold = SIGNIFICANCE_THRESHOLDS.get(signal_type, 0.3)
    return significance >= threshold


def build_initial_state(
    raw_event: dict[str, Any],
    store_id: str,
    zone_id: str,
    signal_type: SignalType,
    cycle_type: CycleType,
) -> dict[str, Any]:
    """
    Build the initial PharmaIQState fields from the incoming signal.
    """
    return {
        "store_id": store_id,
        "zone_id": zone_id,
        "cycle_type": cycle_type.value,
        "signal_type": signal_type.value,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "raw_event": raw_event,
        # Routing flags — all False at start
        "route_to_critique": False,
        "route_to_compliance": False,
        "route_to_nexus": False,
        "route_to_human_escalation": False,
        "route_to_execution": False,
        "cycle_complete": False,
        # Empty collections
        "cold_chain_alerts": [],
        "quarantine_actions": [],
        "demand_forecasts": [],
        "epidemic_signals": [],
        "inventory_positions": [],
        "expiry_risk_items": [],
        "compliance_gaps": [],
        "staffing_recommendations": [],
        "critique_verdicts": [],
        "compliance_verdicts": [],
        "nexus_priority_decisions": [],
        "pending_escalations": [],
        "demand_anomalies": [],
        "inter_store_transfer_proposals": [],
        "cold_chain_risk_level": "normal",
        "epidemic_confidence": 0.0,
        "schedule_status": {},
        "messages": [],
    }


def get_active_agents_for_cycle(cycle_type: CycleType) -> list[str]:
    """Return the list of agents to activate for a given cycle type."""
    return CYCLE_AGENT_MAP.get(cycle_type, CYCLE_AGENT_MAP[CycleType.MANUAL_TRIGGER])


def ingestion_router(state: PharmaIQState) -> str:
    """
    LangGraph conditional edge: after CHRONICLE entry, route to first Tier 1 agent.
    Returns the name of the next node.
    """
    cycle = state.cycle_type or CycleType.MANUAL_TRIGGER.value
    active = get_active_agents_for_cycle(CycleType(cycle))

    # Filter out CHRONICLE_ENTRY (already run)
    next_agents = [a for a in active if a != "CHRONICLE_ENTRY"]
    if not next_agents:
        return "nexus"

    # Map agent name to node name
    node_map = {
        "SENTINEL": "sentinel",
        "PULSE": "pulse",
        "AEGIS": "aegis",
        "MERIDIAN": "meridian",
    }
    return node_map.get(next_agents[0], "nexus")


def post_tier1_router(state: PharmaIQState) -> str:
    """
    LangGraph conditional edge: after all Tier 1 agents run.
    Routes to CRITIQUE if any agents flagged proposals, else NEXUS.
    """
    if state.route_to_critique:
        return "critique"
    if state.route_to_compliance:
        return "compliance"
    return "nexus"


def post_critique_router(state: PharmaIQState) -> str:
    """Route after CRITIQUE: always to COMPLIANCE."""
    return "compliance"


def post_compliance_router(state: PharmaIQState) -> str:
    """Route after COMPLIANCE: always to NEXUS."""
    return "nexus"


def post_nexus_router(state: PharmaIQState) -> str:
    """
    Route after NEXUS: to execution if approved actions exist, else to chronicle exit.
    """
    if state.route_to_execution:
        return "execution"
    return "chronicle_exit"


def post_execution_router(state: PharmaIQState) -> str:
    """Always route to CHRONICLE exit after execution."""
    return "chronicle_exit"
