"""
MCP Server 1 – Cold Chain IoT Server
Real-time pharmaceutical cold chain monitoring and control.
Interfaces with 960 refrigeration units across 320 stores.

Update frequency: every 60 seconds per unit.
Failure mode: sensor offline > 5 minutes → escalate + flag "UNMONITORED".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("mcp.cold_chain")


@dataclass
class FridgeReading:
    store_id: str
    unit_id: str
    temperature_c: float
    humidity_pct: float
    door_open: bool
    power_source: str          # MAINS | BACKUP | UNKNOWN
    timestamp_utc: str
    sensor_status: str         # ONLINE | OFFLINE | DEGRADED


@dataclass
class ExcursionEvent:
    store_id: str
    unit_id: str
    excursion_type: str        # MINOR | MODERATE | SEVERE | FREEZE
    start_utc: str
    end_utc: str | None
    max_temp_c: float
    min_temp_c: float
    duration_minutes: float
    drugs_affected: list[str] = field(default_factory=list)


@dataclass
class BatchFridgeMapping:
    batch_id: str
    drug_name: str
    drug_id: str
    quantity: int
    stability_profile_id: str
    max_excursion_tolerance_minutes: int
    cumulative_excursion_minutes: float


class ColdChainMCPServer:
    """
    Structured interface between the AI reasoning layer and cold chain IoT systems.
    All methods are async and return typed dataclass instances.
    """

    def __init__(self, base_url: str = settings.mcp_cold_chain_url) -> None:
        self._base = base_url.rstrip("/")

    # ── Read tools ─────────────────────────────────────────────────────────────

    async def get_current_readings(
        self, store_id: str, unit_id: str | None = None
    ) -> list[FridgeReading]:
        """
        Returns real-time temperature, humidity, door-open, and power-source
        readings for a store's refrigeration units.
        Latency target: < 2 seconds.
        """
        params: dict[str, Any] = {"store_id": store_id}
        if unit_id:
            params["unit_id"] = unit_id
        raw = await self._get("/readings/current", params)
        return [FridgeReading(**r) for r in raw.get("readings", [])]

    async def get_excursion_history(
        self,
        store_id: str,
        unit_id: str,
        from_utc: str,
        to_utc: str,
    ) -> list[ExcursionEvent]:
        """Returns historical excursion events for a specific fridge unit."""
        raw = await self._get(
            "/excursions",
            {"store_id": store_id, "unit_id": unit_id, "from_utc": from_utc, "to_utc": to_utc},
        )
        return [ExcursionEvent(**e) for e in raw.get("excursions", [])]

    async def get_batch_fridge_mapping(
        self, store_id: str, unit_id: str
    ) -> list[BatchFridgeMapping]:
        """
        Returns all drug batches currently stored in a specific fridge unit
        along with their drug-specific stability profiles.
        """
        raw = await self._get("/batches", {"store_id": store_id, "unit_id": unit_id})
        return [BatchFridgeMapping(**b) for b in raw.get("batches", [])]

    async def get_unit_maintenance_history(self, store_id: str, unit_id: str) -> list[dict[str, Any]]:
        """Returns maintenance log for a fridge unit (service dates, issues found)."""
        raw = await self._get("/maintenance", {"store_id": store_id, "unit_id": unit_id})
        return raw.get("records", [])

    async def get_all_unit_status(self, store_id: str) -> list[dict[str, Any]]:
        """
        Returns aggregated status for every fridge unit in a store:
        risk level, last reading timestamp, sensor status.
        """
        raw = await self._get("/status", {"store_id": store_id})
        return raw.get("units", [])

    # ── Write tools ────────────────────────────────────────────────────────────

    async def trigger_quarantine_lock(
        self,
        store_id: str,
        unit_id: str,
        batch_ids: list[str],
        reason: str,
        authority_level: str,
        decision_id: str,
    ) -> dict[str, Any]:
        """
        Locks specified batches in ERP (blocks dispensing) and flags for review.

        Authority rules:
          AUTO       → severe excursion (dispatched by NEXUS without human gate)
          HUMAN_INFORMED → moderate excursion (executes + notifies)
        """
        payload = {
            "store_id": store_id,
            "unit_id": unit_id,
            "batch_ids": batch_ids,
            "reason": reason,
            "authority_level": authority_level,
            "decision_id": decision_id,
        }
        return await self._post("/quarantine/lock", payload)

    async def log_excursion_event(
        self,
        store_id: str,
        unit_id: str,
        excursion: dict[str, Any],
        pharmacist_on_duty_id: str,
    ) -> dict[str, Any]:
        """
        CDSCO-compliant excursion logging: batch number, timestamp, duration,
        peak temperature, pharmacist signature.
        """
        return await self._post(
            "/excursions/log",
            {"store_id": store_id, "unit_id": unit_id, "excursion": excursion,
             "pharmacist_id": pharmacist_on_duty_id},
        )

    async def create_maintenance_request(
        self,
        store_id: str,
        unit_id: str,
        priority: str,
        notes: str,
        recommend_replacement: bool = False,
    ) -> dict[str, Any]:
        """Submits a maintenance work order via ERP MCP Server."""
        return await self._post(
            "/maintenance/request",
            {"store_id": store_id, "unit_id": unit_id,
             "priority": priority, "notes": notes,
             "recommend_replacement": recommend_replacement},
        )

    # ── Internal HTTP helpers ──────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("mcp_cold_chain_get_failed", path=path, error=str(exc))
            return {}

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.error("mcp_cold_chain_post_failed", path=path, error=str(exc))
            return {"error": str(exc)}
