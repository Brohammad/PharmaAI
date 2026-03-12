"""
Action Execution Engine.

The only layer that calls MCP server WRITE operations.
All Tier 1 agents are read-only proposers.
Execution only happens when NEXUS has approved an action.

Each action is:
  1. Looked up in the approved_actions list from NEXUS
  2. Authority level is re-verified (defence-in-depth)
  3. Appropriate MCP write method is called
  4. Outcome is recorded to audit log
  5. Notifications are sent via CommunicationMCP

Actions that arrive here have already passed:
  CRITIQUE (quality validation) + COMPLIANCE (regulatory verification) + NEXUS (authority gate)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from config.authority_matrix import can_auto_execute, get_authority
from graph.state import PharmaIQState
from tools.mcp.cold_chain import ColdChainMCPServer
from tools.mcp.erp import ERPMCPServer
from tools.mcp.hrms import HRMSMCPServer
from tools.mcp.distributor import DistributorMCPServer
from tools.mcp.communication import CommunicationMCPServer
from utils.logger import get_logger, get_audit_logger

logger = get_logger("graph.execution")


class ExecutionEngine:
    """
    Executes NEXUS-approved actions via the appropriate MCP servers.
    Maintains a full execution log for CHRONICLE and regulatory audit.
    """

    def __init__(self) -> None:
        self._cold_chain = ColdChainMCPServer()
        self._erp = ERPMCPServer()
        self._hrms = HRMSMCPServer()
        self._distributor = DistributorMCPServer()
        self._comm = CommunicationMCPServer()
        self._audit = get_audit_logger()

    async def execute(self, state: PharmaIQState) -> PharmaIQState:
        """
        LangGraph node entry point.
        Iterates over nexus_priority_decisions and executes each approved action.
        """
        if not state.route_to_execution:
            return state

        logger.info(
            "execution_start",
            store_id=state.store_id,
            actions_count=len(state.nexus_priority_decisions),
        )

        execution_results: list[dict[str, Any]] = []

        for action in state.nexus_priority_decisions:
            try:
                result = await self._dispatch_action(action, state)
                execution_results.append(result)

                # Send appropriate notification
                await self._notify_action(action, result, state)

                # Record to audit
                await self._audit.update_outcome(
                    decision_id=action.get("audit_decision_id", str(uuid.uuid4())),
                    outcome={
                        "status": result.get("status", "UNKNOWN"),
                        "executed_at": datetime.now(timezone.utc).isoformat(),
                        "mcp_response": result.get("mcp_response", {}),
                    },
                )

            except Exception as exc:
                logger.error(
                    "execution_action_failed",
                    action_id=action.get("id"),
                    action_type=action.get("type"),
                    error=str(exc),
                )
                execution_results.append({
                    "action_id": action.get("id"),
                    "status": "FAILED",
                    "error": str(exc),
                })

        logger.info(
            "execution_complete",
            total=len(execution_results),
            succeeded=sum(1 for r in execution_results if r.get("status") == "SUCCESS"),
            failed=sum(1 for r in execution_results if r.get("status") == "FAILED"),
        )

        return state.model_copy(update={
            "execution_results": execution_results,
            "route_to_execution": False,
        })

    async def _dispatch_action(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        """Route action to correct MCP server method."""
        action_type = action.get("type", "")
        domain = action.get("domain", "")
        action_id = action.get("id", "")

        # Re-verify authority (defence-in-depth)
        if not can_auto_execute(domain, action.get("action", "")):
            logger.warning(
                "execution_authority_recheck_failed",
                action_id=action_id,
                domain=domain,
                action=action.get("action"),
            )
            return {
                "action_id": action_id,
                "status": "BLOCKED_AUTHORITY_RECHECK",
                "reason": "Authority matrix re-check failed at execution gate",
            }

        # ── Cold chain actions ─────────────────────────────────────────────────
        if action_type == "cold_chain_quarantine":
            return await self._execute_quarantine(action, state)

        if action_type == "maintenance_request":
            return await self._execute_maintenance_request(action, state)

        # ── Procurement actions ───────────────────────────────────────────────
        if action_type == "purchase_order":
            return await self._execute_purchase_order(action, state)

        if action_type == "inter_store_transfer":
            return await self._execute_transfer(action, state)

        # ── Staffing actions ──────────────────────────────────────────────────
        if action_type == "schedule_change":
            return await self._execute_schedule_change(action, state)

        # ── Communication actions ─────────────────────────────────────────────
        if action_type == "patient_notification":
            return await self._execute_patient_notification(action, state)

        if action_type == "escalation_notification":
            return await self._execute_escalation(action, state)

        logger.warning("execution_unknown_action_type", action_type=action_type)
        return {
            "action_id": action_id,
            "status": "SKIPPED",
            "reason": f"Unknown action type: {action_type}",
        }

    # ── Action handlers ────────────────────────────────────────────────────────

    async def _execute_quarantine(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        """Execute batch quarantine via ERP + cold chain lock."""
        batch_ids = action.get("batch_ids", [])
        store_id = action.get("store", state.store_id or "")
        reason = action.get("reason", "Cold chain excursion")

        results = []
        for batch_id in batch_ids:
            # Lock fridge unit
            lock_result = await self._cold_chain.trigger_quarantine_lock(
                store_id=store_id,
                unit_id=action.get("unit_id", ""),
                reason=reason,
            )
            # Quarantine in ERP
            erp_result = await self._erp.execute_batch_quarantine(
                store_id=store_id,
                batch_id=batch_id,
                reason=reason,
                reference_id=action.get("id", ""),
            )
            results.append({"batch_id": batch_id, "lock": lock_result, "erp": erp_result})

        return {
            "action_id": action.get("id"),
            "status": "SUCCESS",
            "mcp_response": results,
        }

    async def _execute_maintenance_request(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        result = await self._cold_chain.create_maintenance_request(
            store_id=action.get("store", state.store_id or ""),
            unit_id=action.get("unit_id", ""),
            priority=action.get("priority", "HIGH"),
            description=action.get("description", ""),
        )
        return {"action_id": action.get("id"), "status": "SUCCESS", "mcp_response": result}

    async def _execute_purchase_order(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        result = await self._erp.create_purchase_order(
            store_id=action.get("store", state.store_id or ""),
            sku_id=action.get("sku_id", ""),
            quantity=action.get("quantity", 0),
            distributor_id=action.get("distributor_id", ""),
            reason=action.get("reason", "PULSE demand forecast"),
            urgency=action.get("urgency", "STANDARD"),
        )
        return {"action_id": action.get("id"), "status": "SUCCESS", "mcp_response": result}

    async def _execute_transfer(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        result = await self._erp.initiate_inter_store_transfer(
            from_store_id=action.get("from_store", ""),
            to_store_id=action.get("to_store", ""),
            sku_id=action.get("sku_id", ""),
            batch_id=action.get("batch_id", ""),
            quantity=action.get("quantity", 0),
            cold_chain_required=action.get("cold_chain_required", False),
            reason=action.get("reason", "MERIDIAN expiry optimisation"),
        )
        return {"action_id": action.get("id"), "status": "SUCCESS", "mcp_response": result}

    async def _execute_schedule_change(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        result = await self._hrms.apply_schedule_change(
            store_id=action.get("store", state.store_id or ""),
            staff_id=action.get("staff_id", ""),
            shift_date=action.get("shift_date", ""),
            shift_start=action.get("shift_start", ""),
            shift_end=action.get("shift_end", ""),
            reason=action.get("reason", "AEGIS schedule optimisation"),
        )
        return {"action_id": action.get("id"), "status": "SUCCESS", "mcp_response": result}

    async def _execute_patient_notification(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        result = await self._comm.send_patient_notification(
            patient_ids=action.get("patient_ids", []),
            notification_type=action.get("notification_type", "COLD_CHAIN_ADVISORY"),
            message=action.get("message", ""),
            batch_ids=action.get("batch_ids", []),
        )
        return {"action_id": action.get("id"), "status": "SUCCESS", "mcp_response": result}

    async def _execute_escalation(
        self, action: dict[str, Any], state: PharmaIQState
    ) -> dict[str, Any]:
        result = await self._comm.trigger_escalation(
            escalation_id=action.get("escalation_id", str(uuid.uuid4())),
            urgency=action.get("urgency", "URGENT"),
            summary=action.get("summary", ""),
            details=action.get("details", {}),
            requires_ack=action.get("requires_ack", True),
        )
        return {"action_id": action.get("id"), "status": "SUCCESS", "mcp_response": result}

    async def _notify_action(
        self,
        action: dict[str, Any],
        result: dict[str, Any],
        state: PharmaIQState,
    ) -> None:
        """Send status notification for executed action."""
        try:
            urgency = "INFORMATIONAL"
            if action.get("type") == "cold_chain_quarantine":
                urgency = "CRITICAL"
            elif action.get("type") in ("staffing_action", "purchase_order"):
                urgency = "IMPORTANT"

            await self._comm.send_notification(
                recipients=["operations@medchain.in"],
                channels=["email", "dashboard"],
                urgency=urgency,
                subject=f"PharmaIQ Action Executed: {action.get('type', 'Unknown')}",
                body=(
                    f"Action {action.get('id', '')} has been executed automatically by PharmaIQ.\n"
                    f"Store: {action.get('store', state.store_id)}\n"
                    f"Status: {result.get('status')}\n"
                    f"Domain: {action.get('domain')}"
                ),
            )
        except Exception as exc:
            logger.warning("execution_notify_failed", error=str(exc))


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_engine = ExecutionEngine()


async def execution_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _engine.execute(state)
    return {
        "execution_results": getattr(updated, "execution_results", []),
        "route_to_execution": updated.route_to_execution,
        "messages": updated.messages,
    }
