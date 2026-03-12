"""
MCP Server 3 – HRMS Server
Staff scheduling, compliance tracking, and workforce optimisation.
Connects to MedChain's Zoho People + custom scheduling module.

Hard constraints (never relaxed):
  - Registered pharmacist (D.Pharm / B.Pharm) present during ALL operating hours
  - Max consecutive shift: 9 hours (per Shops & Establishments Act)
  - Min rest between shifts: 12 hours
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("mcp.hrms")


@dataclass
class StaffMember:
    staff_id: str
    name: str
    role: str                  # PHARMACIST | TECH | CASHIER | MANAGER
    certification: str         # D_PHARM | B_PHARM | PHARM_D | NONE
    registration_number: str | None
    registration_expiry: str | None
    experience_months: int
    languages: list[str]
    cold_chain_trained: bool
    schedule_h_eligible: bool
    current_store_id: str
    accumulated_hours_this_week: float
    overtime_remaining_hours: float


@dataclass
class ShiftSlot:
    staff_id: str
    store_id: str
    date: str
    shift_start: str           # ISO datetime
    shift_end: str
    role: str
    is_pharmacist: bool
    is_schedule_h_eligible: bool
    overtime: bool


@dataclass
class ComplianceStatus:
    store_id: str
    timestamp_utc: str
    pharmacist_present: bool
    schedule_h_eligible: bool
    gap_start_utc: str | None
    gap_duration_minutes: float
    risk_level: str            # NONE | LOW | MEDIUM | HIGH | CRITICAL


class HRMSMCPServer:
    """
    Interface between the AI reasoning layer and MedChain's HRMS.
    """

    def __init__(self, base_url: str = settings.mcp_hrms_url) -> None:
        self._base = base_url.rstrip("/")

    # ── Read tools ─────────────────────────────────────────────────────────────

    async def get_staff_roster(
        self,
        store_id: str,
        date_from: str,
        date_to: str,
    ) -> list[ShiftSlot]:
        """Returns the scheduled roster for a store over a date range."""
        raw = await self._get("/roster", {"store_id": store_id, "from": date_from, "to": date_to})
        return [ShiftSlot(**s) for s in raw.get("shifts", [])]

    async def get_pharmacist_pool(
        self,
        zone_id: str,
        date: str,
        certification_required: str | None = None,
        cold_chain_trained: bool = False,
    ) -> list[StaffMember]:
        """
        Returns available pharmacists in a zone on a given date.
        Filters by certification type and cold chain training if required.
        """
        params: dict[str, Any] = {
            "zone_id": zone_id,
            "date": date,
            "cold_chain_trained": cold_chain_trained,
        }
        if certification_required:
            params["certification"] = certification_required
        raw = await self._get("/pharmacists/available", params)
        return [StaffMember(**m) for m in raw.get("pharmacists", [])]

    async def check_compliance_status(
        self,
        store_id: str,
        timestamp_utc: str,
    ) -> ComplianceStatus:
        """
        Returns real-time compliance status: is a registered pharmacist
        physically scheduled and checked-in at this store right now?
        """
        raw = await self._get(
            "/compliance/status",
            {"store_id": store_id, "timestamp": timestamp_utc},
        )
        return ComplianceStatus(**raw) if raw else ComplianceStatus(
            store_id=store_id, timestamp_utc=timestamp_utc,
            pharmacist_present=False, schedule_h_eligible=False,
            gap_start_utc=None, gap_duration_minutes=0.0,
            risk_level="UNKNOWN",
        )

    async def get_leave_forecast(
        self,
        zone_id: str,
        date_from: str,
        date_to: str,
    ) -> list[dict[str, Any]]:
        """Returns approved and pending leave requests with coverage gap flags."""
        raw = await self._get("/leave/forecast", {"zone_id": zone_id, "from": date_from, "to": date_to})
        return raw.get("leave_records", [])

    async def get_workforce_capacity_model(self, zone_id: str, date: str) -> dict[str, Any]:
        """
        Returns the complete workforce capacity model for a zone:
        pharmacist count, total available hours, overtime budget, skill distribution.
        """
        raw = await self._get("/workforce/capacity", {"zone_id": zone_id, "date": date})
        return raw

    async def get_staff_member(self, staff_id: str) -> StaffMember | None:
        """Fetches full profile for a specific staff member."""
        raw = await self._get("/staff/profile", {"staff_id": staff_id})
        return StaffMember(**raw) if raw else None

    # ── Write tools ────────────────────────────────────────────────────────────

    async def propose_schedule_change(
        self,
        store_id: str,
        date: str,
        changes: list[dict[str, Any]],
        reason: str,
        authority_level: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Proposes shift changes to HRMS.
        Returns feasibility assessment + constraint violations + cost delta.
        AUTO authority: non-overtime changes.
        HUMAN_REQUIRED: overtime or cross-zone redeployment.
        """
        return await self._post("/schedule/propose", {
            "store_id": store_id,
            "date": date,
            "changes": changes,
            "reason": reason,
            "authority_level": authority_level,
            "decision_id": decision_id,
        })

    async def apply_schedule_change(
        self,
        proposal_id: str,
        approved_by: str | None = None,
        decision_id: str | None = None,
    ) -> dict[str, Any]:
        """Applies a previously proposed schedule change (after approval if required)."""
        return await self._post("/schedule/apply", {
            "proposal_id": proposal_id,
            "approved_by": approved_by,
            "decision_id": decision_id,
        })

    async def flag_compliance_breach(
        self,
        store_id: str,
        gap_start_utc: str,
        gap_type: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Records a compliance breach in HRMS for audit purposes.
        Triggers notification chain via Communication MCP Server.
        """
        return await self._post("/compliance/breach", {
            "store_id": store_id,
            "gap_start_utc": gap_start_utc,
            "gap_type": gap_type,
            "decision_id": decision_id,
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
            logger.warning("mcp_hrms_get_failed", path=path, error=str(exc))
            return {}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.error("mcp_hrms_post_failed", path=path, error=str(exc))
            return {"error": str(exc)}
