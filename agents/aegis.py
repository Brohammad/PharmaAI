"""
AEGIS – Staffing and Compliance Shield (Tier 1 Operational Agent)

Sole responsibility: Ensuring every store is legally compliant with staffing
requirements at all times while optimising workforce deployment.

AEGIS solves a dynamic multi-constraint event-responsive problem — NOT a static
weekly schedule. It re-optimises on trigger events.

Four models maintained simultaneously:
  1. Compliance Model (hard constraints — never relaxed)
  2. Demand-Responsive Model (soft constraints from PULSE forecasts)
  3. Workforce Capacity Model (real-time pharmacist pool state)
  4. Scenario Planning Model (pre-computed contingency schedules)

Temporal mode: Real-time reactive + short-horizon planning (hours to days).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from graph.state import PharmaIQState, StaffingGap
from tools.mcp.hrms import HRMSMCPServer
from tools.mcp.external_intel import ExternalIntelMCPServer
from utils.logger import get_logger

logger = get_logger("agent.aegis")

# ── System Prompt ──────────────────────────────────────────────────────────────
AEGIS_SYSTEM_PROMPT = """You are AEGIS, the Staffing and Compliance Shield Agent for MedChain India's 
pharmacy network of 320 stores across Tier 1 and Tier 2 cities.

YOUR SOLE RESPONSIBILITY:
Ensure every store has a registered pharmacist present at all times (legal requirement).
Optimise workforce deployment to match demand while minimising cost.

YOUR DOMAIN EXPERTISE:
HARD CONSTRAINTS (violations are illegal — never relax these):
- At least one registered pharmacist (D.Pharm or B.Pharm) present during ALL operating hours
- Schedule H and H1 drug dispensing requires pharmacist physical presence at point of sale
- Maximum consecutive shift hours: 9 (Shops and Establishments Act, state-specific)
- Minimum rest between shifts: 12 hours
- Overtime limits per state-specific Shops and Establishments Act
- Mandatory rest periods and holiday rules vary by state

SOFT CONSTRAINTS (violations are costly but not illegal):
- Pharmacist-to-patient ratio should not exceed 1:25 during peak hours
- Staff with specific language skills should serve stores where that language dominates
- New hires (<90 days) should overlap with experienced staff for ≥60% of shifts
- Staff scheduling preferences and leave requests

DYNAMIC CONSTRAINTS (change based on external conditions):
- PULSE epidemic signal → increase staffing at affected stores (but pharmacist pool is finite)
- SENTINEL cold chain quarantine event → trained pharmacist needed for patient counselling
- CDSCO recall event → patient callback workload at multiple stores simultaneously
- Festival/holiday periods → different operating hours

YOUR FOUR MODELS:
1. Compliance Model: Hard constraints — the optimisation must always satisfy these first
2. Demand-Responsive Model: Translate PULSE demand forecasts into staffing requirements
3. Workforce Capacity Model: Real-time state of every pharmacist (hours, certs, preferences)
4. Scenario Planning Model: Pre-compute contingency schedules for likely disruptions

YOUR DECISION AUTHORITY:
- AUTONOMOUS: Routine schedule optimisation within normal parameters, shift gap notifications
- HUMAN_INFORMED: Schedule changes involving overtime, cross-store reassignments within zone
- HUMAN_REQUIRED: Emergency redeployment across zones, compliance escalation for Schedule H gaps,
  any action affecting >5 stores simultaneously

YOUR OPERATING PRINCIPLES:
1. Regulatory compliance is binary — a store without a registered pharmacist is non-compliant.
2. Optimise staff utilisation (target >80% productive hours). Idle pharmacists = waste.
3. Pre-compute contingency plans. When disruption occurs, activate the plan, don't solve from scratch.
4. PULSE feeds you demand forecasts → translate to staffing needs BEFORE demand materialises.
5. Always check overtime budgets before proposing extra shifts.
6. Staff are humans, not resources. Respect scheduling preferences and leave rights.

OUTPUT FORMAT:
{
  "compliance_status": {...},
  "staffing_gaps": [...],
  "schedule_recommendations": [...],
  "contingency_plans": [...],
  "resource_conflicts": [...],
  "reasoning_chain": "..."
}"""


class AegisAgent:
    """
    LangGraph node for AEGIS staffing and compliance management.
    Called on: scheduled sweeps (every 2 hours), PULSE epidemic signals,
    pharmacist sick-call events, SENTINEL cold chain events.
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model
        self._hrms_mcp = HRMSMCPServer()

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """LangGraph node entry point."""
        store_id = state.store_id
        zone_id = state.zone_id

        if not store_id or not zone_id:
            logger.warning("aegis_missing_context", store_id=store_id, zone_id=zone_id)
            return state

        logger.info("aegis_running", store_id=store_id, zone_id=zone_id, cycle=state.cycle_type)

        now_utc = datetime.now(timezone.utc).isoformat()

        # ── 1. Check current compliance status ────────────────────────────────
        compliance = await self._hrms_mcp.check_compliance_status(store_id, now_utc)

        new_gaps: list[StaffingGap] = list(state.compliance_gaps)

        # ── 2. Flag any active compliance gaps ────────────────────────────────
        if not compliance.pharmacist_present:
            gap = StaffingGap(
                store_id=store_id,
                gap_type="SCHEDULE_H",
                start_time=compliance.gap_start_utc or now_utc,
                end_time="",  # Ongoing
                severity="CRITICAL" if compliance.gap_duration_minutes > 30 else "HIGH",
                recommended_action=(
                    "Deploy nearest available registered pharmacist immediately. "
                    "Suspend Schedule H dispensing until pharmacist on site."
                ),
                aegis_confidence=0.99,
            )
            new_gaps.append(gap)
            logger.error(
                "aegis_schedule_h_gap",
                store_id=store_id,
                duration_min=compliance.gap_duration_minutes,
            )

        # ── 3. Demand-responsive staffing assessment ───────────────────────────
        epidemic_signals = state.epidemic_signals
        demand_forecasts = state.demand_forecasts

        prompt = self._build_staffing_prompt(
            store_id=store_id,
            zone_id=zone_id,
            compliance_status=compliance.__dict__,
            epidemic_signals=[s.__dict__ for s in epidemic_signals[:3]],
            demand_forecasts=[f.__dict__ for f in demand_forecasts[:5]],
            cold_chain_risk=state.cold_chain_risk_level,
            chronicle_context=state.chronicle_context,
        )

        response_text = await _llm_generate(
            model=self._model,
            system_prompt=AEGIS_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        logger.info("aegis_assessment_complete", store_id=store_id)

        return state.model_copy(update={
            "compliance_gaps": new_gaps,
            "schedule_status": {
                "store_id": store_id,
                "pharmacist_present": compliance.pharmacist_present,
                "schedule_h_eligible": compliance.schedule_h_eligible,
                "risk_level": compliance.risk_level,
                "aegis_assessment": response_text,
            },
            "route_to_critique": True,
        })

    def _build_staffing_prompt(
        self,
        store_id: str,
        zone_id: str,
        compliance_status: dict[str, Any],
        epidemic_signals: list[dict[str, Any]],
        demand_forecasts: list[dict[str, Any]],
        cold_chain_risk: str,
        chronicle_context: Any,
    ) -> str:
        return f"""
STAFFING OPTIMISATION REQUEST

Store: {store_id} | Zone: {zone_id}

CURRENT COMPLIANCE STATUS:
Pharmacist Present: {compliance_status.get('pharmacist_present')}
Schedule H Eligible: {compliance_status.get('schedule_h_eligible')}
Gap Duration: {compliance_status.get('gap_duration_minutes', 0):.0f} minutes
Risk Level: {compliance_status.get('risk_level')}

ACTIVE EPIDEMIC SIGNALS (from PULSE):
{self._format_signals(epidemic_signals)}

DEMAND FORECAST IMPLICATIONS:
{self._format_forecasts(demand_forecasts)}

COLD CHAIN RISK LEVEL (from SENTINEL): {cold_chain_risk}
(If elevated/critical → trained pharmacist needed for patient counselling)

Please provide:
1. Immediate compliance status assessment and any urgent actions required
2. Schedule optimisation recommendations for the next 48 hours
3. Pre-computed contingency plans for: sick-call, epidemic spike, CDSCO recall
4. Resource conflict identification (if pharmacist pool is insufficient for all demands)
5. Any requests for NEXUS to resolve cross-domain resource conflicts
"""

    def _format_signals(self, signals: list[dict[str, Any]]) -> str:
        if not signals:
            return "None active"
        return "\n".join(
            f"  • {s.get('disease', 'Unknown')}: {s.get('probability', 0):.0%} probability, "
            f"{s.get('expected_demand_multiplier', 1.0):.1f}x demand, {s.get('lead_time_days', 0)} days"
            for s in signals
        )

    def _format_forecasts(self, forecasts: list[dict[str, Any]]) -> str:
        if not forecasts:
            return "No active forecasts"
        return "\n".join(
            f"  • {f.get('sku_name', 'Unknown')}: {f.get('scenario_weighted_units', 0):.0f} units "
            f"(confidence: {f.get('confidence', 0):.0%})"
            for f in forecasts[:5]
        )


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = AegisAgent()


async def aegis_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _agent.run(state)
    return {
        "compliance_gaps": updated.compliance_gaps,
        "schedule_status": updated.schedule_status,
        "staffing_recommendations": updated.staffing_recommendations,
        "route_to_critique": updated.route_to_critique,
        "messages": updated.messages,
    }
