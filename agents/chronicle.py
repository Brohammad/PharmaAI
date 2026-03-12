"""
CHRONICLE – Institutional Memory and Learning Agent (Tier 3 Meta Agent)

The system's long-term intelligence accumulator.
CHRONICLE transforms individual decisions into organisational wisdom.

Four functions:
  1. Decision Outcome Tracking — connects decisions to real-world results
  2. Pattern Library — extracts reusable patterns from outcome data
  3. Agent Performance Evaluation — calibrates each agent's confidence scores
  4. Contextual Memory Injection — provides relevant historical context to other agents

CHRONICLE runs as the first node in each new cycle (injecting context before any Tier 1 agent
processes signals) AND as the last node (recording outcomes from the completed cycle).

Temporal mode: Background / end-of-cycle.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from graph.state import PharmaIQState, ChronicleContext
from utils.logger import get_logger, get_audit_logger

logger = get_logger("agent.chronicle")

from prompts.chronicle import CHRONICLE_SYSTEM_PROMPT  # noqa: E402


class ChronicleAgent:
    """
    LangGraph node for CHRONICLE institutional memory.
    
    Entry mode (start of cycle): Injects contextual memory into state.
    Exit mode (end of cycle): Records outcomes and updates pattern library.
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model_synthesis
        self._audit = get_audit_logger()

    async def run_entry(self, state: PharmaIQState) -> PharmaIQState:
        """
        CHRONICLE entry mode: Inject contextual memory before Tier 1 agents run.
        Called at the very start of each decision cycle.
        """
        store_id = state.store_id or ""
        zone_id = state.zone_id or ""
        cycle_type = state.cycle_type or "SCHEDULED"

        logger.info("chronicle_entry", store_id=store_id, zone_id=zone_id, cycle=cycle_type)

        prompt = f"""
CONTEXTUAL MEMORY INJECTION REQUEST

Store: {store_id} | Zone: {zone_id}
Cycle Type: {cycle_type}
Timestamp: {state.timestamp_utc}

Retrieve and synthesise the most relevant historical context for this decision cycle.
Filter for: same zone, same season/month, same cycle type, similar active signals.

If this is a MORNING_FORECAST cycle: emphasise demand patterns and data quality notes.
If this is a COMPLIANCE_SWEEP cycle: emphasise regulatory patterns and staffing issues.
If this is an EXPIRY_REVIEW cycle: emphasise seasonal demand adjustments for MERIDIAN.
If this is triggered by COLD_CHAIN_ALERT: emphasise past excursion classifications.
If this is triggered by EPIDEMIC_SIGNAL: emphasise past epidemic demand patterns.

Produce the contextual_memory_for_next_cycle section of your output.
"""

        try:
            response_text = await _llm_generate(
                model=self._model,
                system_prompt=CHRONICLE_SYSTEM_PROMPT,
                user_prompt=prompt,
            )

            ctx = self._parse_chronicle_context(response_text, zone_id, cycle_type)
        except Exception as exc:
            logger.warning("chronicle_entry_failed", error=str(exc))
            ctx = ChronicleContext(
                relevant_patterns=[],
                calibration_adjustments={},
                data_quality_warnings=[f"CHRONICLE unavailable: {exc}"],
                recent_accuracy_metrics={},
            )

        return state.model_copy(update={"chronicle_context": ctx})

    async def run_exit(self, state: PharmaIQState) -> PharmaIQState:
        """
        CHRONICLE exit mode: Record outcomes from the completed cycle.
        Called at the very end of each decision cycle after execution.
        """
        store_id = state.store_id or ""

        logger.info(
            "chronicle_exit",
            store_id=store_id,
            approved_actions=len(state.nexus_priority_decisions),
            escalations=len(state.pending_escalations),
        )

        prompt = self._build_outcome_recording_prompt(state)

        try:
            response_text = await _llm_generate(
                model=self._model,
                system_prompt=CHRONICLE_SYSTEM_PROMPT,
                user_prompt=prompt,
            )

            updates = self._parse_chronicle_exit_response(response_text)

            # Update audit records with CHRONICLE's outcome assessments
            for summary in updates.get("outcome_summaries", []):
                decision_id = summary.get("decision_id")
                outcome = summary.get("outcome")
                if decision_id and outcome:
                    await self._audit.update_outcome(decision_id, outcome)

            logger.info(
                "chronicle_learning_recorded",
                new_patterns=len(updates.get("new_patterns", [])),
                calibration_updates=len(updates.get("calibration_updates", {})),
            )

        except Exception as exc:
            logger.error("chronicle_exit_failed", error=str(exc))

        # Mark cycle complete
        return state.model_copy(update={"cycle_complete": True})

    def _build_outcome_recording_prompt(self, state: PharmaIQState) -> str:
        decisions_summary = []

        for decision in state.nexus_priority_decisions[:10]:
            decisions_summary.append({
                "type": decision.get("type"),
                "id": decision.get("id"),
                "store": decision.get("store"),
                "approved": True,
                "source_agent": decision.get("source_agent"),
            })

        for esc in state.pending_escalations[:5]:
            decisions_summary.append({
                "type": "escalated_action",
                "id": esc.escalation_id,
                "status": esc.status,
                "action_type": esc.action_type,
            })

        return f"""
CYCLE OUTCOME RECORDING REQUEST

Store: {state.store_id} | Zone: {state.zone_id}
Cycle: {state.cycle_type}

DECISIONS MADE THIS CYCLE:
{json.dumps(decisions_summary, indent=2)}

VALIDATION RESULTS:
CRITIQUE verdicts: {[v.outcome for v in state.critique_verdicts]}
COMPLIANCE verdicts: {[v.outcome for v in state.compliance_verdicts]}

COLD CHAIN RISK LEVEL: {state.cold_chain_risk_level}

Please:
1. Record outcome summaries for each decision (marking as UNKNOWN if outcome not yet observable)
2. Extract any new patterns worth adding to the pattern library
3. Compute calibration updates for each agent based on this cycle's evidence
4. Flag any anomalies (unusual critique rejection rates, compliance failures, etc.)
"""

    def _parse_chronicle_context(
        self, raw: str, zone_id: str, cycle_type: str
    ) -> ChronicleContext:
        try:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                mem = data.get("contextual_memory_for_next_cycle", {})
                return ChronicleContext(
                    relevant_patterns=mem.get("relevant_patterns", []),
                    calibration_adjustments=mem.get("calibration_adjustments", {}),
                    data_quality_warnings=mem.get("data_quality_warnings", []),
                    recent_accuracy_metrics=mem.get("recent_accuracy_metrics", {}),
                )
        except (json.JSONDecodeError, AttributeError):
            pass
        return ChronicleContext(
            relevant_patterns=[],
            calibration_adjustments={},
            data_quality_warnings=[],
            recent_accuracy_metrics={},
        )

    def _parse_chronicle_exit_response(self, raw: str) -> dict[str, Any]:
        try:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"outcome_summaries": [], "new_patterns": [], "calibration_updates": {}}


# ── LangGraph node wrappers ────────────────────────────────────────────────────
_agent = ChronicleAgent()


async def chronicle_entry_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node — CHRONICLE entry (start of cycle)."""
    updated = await _agent.run_entry(state)
    return {"chronicle_context": updated.chronicle_context}


async def chronicle_exit_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node — CHRONICLE exit (end of cycle)."""
    updated = await _agent.run_exit(state)
    return {"cycle_complete": updated.cycle_complete}
