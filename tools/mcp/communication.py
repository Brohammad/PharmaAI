"""
MCP Server 7 – Communication & Notification Server (NEW in industry-grade design)
Structured multi-channel communication routing system.

Urgency taxonomy:
  CRITICAL    → Phone + SMS + App push + Email  (ack required within 15 min)
  URGENT      → SMS + App push + Email          (ack required within 1 hour)
  IMPORTANT   → App push + Email                (review within 4 hours)
  INFORMATIONAL → Email + Dashboard             (review within 24 hours)

Escalation logic:
  CRITICAL unacked after 15 min → re-notify + notify manager
  CRITICAL unacked after 30 min → notify regional head + log escalation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("mcp.communication")


@dataclass
class NotificationRequest:
    notification_id: str
    urgency: str                    # CRITICAL | URGENT | IMPORTANT | INFORMATIONAL
    audience: list[str]             # staff_ids, role_codes, or zone_ids
    subject: str
    body: str
    action_required: str | None     # Plain-language action request
    decision_id: str | None         # Links back to the decision that triggered this
    requires_acknowledgement: bool
    ack_deadline_minutes: int | None


@dataclass
class HumanApprovalRequest:
    approval_id: str
    decision_id: str
    domain: str
    action: str
    agent: str
    context_summary: str            # Executive level (1–2 sentences)
    operational_detail: str         # Operational level (key facts for decision-maker)
    full_audit_trail_url: str       # Link to Level 3 explainability
    options: list[dict[str, Any]]   # [{option_id, label, consequence}]
    recommended_option: str
    deadline_minutes: int


class CommunicationMCPServer:
    """
    Interface between the AI reasoning layer and MedChain's communication systems.
    Handles all outbound notifications, escalations, and human approval requests.
    """

    def __init__(self, base_url: str = settings.mcp_communication_url) -> None:
        self._base = base_url.rstrip("/")

    # ── Notifications ──────────────────────────────────────────────────────────

    async def send_notification(
        self,
        urgency: str,
        audience: list[str],
        subject: str,
        body: str,
        decision_id: str | None = None,
        action_required: str | None = None,
        requires_acknowledgement: bool = False,
        ack_deadline_minutes: int | None = None,
    ) -> dict[str, Any]:
        """
        Routes a notification to the correct audience via the correct channel
        based on urgency level.
        """
        return await self._post("/notify", {
            "urgency": urgency,
            "audience": audience,
            "subject": subject,
            "body": body,
            "decision_id": decision_id,
            "action_required": action_required,
            "requires_acknowledgement": requires_acknowledgement,
            "ack_deadline_minutes": ack_deadline_minutes,
        })

    async def send_cold_chain_alert(
        self,
        store_id: str,
        unit_id: str,
        excursion_type: str,
        affected_batches: list[str],
        recommended_action: str,
        urgency: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Structured cold chain alert to store pharmacist + zone supervisor.
        Includes step-by-step response instructions.
        """
        return await self._post("/alerts/cold-chain", {
            "store_id": store_id,
            "unit_id": unit_id,
            "excursion_type": excursion_type,
            "affected_batches": affected_batches,
            "recommended_action": recommended_action,
            "urgency": urgency,
            "decision_id": decision_id,
        })

    async def send_patient_notification(
        self,
        store_id: str,
        batch_id: str,
        drug_name: str,
        notification_reason: str,
        patient_ids: list[str],
        plain_language_message: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Patient notification for potentially compromised dispensed medication.
        Requires HUMAN_REQUIRED authority before this can be called.
        Plain language — no technical jargon.
        """
        return await self._post("/notify/patients", {
            "store_id": store_id,
            "batch_id": batch_id,
            "drug_name": drug_name,
            "reason": notification_reason,
            "patient_ids": patient_ids,
            "message": plain_language_message,
            "decision_id": decision_id,
        })

    async def send_schedule_h_compliance_alert(
        self,
        store_id: str,
        gap_start_utc: str,
        gap_type: str,
        urgency: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Sends Schedule H compliance gap alert to store manager + zone compliance officer.
        """
        return await self._post("/alerts/schedule-h", {
            "store_id": store_id,
            "gap_start_utc": gap_start_utc,
            "gap_type": gap_type,
            "urgency": urgency,
            "decision_id": decision_id,
        })

    async def send_epidemic_zone_briefing(
        self,
        zone_ids: list[str],
        disease: str,
        probability: float,
        affected_stores: list[str],
        recommended_actions: list[str],
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Epidemic signal briefing to zone operations managers and national supply chain head.
        """
        return await self._post("/briefings/epidemic", {
            "zone_ids": zone_ids,
            "disease": disease,
            "probability": probability,
            "affected_stores": affected_stores,
            "recommended_actions": recommended_actions,
            "decision_id": decision_id,
        })

    # ── Human-in-the-loop approval ─────────────────────────────────────────────

    async def request_human_approval(
        self,
        decision_id: str,
        domain: str,
        action: str,
        agent: str,
        context_summary: str,
        operational_detail: str,
        full_audit_trail_url: str,
        options: list[dict[str, Any]],
        recommended_option: str,
        deadline_minutes: int,
        approver_audience: list[str],
    ) -> dict[str, Any]:
        """
        Sends an approval request to the designated decision-maker.
        Includes three-level explainability context.
        Returns approval_request_id for tracking.
        """
        return await self._post("/approvals/request", {
            "decision_id": decision_id,
            "domain": domain,
            "action": action,
            "agent": agent,
            "context_summary": context_summary,
            "operational_detail": operational_detail,
            "audit_trail_url": full_audit_trail_url,
            "options": options,
            "recommended_option": recommended_option,
            "deadline_minutes": deadline_minutes,
            "approver_audience": approver_audience,
        })

    async def get_approval_status(self, approval_request_id: str) -> dict[str, Any]:
        """Polls the status of a pending human approval request."""
        raw = await self._get("/approvals/status", {"approval_id": approval_request_id})
        return raw

    async def trigger_escalation(
        self,
        notification_id: str,
        escalation_level: int,    # 1 = manager, 2 = regional head
        reason: str,
    ) -> dict[str, Any]:
        """
        Manually escalates an unacknowledged CRITICAL notification.
        Called by NEXUS when ack deadline is missed.
        """
        return await self._post("/escalate", {
            "notification_id": notification_id,
            "escalation_level": escalation_level,
            "reason": reason,
        })

    # ── Internal HTTP helpers ──────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("mcp_communication_get_failed", path=path, error=str(exc))
            return {}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.error("mcp_communication_post_failed", path=path, error=str(exc))
            return {"error": str(exc)}
