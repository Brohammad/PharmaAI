"""
MCP Server 6 – Regulatory Knowledge Server (NEW in industry-grade design)
Version-controlled, manually-verified regulatory knowledge base.

Critical distinction from External Intelligence Server:
  - External Intel → data feeds (IDSP, weather, AQI, Google Trends)
  - Regulatory KB  → rules and requirements (laws, standards, protocols)

Regulatory rules are:
  ✓ Version-controlled (every update has a version + effective date)
  ✓ Manually verified before activation (never auto-updated from web scrapes)
  ✓ Auditable (COMPLIANCE agent knows exactly which version was active
    at the time of any decision)
  ✓ Traceable (every action references the specific regulation it satisfies)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("mcp.regulatory_kb")


@dataclass
class RegulatoryRule:
    rule_id: str
    domain: str              # DISPENSING | COLD_CHAIN | STAFFING | PROCUREMENT | STORAGE
    title: str
    description: str
    applicable_states: list[str]   # empty = nationwide
    authority: str           # CDSCO | STATE_FDA | WHO | SHOPS_EST_ACT | D_AND_C_ACT
    version: str
    effective_date: str
    citation: str            # Full legal citation
    action_required: str     # What must be done to comply
    non_compliance_consequence: str


@dataclass
class DrugScheduleInfo:
    drug_name: str
    sku_id: str
    schedule: str            # H | H1 | X | G | C | C1 | OTC
    dispensing_requirements: str
    storage_requirements: str
    record_keeping_required: bool
    pharmacist_presence_required: bool
    prescription_required: bool
    max_dispensing_qty: int | None


@dataclass
class ComplianceCheckResult:
    action_id: str
    is_compliant: bool
    verdict: str             # COMPLIANT | CONDITIONALLY_COMPLIANT | NON_COMPLIANT
    rules_checked: list[str]
    conditions: list[str]    # Steps required before action can proceed
    violations: list[str]
    suggested_compliant_alternative: str | None


class RegulatoryKBMCPServer:
    """
    Interface between the COMPLIANCE agent and the regulatory knowledge base.
    All responses include version metadata for audit trail purposes.
    """

    def __init__(self, base_url: str = settings.mcp_regulatory_kb_url) -> None:
        self._base = base_url.rstrip("/")

    # ── Drug schedule lookups ──────────────────────────────────────────────────

    async def get_drug_schedule(self, drug_id: str) -> DrugScheduleInfo | None:
        """
        Returns full scheduling information for a drug including dispensing,
        storage, and record-keeping requirements.
        """
        raw = await self._get("/drugs/schedule", {"drug_id": drug_id})
        return DrugScheduleInfo(**raw) if raw else None

    async def get_drug_stability_regulatory(self, drug_id: str) -> dict[str, Any]:
        """
        Returns regulatory (WHO/CDSCO) cold chain storage requirements for a drug.
        Distinct from the operational stability profiles in config/drug_stability.py —
        this is the legal minimum standard.
        """
        raw = await self._get("/drugs/cold-chain", {"drug_id": drug_id})
        return raw

    async def check_drug_interaction(
        self,
        drug_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        Returns known drug interaction risks for a combination of drugs.
        Used at dispensing time for Schedule H interaction screening.
        """
        raw = await self._get("/drugs/interactions", {"drug_ids": ",".join(drug_ids)})
        return raw.get("interactions", [])

    async def get_dpco_ceiling_price(self, sku_id: str) -> dict[str, Any]:
        """
        Returns DPCO (Drug Price Control Order) ceiling price for a SKU.
        Procurement actions must not exceed this for price-controlled drugs.
        """
        raw = await self._get("/pricing/dpco", {"sku_id": sku_id})
        return raw

    # ── Regulatory rules ───────────────────────────────────────────────────────

    async def get_regulation(self, rule_id: str) -> RegulatoryRule | None:
        """Fetches a specific regulatory rule by ID."""
        raw = await self._get("/rules/get", {"rule_id": rule_id})
        return RegulatoryRule(**raw) if raw else None

    async def get_regulations_for_domain(
        self,
        domain: str,
        state: str | None = None,
    ) -> list[RegulatoryRule]:
        """Returns all active regulations for a domain, optionally filtered by state."""
        params: dict[str, Any] = {"domain": domain}
        if state:
            params["state"] = state
        raw = await self._get("/rules/domain", params)
        return [RegulatoryRule(**r) for r in raw.get("rules", [])]

    async def check_action_compliance(
        self,
        action_type: str,
        domain: str,
        context: dict[str, Any],
        state: str | None = None,
    ) -> ComplianceCheckResult:
        """
        The primary tool used by the COMPLIANCE agent.
        Evaluates a proposed action against all applicable regulations.
        Returns detailed verdict with conditions and violations.
        """
        payload = {
            "action_type": action_type,
            "domain": domain,
            "context": context,
        }
        if state:
            payload["state"] = state
        raw = await self._post("/compliance/check", payload)
        return ComplianceCheckResult(**raw) if raw else ComplianceCheckResult(
            action_id=context.get("action_id", "unknown"),
            is_compliant=False,
            verdict="NON_COMPLIANT",
            rules_checked=[],
            conditions=[],
            violations=["Regulatory KB server unreachable — defaulting to NON_COMPLIANT for safety"],
            suggested_compliant_alternative=None,
        )

    async def verify_pharmacist_registration(
        self,
        registration_number: str,
        state: str,
    ) -> dict[str, Any]:
        """
        Verifies a pharmacist's registration is active and valid in a given state.
        Queries State Pharmacy Council registry.
        """
        raw = await self._get("/pharmacists/verify", {
            "registration_number": registration_number,
            "state": state,
        })
        return raw

    async def get_recall_compliance_checklist(self, recall_class: str) -> list[str]:
        """
        Returns the CDSCO-mandated step-by-step checklist for a drug recall.
        recall_class: CLASS_I | CLASS_II | CLASS_III
        """
        raw = await self._get("/recalls/checklist", {"class": recall_class})
        return raw.get("steps", [])

    async def get_active_rule_version(self, domain: str) -> dict[str, Any]:
        """
        Returns the currently active version of all rules for a domain.
        Included in audit trail for every COMPLIANCE decision.
        """
        raw = await self._get("/rules/active-version", {"domain": domain})
        return raw

    # ── Internal HTTP helpers ──────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("mcp_regulatory_kb_get_failed", path=path, error=str(exc))
            return {}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.error("mcp_regulatory_kb_post_failed", path=path, error=str(exc))
            return {"error": str(exc)}
