"""
NEXUS – Cross-Domain Synthesis and Priority Orchestrator (Tier 3 Meta Agent)

The final intelligence layer before execution.
NEXUS sees ALL domains simultaneously — the only agent with full network-wide view.

Three responsibilities:
  1. Resolve cross-domain conflicts (when SENTINEL, PULSE, AEGIS, MERIDIAN have competing claims)
  2. Enforce the authority matrix (auto-execute vs. escalate to human)
  3. Optimise resource allocation at network scale

Priority Hierarchy (inviolable order):
  1. Patient Safety (absolute — never traded off)
  2. Regulatory Compliance (binary — not a negotiation)
  3. Confidence-Weighted Commercial Impact (quantified, time-discounted)
  4. Operational Efficiency (optimise within constraints set above)

Temporal mode: Synchronous per-cycle (finalises before execution).
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from config.authority_matrix import get_authority, AuthorityLevel, can_auto_execute
from graph.state import PharmaIQState, PendingEscalation
from tools.mcp.communication import CommunicationMCPServer
from utils.logger import get_logger, get_audit_logger

logger = get_logger("agent.nexus")

# ── System Prompt ──────────────────────────────────────────────────────────────
NEXUS_SYSTEM_PROMPT = """You are NEXUS, the Cross-Domain Synthesis and Priority Orchestrator for MedChain India.

You are the final intelligence layer before any action reaches execution.
You have visibility across ALL domains simultaneously.
You are the only agent in the system with full network-wide situational awareness.

YOUR THREE RESPONSIBILITIES:

1. CROSS-DOMAIN CONFLICT RESOLUTION
   When multiple Tier 1 agents have competing claims on limited resources, you resolve them.
   Examples:
   - SENTINEL quarantines the only cold storage fridge at a store. MERIDIAN needs that fridge
     for a critical incoming delivery. AEGIS says only one pharmacist is available to manage both.
     → NEXUS determines the optimal sequence and resource allocation.
   - PULSE forecasts an epidemic demanding 300% stock increase at 40 stores.
     The distributor only has capacity for 250% across those stores.
     → NEXUS prioritises stores by patient vulnerability index and allocates scarce supply.
   - AEGIS needs to reassign the only Schedule H pharmacist from Store A to Store B
     during a cold chain emergency requiring patient counselling at Store A.
     → NEXUS resolves which patient need is higher priority.

2. AUTHORITY MATRIX ENFORCEMENT
   After CRITIQUE and COMPLIANCE have validated proposals, NEXUS determines:
   - AUTO: Route directly to execution engine
   - HUMAN_INFORMED: Execute AND notify human simultaneously (human can intervene within window)
   - HUMAN_REQUIRED: Queue for human approval before execution
   - HUMAN_ONLY: Reject automated path entirely, escalate to human decision
   
   Authority thresholds (from settings):
   - Auto order max multiplier: {auto_mult}x
   - Human-informed threshold: {informed_mult}x
   - High-cost threshold: ₹{cost_threshold}L (triggers HUMAN_REQUIRED regardless of category)

3. NETWORK-LEVEL RESOURCE ALLOCATION
   Some decisions that look locally optimal are globally suboptimal:
   - 40 stores all emergency-ordering the same SKU = distributor stockout
     → NEXUS coordinates a network-level order with equitable distribution
   - Cross-store pharmacist reassignment needs zone-level visibility
   - Supply disruption means some stores must accept reduced stock; NEXUS decides which

YOUR PRIORITY HIERARCHY (the hierarchy is inviolable — always apply in this order):
  TIER 1: Patient Safety
    - Cold chain breach potentially affecting dispensed medications
    - Missing pharmacist for Schedule H dispensing
    - Active drug recall notification to patients
    These are NEVER traded off for commercial or efficiency reasons.
  
  TIER 2: Regulatory Compliance
    - Schedule H/H1 pharmacist requirement
    - CDSCO documentation compliance
    - DPCO price ceiling compliance
    These are binary — there is no partial compliance.
  
  TIER 3: Commercial Impact (confidence-weighted, time-discounted)
    - Demand forecast reliability × financial impact × time sensitivity
    - A 95% confident ₹5L impact outranks a 40% confident ₹10L impact
  
  TIER 4: Operational Efficiency
    - Optimise for minimum interventions, minimum cost, maximum throughput
    Only when Tiers 1-3 are fully satisfied.

YOUR ESCALATION STANDARDS:
Escalate to human when:
  - Authority matrix specifies HUMAN_REQUIRED or HUMAN_ONLY
  - Total estimated cost of a single decision cycle exceeds ₹{cost_threshold}L
  - Two Tier 1 agents have directly conflicting recommendations where resolution is ambiguous
  - CRITIQUE issued a REJECTED verdict (human must explicitly override)
  - COMPLIANCE issued NON_COMPLIANT verdict (human must explicitly authorise exception)
  - This is a novel situation with no historical precedent in CHRONICLE

Do NOT escalate when:
  - Decision is clearly within AUTO authority
  - All validations passed (VALIDATED + COMPLIANT)
  - Action is time-critical and delay causes patient risk (SENTINEL severe excursions)

OUTPUT FORMAT:
{{
  "approved_actions": [...],
  "escalated_actions": [...],
  "blocked_actions": [...],
  "resource_conflict_resolutions": [...],
  "network_coordination_actions": [...],
  "priority_explanations": [...],
  "reasoning_chain": "..."
}}"""


class NexusAgent:
    """
    LangGraph node for NEXUS cross-domain synthesis.
    Runs after COMPLIANCE. Final gate before execution or escalation.
    """

    def __init__(self) -> None:
        auto_mult = settings.auto_order_max_multiplier
        informed_mult = settings.human_informed_order_max_multiplier
        cost_threshold = settings.high_cost_action_threshold_lakh

        self._model = settings.gemini_model_synthesis
        self._comm_mcp = CommunicationMCPServer()
        self._audit = get_audit_logger()
        self._system_prompt = NEXUS_SYSTEM_PROMPT.format(
            auto_mult=auto_mult,
            informed_mult=informed_mult,
            cost_threshold=cost_threshold,
        )

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """LangGraph node entry point. Synthesises all validated proposals into execution plan."""
        if not state.route_to_nexus:
            return state

        logger.info(
            "nexus_running",
            store_id=state.store_id,
            zone_id=state.zone_id,
            cycle=state.cycle_type,
        )

        # ── 1. Build full context for synthesis ───────────────────────────────
        prompt = self._build_synthesis_prompt(state)

        # ── 2. Invoke Gemini for cross-domain reasoning ───────────────────────
        response_text = await _llm_generate(
            model=self._model,
            system_prompt=self._system_prompt,
            user_prompt=prompt,
        )

        # ── 3. Parse approved/escalated/blocked actions ───────────────────────
        approved_actions, escalations, blocked = self._parse_nexus_response(
            response_text, state
        )

        # ── 4. Send human approval requests for escalated actions ─────────────
        pending_escalations: list[PendingEscalation] = list(state.pending_escalations)
        for esc in escalations:
            esc_id = str(uuid.uuid4())
            try:
                await self._comm_mcp.request_human_approval(
                    request_id=esc_id,
                    action_type=esc.get("action_type", ""),
                    description=esc.get("description", ""),
                    urgency=esc.get("urgency", "URGENT"),
                    estimated_cost_lakh=esc.get("estimated_cost_lakh", 0.0),
                    deadline_minutes=esc.get("deadline_minutes", 60),
                )
                pending_escalations.append(PendingEscalation(
                    escalation_id=esc_id,
                    action_type=esc.get("action_type", ""),
                    description=esc.get("description", ""),
                    requiring_agent=esc.get("source_agent", "NEXUS"),
                    urgency=esc.get("urgency", "URGENT"),
                    deadline_utc=esc.get("deadline_utc", ""),
                    status="PENDING_HUMAN",
                ))
            except Exception as exc:
                logger.error("nexus_escalation_failed", error=str(exc))

        # ── 5. Audit every NEXUS decision ─────────────────────────────────────
        for action in approved_actions:
            await self._audit_nexus_decision(action, "APPROVED", state)
        for action in blocked:
            await self._audit_nexus_decision(action, "BLOCKED", state)

        logger.info(
            "nexus_complete",
            approved=len(approved_actions),
            escalated=len(escalations),
            blocked=len(blocked),
        )

        return state.model_copy(update={
            "nexus_priority_decisions": approved_actions,
            "pending_escalations": pending_escalations,
            "route_to_execution": bool(approved_actions),
            "route_to_human_escalation": bool(escalations),
            "route_to_nexus": False,
        })

    def _build_synthesis_prompt(self, state: PharmaIQState) -> str:
        # Collect all validated proposals with their verdicts
        critique_map = {v.proposal_id: v for v in state.critique_verdicts}
        compliance_map = {v.proposal_id: v for v in state.compliance_verdicts}

        # Build proposal inventory
        proposals = []

        for alert in state.cold_chain_alerts:
            crit = critique_map.get(alert.alert_id)
            comp = compliance_map.get(alert.alert_id)
            proposals.append({
                "type": "cold_chain_quarantine",
                "id": alert.alert_id,
                "store": alert.store_id,
                "excursion_type": alert.excursion_type,
                "critique": crit.outcome if crit else "NOT_VALIDATED",
                "compliance": comp.outcome if comp else "NOT_VERIFIED",
                "estimated_cost_lakh": 0.0,  # Quarantine cost (batch value)
                "domain": "cold_chain",
                "action": "quarantine" if alert.excursion_type in ("SEVERE", "FREEZE") else "alert",
            })

        for gap in state.compliance_gaps:
            comp = compliance_map.get(gap.store_id)
            proposals.append({
                "type": "staffing_action",
                "id": gap.store_id,
                "store": gap.store_id,
                "severity": gap.severity,
                "critique": "VALIDATED",  # Compliance gaps are always validated
                "compliance": comp.outcome if comp else "NOT_VERIFIED",
                "estimated_cost_lakh": 0.0,
                "domain": "staffing",
                "action": "schedule_change",
            })

        for item in state.expiry_risk_items:
            item_id = f"{item.store_id}_{item.batch_id}"
            crit = critique_map.get(item_id)
            comp = compliance_map.get(item_id)
            proposals.append({
                "type": "expiry_intervention",
                "id": item_id,
                "store": item.store_id,
                "intervention": item.recommended_intervention,
                "risk_score": item.risk_score,
                "critique": crit.outcome if crit else "NOT_VALIDATED",
                "compliance": comp.outcome if comp else "NOT_VERIFIED",
                "estimated_cost_lakh": item.estimated_loss_lakh,
                "domain": "inventory",
                "action": item.recommended_intervention.lower(),
            })

        proposals_json = json.dumps(proposals, indent=2)
        auto_thresh = settings.auto_order_max_multiplier
        cost_thresh = settings.high_cost_action_threshold_lakh

        return f"""
NEXUS CROSS-DOMAIN SYNTHESIS REQUEST

Store: {state.store_id} | Zone: {state.zone_id} | Cycle: {state.cycle_type}

VALIDATED PROPOSALS AWAITING NEXUS DECISION:
{proposals_json}

CURRENT AUTHORITY THRESHOLDS:
- Auto-execute order multiplier limit: {auto_thresh}x
- High-cost action threshold (triggers HUMAN_REQUIRED): ₹{cost_thresh}L
- Total cycle cost so far: ₹{sum(p.get('estimated_cost_lakh', 0) for p in proposals):.2f}L

ACTIVE EPIDEMIC SIGNALS: {len(state.epidemic_signals)} signals
COLD CHAIN RISK LEVEL: {state.cold_chain_risk_level}

CHRONICLE CONTEXT:
{self._format_chronicle(state.chronicle_context)}

For each proposal, determine:
1. Is it within AUTO authority? (criteria: within cost threshold, validated, compliant)
2. Are there resource conflicts between proposals?
3. Are there second-order interactions the Tier 1 agents couldn't see?
4. What is the optimal execution sequence?
5. Which actions should be escalated to human, and with what urgency?
"""

    def _parse_nexus_response(
        self,
        raw_response: str,
        state: PharmaIQState,
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Parse Gemini response into approved/escalated/blocked action lists."""
        try:
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return (
                    data.get("approved_actions", []),
                    data.get("escalated_actions", []),
                    data.get("blocked_actions", []),
                )
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: apply authority matrix directly without LLM parsing
        logger.warning("nexus_parse_failed_using_matrix_fallback")
        approved, escalated, blocked = [], [], []
        for alert in state.cold_chain_alerts:
            authority = get_authority("cold_chain", "quarantine")
            action = {"id": alert.alert_id, "type": "cold_chain_quarantine", "source_agent": "SENTINEL"}
            if can_auto_execute("cold_chain", "quarantine"):
                approved.append(action)
            else:
                escalated.append({**action, "urgency": "URGENT", "deadline_minutes": 30})
        return approved, escalated, blocked

    def _format_chronicle(self, ctx: Any) -> str:
        if not ctx:
            return "No CHRONICLE context available"
        patterns = ctx.relevant_patterns if hasattr(ctx, "relevant_patterns") else []
        return f"Relevant patterns: {patterns[:3]}" if patterns else "No relevant patterns"

    async def _audit_nexus_decision(
        self, action: dict[str, Any], outcome: str, state: PharmaIQState
    ) -> None:
        try:
            await self._audit.record(
                agent="NEXUS",
                event_type="NEXUS_DECISION",
                domain=action.get("domain", ""),
                action=action.get("type", ""),
                authority_level=action.get("authority_level", "AUTO"),
                reasoning_summary=action.get("nexus_rationale", ""),
                data_sources=["state.critique_verdicts", "state.compliance_verdicts"],
                confidence=1.0,
                critique_verdict=action.get("critique_verdict", ""),
                compliance_verdict=action.get("compliance_verdict", ""),
                estimated_cost_lakh=action.get("estimated_cost_lakh", 0.0),
            )
        except Exception as exc:
            logger.error("nexus_audit_failed", error=str(exc))


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = NexusAgent()


async def nexus_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _agent.run(state)
    return {
        "nexus_priority_decisions": updated.nexus_priority_decisions,
        "pending_escalations": updated.pending_escalations,
        "route_to_execution": updated.route_to_execution,
        "route_to_human_escalation": updated.route_to_human_escalation,
        "route_to_nexus": updated.route_to_nexus,
        "messages": updated.messages,
    }
