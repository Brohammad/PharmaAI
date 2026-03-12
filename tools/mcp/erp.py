"""
MCP Server 2 – ERP / Inventory Server
Real-time inventory position, batch tracking, and procurement execution.
Connects to MedChain's SAP Business One instance.

Write authority:
  Purchase orders: AUTO if ≤ 2.5x standard reorder; HUMAN_REQUIRED if > 2.5x
  Batch quarantine: aligned with cold chain authority matrix
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("mcp.erp")


@dataclass
class InventoryPosition:
    store_id: str
    sku_id: str
    sku_name: str
    batch_id: str
    quantity: int
    expiry_date: str
    unit_cost_inr: float
    days_of_stock: float
    lifecycle_state: str   # HEALTHY | AT_RISK | INTERVENTION_* | CONDEMNED


@dataclass
class SalesVelocity:
    store_id: str
    sku_id: str
    daily_avg: float
    trend_direction: str   # RISING | STABLE | DECLINING
    volatility_score: float  # 0–1 (higher = more unpredictable)
    time_window_days: int


@dataclass
class PurchaseOrder:
    po_number: str
    store_id: str
    items: list[dict[str, Any]]
    distributor_id: str
    estimated_delivery_utc: str
    total_cost_inr: float
    status: str   # PENDING | CONFIRMED | IN_TRANSIT | DELIVERED


class ERPMCPServer:
    """
    Interface between the AI reasoning layer and MedChain's SAP B1 ERP.
    """

    def __init__(self, base_url: str = settings.mcp_erp_url) -> None:
        self._base = base_url.rstrip("/")

    # ── Read tools ─────────────────────────────────────────────────────────────

    async def get_inventory_position(
        self,
        store_id: str,
        sku_id: str | None = None,
        category: str | None = None,
        include_expiry_data: bool = True,
    ) -> list[InventoryPosition]:
        """Current stock position at a store, optionally filtered by SKU or category."""
        params: dict[str, Any] = {"store_id": store_id, "include_expiry": include_expiry_data}
        if sku_id:
            params["sku_id"] = sku_id
        if category:
            params["category"] = category
        raw = await self._get("/inventory/position", params)
        return [InventoryPosition(**item) for item in raw.get("items", [])]

    async def get_sales_velocity(
        self,
        store_id: str,
        sku_id: str,
        time_window_days: int = 30,
    ) -> SalesVelocity:
        """Returns daily average sales velocity + trend direction for a SKU."""
        raw = await self._get(
            "/inventory/velocity",
            {"store_id": store_id, "sku_id": sku_id, "window_days": time_window_days},
        )
        return SalesVelocity(**raw) if raw else SalesVelocity(
            store_id=store_id, sku_id=sku_id, daily_avg=0.0,
            trend_direction="STABLE", volatility_score=0.5, time_window_days=time_window_days
        )

    async def get_expiry_risk_report(
        self,
        store_id: str | None = None,
        risk_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Returns SKUs where Days-of-Stock / Days-to-Expiry ratio > risk_threshold.
        System-wide scan when store_id is None.
        """
        params: dict[str, Any] = {"risk_threshold": risk_threshold}
        if store_id:
            params["store_id"] = store_id
        raw = await self._get("/inventory/expiry-risk", params)
        return raw.get("items", [])

    async def get_batch_dispensing_records(
        self,
        batch_id: str,
        store_id: str,
    ) -> list[dict[str, Any]]:
        """
        Returns all dispensing records for a batch.
        Used by SENTINEL to assess patient notification requirements.
        """
        raw = await self._get("/dispensing/records", {"batch_id": batch_id, "store_id": store_id})
        return raw.get("records", [])

    async def get_standard_reorder_quantity(self, store_id: str, sku_id: str) -> float:
        """Returns the store's standard reorder quantity for a SKU (used for multiplier checks)."""
        raw = await self._get("/inventory/reorder-qty", {"store_id": store_id, "sku_id": sku_id})
        return float(raw.get("standard_qty", 0))

    # ── Write tools ────────────────────────────────────────────────────────────

    async def create_purchase_order(
        self,
        store_id: str,
        items: list[dict[str, Any]],
        urgency_level: str,
        justification: str,
        authority_level: str,
        decision_id: str,
        preferred_distributor_id: str | None = None,
    ) -> PurchaseOrder | dict[str, Any]:
        """
        Creates a purchase order in SAP B1.
        Authority guard: caller must pass authority_level (AUTO / HUMAN_REQUIRED etc.)
        The ERP server validates this against the multiplier threshold.
        """
        payload = {
            "store_id": store_id,
            "items": items,
            "urgency": urgency_level,
            "justification": justification,
            "authority_level": authority_level,
            "decision_id": decision_id,
        }
        if preferred_distributor_id:
            payload["preferred_distributor"] = preferred_distributor_id
        raw = await self._post("/procurement/order", payload)
        if "po_number" in raw:
            return PurchaseOrder(**raw)
        return raw

    async def execute_batch_quarantine(
        self,
        store_id: str,
        batch_ids: list[str],
        reason_code: str,
        quarantine_type: str,
        authority_level: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Blocks dispensing of specified batches in the ERP system.
        quarantine_type: HOLD | DESTROY | RETURN_TO_DISTRIBUTOR
        """
        return await self._post("/inventory/quarantine", {
            "store_id": store_id,
            "batch_ids": batch_ids,
            "reason_code": reason_code,
            "quarantine_type": quarantine_type,
            "authority_level": authority_level,
            "decision_id": decision_id,
        })

    async def initiate_inter_store_transfer(
        self,
        from_store: str,
        to_store: str,
        items: list[dict[str, Any]],
        reason: str,
        cold_chain_required: bool,
        authority_level: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Creates an inter-store transfer order.
        Cold chain transfers require additional logistics coordination.
        """
        return await self._post("/inventory/transfer", {
            "from_store": from_store,
            "to_store": to_store,
            "items": items,
            "reason": reason,
            "cold_chain_required": cold_chain_required,
            "authority_level": authority_level,
            "decision_id": decision_id,
        })

    async def execute_cdsco_recall_removal(
        self,
        batch_ids: list[str],
        recall_notice_id: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Immediately blocks all matched batches across all stores.
        Used for CDSCO recall compliance (must complete within 2 hours).
        """
        return await self._post("/regulatory/recall-removal", {
            "batch_ids": batch_ids,
            "recall_notice_id": recall_notice_id,
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
            logger.warning("mcp_erp_get_failed", path=path, error=str(exc))
            return {}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.error("mcp_erp_post_failed", path=path, error=str(exc))
            return {"error": str(exc)}
