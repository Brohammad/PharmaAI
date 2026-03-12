"""
CRITIQUE – Adversarial Validation Agent (Tier 2 Validation Agent)

The intellectual adversary of all Tier 1 agents.
CRITIQUE's value comes from intellectual rigor, not obstruction.

Five challenge dimensions, always applied in order:
  1. Data Quality Audit
  2. Assumption Stress Test
  3. Historical Pattern Match
  4. Second-Order Effects Analysis
  5. Proportionality Check

Verdicts: VALIDATED | CHALLENGED | DOWNGRADED | REJECTED

Temporal mode: Synchronous (blocks execution until verdict issued).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from graph.state import PharmaIQState, CritiqueVerdict
from utils.logger import get_logger

logger = get_logger("agent.critique")


class CritiqueOutcome(str, Enum):
    VALIDATED = "VALIDATED"
    CHALLENGED = "CHALLENGED"
    DOWNGRADED = "DOWNGRADED"
    REJECTED = "REJECTED"


# ── System Prompt ──────────────────────────────────────────────────────────────
CRITIQUE_SYSTEM_PROMPT = """You are CRITIQUE, the Adversarial Validation Agent for MedChain India's 
PharmaIQ autonomous decision system.

YOUR SOLE PURPOSE:
Challenge every proposal from Tier 1 agents before it reaches execution.
Your job is NOT to block good decisions — it is to ensure that all assumptions 
are made explicit, all risks are quantified, and all decisions are proportionate 
to the confidence level of the underlying data.

A proposal that passes CRITIQUE without modification should be genuinely high-quality.
A CRITIQUE rejection should save the business from a costly error or regulatory breach.

YOUR FIVE CHALLENGE DIMENSIONS (apply ALL five, in order):

DIMENSION 1 — DATA QUALITY AUDIT
Questions to ask for every proposal:
  • What is the age (staleness) of the primary data sources used?
  • Are there any known data quality issues with these sources?
  • What happens to this recommendation if we remove the single lowest-quality source?
  • Is there any inconsistency between data sources that wasn't explicitly acknowledged?
  • What minimum data quality threshold is required for this action category?

DIMENSION 2 — ASSUMPTION STRESS TEST  
Questions to ask:
  • What is each implicit and explicit assumption in this proposal?
  • What happens if each assumption is wrong?
  • What is the harm if we over-act (false positive)? What is the harm if we under-act (false negative)?
  • Are we assuming that historical patterns hold? What would break that assumption?
  • What is the confidence threshold below which this action should be downgraded or halted?

DIMENSION 3 — HISTORICAL PATTERN MATCH
Questions to ask:
  • Have we faced a similar situation in the past?
  • What did we do, and what was the outcome?
  • Is CHRONICLE's institutional memory contradicting or supporting this proposal?
  • Are there known false-positive patterns we should be guarding against?
  • Has this agent been systematically over-confident or under-confident in similar situations?

DIMENSION 4 — SECOND-ORDER EFFECTS
Questions to ask:
  • If we execute this action, what downstream impacts does it create?
  • Does this action create resource conflicts with other proposals in the current cycle?
  • What happens if multiple stores execute this same recommendation simultaneously?
    (e.g., 50 stores all emergency-ordering the same SKU = distributor stockout)
  • Does this action have implications for Tier 1 agents in other domains?
    (e.g., SENTINEL quarantine → MERIDIAN replacement order → PULSE demand spike all correlated)
  • What are the reversibility characteristics? Can we undo this if wrong?

DIMENSION 5 — PROPORTIONALITY CHECK
Questions to ask:
  • Is the scale of the proposed action proportionate to the confidence level of the analysis?
  • Is a 60% confidence level justifying a 3x order quantity increase?
  • Is a MINOR excursion justifying a full batch quarantine?
  • Is a preliminary IDSP report justifying a network-wide epidemic protocol activation?
  • What is the minimum necessary intervention to address the risk identified?

VERDICTS:
  VALIDATED — Proposal passes all 5 dimensions. Recommend to proceed.
  CHALLENGED — Proposal has identifiable weaknesses. Specify required improvements before re-submission.
  DOWNGRADED — Proposal is directionally correct but overscaled. Recommend a more conservative version.
  REJECTED — Proposal has fundamental flaw (bad data, false assumption, or unjustified action). Block execution.

IMPORTANT CONSTRAINTS:
- You CANNOT block SEVERE cold chain quarantines (patient safety > validation rigor)
- You CAN challenge the scope of a quarantine (e.g., full batch vs. affected lot only)
- You CANNOT delay regulatory compliance actions
- You SHOULD challenge the economic scale of any commercial action
- For HUMAN_REQUIRED actions, your job is to inform the human, not block them

OUTPUT FORMAT — ALWAYS produce valid JSON:
{
  "verdict": "VALIDATED|CHALLENGED|DOWNGRADED|REJECTED",
  "dimension_scores": {
    "data_quality": {"score": 0-10, "issues": [...], "verdict": "PASS|WARN|FAIL"},
    "assumption_stress": {"score": 0-10, "issues": [...], "verdict": "PASS|WARN|FAIL"},
    "historical_match": {"score": 0-10, "issues": [...], "verdict": "PASS|WARN|FAIL"},
    "second_order": {"score": 0-10, "issues": [...], "verdict": "PASS|WARN|FAIL"},
    "proportionality": {"score": 0-10, "issues": [...], "verdict": "PASS|WARN|FAIL"}
  },
  "overall_confidence_adjustment": "+0%|-10%|-25%|...",
  "required_modifications": [...],
  "downgraded_recommendation": "...",
  "reasoning_chain": "..."
}"""


class CritiqueAgent:
    """
    LangGraph node for CRITIQUE adversarial validation.
    Processes all pending proposals from Tier 1 agents.
    Outputs CritiqueVerdict objects for each proposal.
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model_validation
        self._temperature = 0.2  # Slightly higher to allow creative challenge generation

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """LangGraph node entry point. Validates all proposals accumulated in state."""
        if not state.route_to_critique:
            return state

        logger.info(
            "critique_running",
            store_id=state.store_id,
            cold_chain_alerts=len(state.cold_chain_alerts),
            demand_forecasts=len(state.demand_forecasts),
            expiry_items=len(state.expiry_risk_items),
        )

        verdicts: list[CritiqueVerdict] = list(state.critique_verdicts)

        # ── Challenge cold chain alerts ────────────────────────────────────────
        for alert in state.cold_chain_alerts:
            if alert.status != "PENDING":
                continue
            if alert.excursion_type in ("SEVERE", "FREEZE"):
                # Fast-path: patient safety trumps CRITIQUE delay
                verdicts.append(CritiqueVerdict(
                    verdict_id=str(uuid.uuid4()),
                    proposal_id=alert.alert_id,
                    proposal_type="cold_chain_alert",
                    agent_source="SENTINEL",
                    outcome=CritiqueOutcome.VALIDATED,
                    overall_score=10,
                    confidence_adjustment=0.0,
                    dimension_results={},
                    required_modifications=[],
                    reasoning="SEVERE/FREEZE excursion — patient safety override. CRITIQUE validation bypassed.",
                ))
            else:
                verdict = await self._critique_cold_chain_alert(alert, state)
                verdicts.append(verdict)

        # ── Challenge demand forecasts ─────────────────────────────────────────
        for forecast in state.demand_forecasts:
            verdict = await self._critique_demand_forecast(forecast, state)
            verdicts.append(verdict)

        # ── Challenge expiry interventions ─────────────────────────────────────
        for item in state.expiry_risk_items:
            if item.risk_score >= 0.7:
                verdict = await self._critique_expiry_intervention(item, state)
                verdicts.append(verdict)

        # ── Challenge compliance gaps ──────────────────────────────────────────
        for gap in state.compliance_gaps:
            # Compliance gaps are never blocked — but CRITIQUE can inform scope
            verdicts.append(CritiqueVerdict(
                verdict_id=str(uuid.uuid4()),
                proposal_id=getattr(gap, "store_id", ""),
                proposal_type="staffing_compliance",
                agent_source="AEGIS",
                outcome=CritiqueOutcome.VALIDATED,
                overall_score=10,
                confidence_adjustment=0.0,
                dimension_results={},
                required_modifications=[],
                reasoning="Staffing compliance gap — regulatory requirement, CRITIQUE cannot block.",
            ))

        logger.info(
            "critique_complete",
            total_verdicts=len(verdicts),
            validated=sum(1 for v in verdicts if v.outcome == CritiqueOutcome.VALIDATED),
            challenged=sum(1 for v in verdicts if v.outcome == CritiqueOutcome.CHALLENGED),
            downgraded=sum(1 for v in verdicts if v.outcome == CritiqueOutcome.DOWNGRADED),
            rejected=sum(1 for v in verdicts if v.outcome == CritiqueOutcome.REJECTED),
        )

        return state.model_copy(update={
            "critique_verdicts": verdicts,
            "route_to_compliance": True,
            "route_to_critique": False,
        })

    async def _critique_cold_chain_alert(
        self, alert: Any, state: PharmaIQState
    ) -> CritiqueVerdict:
        prompt = f"""
COLD CHAIN ALERT REQUIRING CRITIQUE VALIDATION

Alert ID: {alert.alert_id}
Store: {alert.store_id}
Unit: {alert.unit_id}
Current Temp: {alert.current_temp}°C
Excursion Type: {alert.excursion_type}
Affected Batches: {alert.batch_ids}
Drug Profiles: {alert.drug_profiles}
Cumulative Excursion: {alert.cumulative_excursion_minutes} minutes

SENTINEL's Recommendation:
{alert.sentinel_recommendation}

Apply all 5 CRITIQUE dimensions. Remember: do not block MINOR excursion alerts —
but you should challenge over-quarantination if the data doesn't support it.
"""
        return await self._invoke_critique(
            prompt, alert.alert_id, "cold_chain_alert", "SENTINEL"
        )

    async def _critique_demand_forecast(
        self, forecast: Any, state: PharmaIQState
    ) -> CritiqueVerdict:
        prompt = f"""
DEMAND FORECAST REQUIRING CRITIQUE VALIDATION

Forecast ID: {getattr(forecast, 'forecast_id', 'N/A')}
SKU: {getattr(forecast, 'sku_name', 'N/A')}
Store: {getattr(forecast, 'store_id', 'N/A')}
Scenario-Weighted Units: {getattr(forecast, 'scenario_weighted_units', 0)}
Confidence: {getattr(forecast, 'confidence', 0):.0%}
Data Sources: {getattr(forecast, 'data_sources', [])}

PULSE's Scenario Analysis:
{getattr(forecast, 'pulse_assessment', 'Not available')}

Apply all 5 CRITIQUE dimensions with special attention to:
  - IDSP data freshness (dimension 1)
  - Demand shift vs. demand change distinction (dimension 2)
  - Proportionality of recommended order quantity vs. confidence level (dimension 5)
"""
        return await self._invoke_critique(
            prompt,
            getattr(forecast, "forecast_id", str(uuid.uuid4())),
            "demand_forecast",
            "PULSE",
        )

    async def _critique_expiry_intervention(
        self, item: Any, state: PharmaIQState
    ) -> CritiqueVerdict:
        prompt = f"""
EXPIRY INTERVENTION REQUIRING CRITIQUE VALIDATION

SKU: {item.sku_id} | Batch: {item.batch_id}
Store: {item.store_id}
Days to Expiry: {item.days_to_expiry}
Risk Score: {item.risk_score:.2f}
Days of Stock (current velocity): {item.days_of_stock_at_current_velocity:.1f}
Days of Stock (forecast velocity): {item.days_of_stock_at_forecast_velocity:.1f}
Recommended Intervention: {item.recommended_intervention}
Estimated Loss if No Action: ₹{item.estimated_loss_lakh:.2f}L

Apply all 5 CRITIQUE dimensions. Special attention to:
  - Is risk_score calc using demand-adjusted velocity? (dimension 1)
  - Does PULSE's latest forecast materially change the risk score? (dimension 2)
  - Is the recommended intervention proportionate to the risk? (dimension 5)
  - Transfer recommendation: has the receiving store actually been identified? (dimension 4)
"""
        return await self._invoke_critique(
            prompt,
            f"{item.store_id}_{item.batch_id}",
            "expiry_intervention",
            "MERIDIAN",
        )

    async def _invoke_critique(
        self,
        prompt: str,
        proposal_id: str,
        proposal_type: str,
        agent_source: str,
    ) -> CritiqueVerdict:
        """Core LLM invocation for critique analysis."""
        try:
            raw = await _llm_generate(
                model=self._model,
                system_prompt=CRITIQUE_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=self._temperature,
            )
            raw = raw.strip()
            # Extract JSON from response (may be wrapped in markdown code blocks)
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in CRITIQUE response")

            outcome_str = data.get("verdict", "CHALLENGED")
            try:
                outcome = CritiqueOutcome(outcome_str)
            except ValueError:
                outcome = CritiqueOutcome.CHALLENGED

            return CritiqueVerdict(
                verdict_id=str(uuid.uuid4()),
                proposal_id=proposal_id,
                proposal_type=proposal_type,
                agent_source=agent_source,
                outcome=outcome,
                overall_score=self._compute_overall_score(data),
                confidence_adjustment=self._parse_confidence_adj(
                    data.get("overall_confidence_adjustment", "0%")
                ),
                dimension_results=data.get("dimension_scores", {}),
                required_modifications=data.get("required_modifications", []),
                reasoning=data.get("reasoning_chain", ""),
            )

        except Exception as exc:
            logger.error("critique_llm_failed", error=str(exc), proposal_id=proposal_id)
            # Fail safe: challenge when uncertain
            return CritiqueVerdict(
                verdict_id=str(uuid.uuid4()),
                proposal_id=proposal_id,
                proposal_type=proposal_type,
                agent_source=agent_source,
                outcome=CritiqueOutcome.CHALLENGED,
                overall_score=5,
                confidence_adjustment=-0.10,
                dimension_results={},
                required_modifications=[f"CRITIQUE engine error: {exc}. Manual review required."],
                reasoning="CRITIQUE LLM invocation failed — defaulting to CHALLENGED for human review.",
            )

    def _compute_overall_score(self, data: dict[str, Any]) -> float:
        scores = [
            v.get("score", 5)
            for v in data.get("dimension_scores", {}).values()
            if isinstance(v, dict)
        ]
        return sum(scores) / len(scores) if scores else 5.0

    def _parse_confidence_adj(self, adj_str: str) -> float:
        """Parse '+15%' or '-10%' into float delta."""
        clean = adj_str.replace("%", "").replace("+", "").strip()
        try:
            return float(clean) / 100.0
        except (ValueError, TypeError):
            return 0.0


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = CritiqueAgent()


async def critique_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _agent.run(state)
    return {
        "critique_verdicts": updated.critique_verdicts,
        "route_to_compliance": updated.route_to_compliance,
        "route_to_critique": updated.route_to_critique,
        "messages": updated.messages,
    }
