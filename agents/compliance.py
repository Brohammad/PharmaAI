"""
COMPLIANCE – Regulatory Verification Agent (Tier 2 Validation Agent)

No action executes without COMPLIANCE sign-off.

COMPLIANCE is not a yes/no checker. It is a regulatory execution enabler:
  • Verify the action is legally permissible
  • Identify required documentation
  • Generate required documentation automatically where possible
  • Flag regulatory conditions that must be met before execution
  • Identify reporting obligations triggered by the action

Verdicts: COMPLIANT | CONDITIONALLY_COMPLIANT | NON_COMPLIANT

Temporal mode: Synchronous (blocks execution until verdict issued).
"""

from __future__ import annotations

import json
import re
import uuid
from enum import Enum
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from graph.state import PharmaIQState, ComplianceVerdict
from tools.mcp.regulatory_kb import RegulatoryKBMCPServer
from utils.logger import get_logger

logger = get_logger("agent.compliance")


class ComplianceOutcome(str, Enum):
    COMPLIANT = "COMPLIANT"
    CONDITIONALLY_COMPLIANT = "CONDITIONALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"


from prompts.compliance import COMPLIANCE_SYSTEM_PROMPT  # noqa: E402


class ComplianceAgent:
    """
    LangGraph node for COMPLIANCE regulatory verification.
    Runs after CRITIQUE. Checks every VALIDATED/DOWNGRADED proposal.
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model_validation
        self._temperature = 0.05  # Near-zero — compliance reasoning must be deterministic
        self._reg_kb = RegulatoryKBMCPServer()

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """LangGraph node entry point. Verifies all VALIDATED/DOWNGRADED proposals."""
        if not state.route_to_compliance:
            return state

        logger.info(
            "compliance_running",
            store_id=state.store_id,
            critique_verdicts=len(state.critique_verdicts),
        )

        # Build the set of proposals that passed CRITIQUE
        passed_proposals = {v.proposal_id for v in state.critique_verdicts
                            if v.outcome in ("VALIDATED", "DOWNGRADED")}

        new_verdicts: list[ComplianceVerdict] = list(state.compliance_verdicts)

        # ── Verify cold chain quarantine actions ───────────────────────────────
        for alert in state.cold_chain_alerts:
            if alert.alert_id not in passed_proposals:
                continue
            verdict = await self._verify_cold_chain_action(alert, state)
            new_verdicts.append(verdict)

        # ── Verify procurement recommendations ────────────────────────────────
        for forecast in state.demand_forecasts:
            forecast_id = getattr(forecast, "forecast_id", None)
            if not forecast_id or forecast_id not in passed_proposals:
                continue
            verdict = await self._verify_procurement_action(forecast, state)
            new_verdicts.append(verdict)

        # ── Verify staffing schedule changes ──────────────────────────────────
        for gap in state.compliance_gaps:
            verdict = await self._verify_staffing_action(gap, state)
            new_verdicts.append(verdict)

        # ── Verify expiry interventions ────────────────────────────────────────
        for item in state.expiry_risk_items:
            item_id = f"{item.store_id}_{item.batch_id}"
            if item_id not in passed_proposals:
                continue
            verdict = await self._verify_expiry_intervention(item, state)
            new_verdicts.append(verdict)

        logger.info(
            "compliance_complete",
            total_verdicts=len(new_verdicts),
            compliant=sum(1 for v in new_verdicts if v.outcome == ComplianceOutcome.COMPLIANT),
            conditional=sum(1 for v in new_verdicts if v.outcome == ComplianceOutcome.CONDITIONALLY_COMPLIANT),
            non_compliant=sum(1 for v in new_verdicts if v.outcome == ComplianceOutcome.NON_COMPLIANT),
        )

        return state.model_copy(update={
            "compliance_verdicts": new_verdicts,
            "route_to_nexus": True,
            "route_to_compliance": False,
        })

    async def _verify_cold_chain_action(
        self, alert: Any, state: PharmaIQState
    ) -> ComplianceVerdict:
        # Fetch regulatory rules from KB
        try:
            kb_result = await self._reg_kb.check_action_compliance(
                action_type="cold_chain_quarantine",
                drug_ids=alert.batch_ids,
                parameters={"excursion_type": alert.excursion_type},
            )
            kb_context = json.dumps(kb_result.__dict__ if hasattr(kb_result, "__dict__") else kb_result)
        except Exception as exc:
            logger.error("compliance_kb_failed", error=str(exc))
            kb_context = "REGULATORY_KB UNAVAILABLE — failing closed"

        prompt = f"""
COLD CHAIN QUARANTINE COMPLIANCE VERIFICATION

Alert ID: {alert.alert_id}
Store: {alert.store_id}
Excursion Type: {alert.excursion_type}
Affected Batch IDs: {alert.batch_ids}
Drug Profiles: {alert.drug_profiles}

REGULATORY KB RESPONSE:
{kb_context}

Verify this quarantine action for:
1. CDSCO GDP documentation requirements
2. Batch dispensing record requirements
3. Patient notification obligations
4. Required regulatory reporting
5. Auto-generate CDSCO Form QA-2 template if SEVERE/FREEZE
"""
        return await self._invoke_compliance(
            prompt, alert.alert_id, "cold_chain_quarantine", "SENTINEL"
        )

    async def _verify_procurement_action(
        self, forecast: Any, state: PharmaIQState
    ) -> ComplianceVerdict:
        sku_id = getattr(forecast, "sku_id", "UNKNOWN")
        order_qty = getattr(forecast, "recommended_order_qty", 0)
        unit_price = getattr(forecast, "unit_price_estimated", 0.0)
        total_value = order_qty * unit_price

        try:
            kb_result = await self._reg_kb.check_action_compliance(
                action_type="procurement",
                drug_ids=[sku_id],
                parameters={"quantity": order_qty, "estimated_value": total_value},
            )
            kb_context = json.dumps(kb_result.__dict__ if hasattr(kb_result, "__dict__") else kb_result)
        except Exception as exc:
            logger.error("compliance_kb_failed", error=str(exc))
            kb_context = "REGULATORY_KB UNAVAILABLE — failing closed"

        prompt = f"""
PROCUREMENT COMPLIANCE VERIFICATION

SKU: {sku_id}
Recommended Order Quantity: {order_qty} units
Estimated Total Value: ₹{total_value:,.2f}

REGULATORY KB RESPONSE:
{kb_context}

Verify this procurement for:
1. Supplier license validity (DML + Storage License)
2. DPCO ceiling price compliance
3. Schedule H/H1/X documentation requirements
4. Quantity justifiability (not front-running)
"""
        return await self._invoke_compliance(
            prompt,
            getattr(forecast, "forecast_id", str(uuid.uuid4())),
            "procurement",
            "PULSE",
        )

    async def _verify_staffing_action(
        self, gap: Any, state: PharmaIQState
    ) -> ComplianceVerdict:
        prompt = f"""
STAFFING SCHEDULE COMPLIANCE VERIFICATION

Store: {gap.store_id}
Gap Type: {gap.gap_type}
Gap Severity: {gap.severity}
Start Time: {gap.start_time}
Recommended Action: {gap.recommended_action}

Verify for:
1. Pharmacist presence maintained at all times (Schedule H compliance)
2. State Shops and Establishments overtime limits
3. Minimum 12-hour rest between shifts
4. Pharmacist registration currency
"""
        return await self._invoke_compliance(
            prompt, gap.store_id, "staffing_schedule", "AEGIS"
        )

    async def _verify_expiry_intervention(
        self, item: Any, state: PharmaIQState
    ) -> ComplianceVerdict:
        prompt = f"""
EXPIRY INTERVENTION COMPLIANCE VERIFICATION

SKU: {item.sku_id} | Batch: {item.batch_id}
Store: {item.store_id}
Days to Expiry: {item.days_to_expiry}
Recommended Intervention: {item.recommended_intervention}

Verify for:
1. Inter-store transfer: GDP documentation (Form 16/16A), cold chain documentation, GST e-way bill
2. Markdown: DPCO ceiling price constraints (cannot markdown below ceiling floor for essential medicines)
3. Return to distributor: regulatory requirements for pharmaceutical returns
4. Batch disposal: CDSCO batch destruction protocols, environmental compliance
"""
        return await self._invoke_compliance(
            prompt,
            f"{item.store_id}_{item.batch_id}",
            "expiry_intervention",
            "MERIDIAN",
        )

    async def _invoke_compliance(
        self,
        prompt: str,
        proposal_id: str,
        action_type: str,
        agent_source: str,
    ) -> ComplianceVerdict:
        """Core LLM invocation for compliance verification."""
        try:
            raw = await _llm_generate(
                model=self._model,
                system_prompt=COMPLIANCE_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=self._temperature,
            )
            raw = raw.strip()
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in COMPLIANCE response")

            outcome_str = data.get("verdict", "CONDITIONALLY_COMPLIANT")
            try:
                outcome = ComplianceOutcome(outcome_str)
            except ValueError:
                outcome = ComplianceOutcome.CONDITIONALLY_COMPLIANT

            return ComplianceVerdict(
                verdict_id=str(uuid.uuid4()),
                proposal_id=proposal_id,
                proposal_type=action_type,
                agent_source=agent_source,
                outcome=outcome,
                documentation_required=data.get("documentation_required", []),
                documentation_generated=data.get("documentation_auto_generated", {}),
                conditions=data.get("conditions", []),
                blocking_issues=data.get("blocking_issues", []),
                reporting_obligations=data.get("reporting_obligations_triggered", []),
                regulatory_basis=data.get("regulatory_basis", []),
                compliance_confidence=data.get("compliance_confidence", 0.8),
                reasoning=data.get("reasoning_chain", ""),
            )

        except Exception as exc:
            logger.error("compliance_llm_failed", error=str(exc), proposal_id=proposal_id)
            # Fail closed: NON_COMPLIANT when uncertain
            return ComplianceVerdict(
                verdict_id=str(uuid.uuid4()),
                proposal_id=proposal_id,
                proposal_type=action_type,
                agent_source=agent_source,
                outcome=ComplianceOutcome.NON_COMPLIANT,
                documentation_required=[],
                documentation_generated={},
                conditions=[],
                blocking_issues=[f"COMPLIANCE engine error: {exc}. Manual review required."],
                reporting_obligations=[],
                regulatory_basis=[],
                compliance_confidence=0.0,
                reasoning="COMPLIANCE LLM invocation failed — failing closed (NON_COMPLIANT).",
            )


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = ComplianceAgent()


async def compliance_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _agent.run(state)
    return {
        "compliance_verdicts": updated.compliance_verdicts,
        "route_to_nexus": updated.route_to_nexus,
        "route_to_compliance": updated.route_to_compliance,
        "messages": updated.messages,
    }
