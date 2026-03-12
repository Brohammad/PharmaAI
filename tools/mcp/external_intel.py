"""
MCP Server 5 – External Intelligence Server
Disease surveillance, weather, regulatory, and market intelligence feeds.

Signal sources by latency:
  MedChain POS    → Real-time    (fastest, highest reliability)
  Google Trends   → 1–2 days    (noisy but fast epidemic proxy)
  IMD weather     → Predictive  (high reliability)
  CPCB AQI        → Real-time   (high reliability)
  IDSP            → 7–14 days   (authoritative but slow)
  WHO/CDSCO       → Variable    (authoritative)

Data quality note: IDSP district-level data has known lag and patchy
coverage in several Indian states. Confidence scores reflect this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("mcp.external_intel")


@dataclass
class DiseaseSurveillanceReport:
    district: str
    state: str
    disease: str
    case_count: int
    trend: str              # RISING | STABLE | DECLINING | NEW_OUTBREAK
    alert_level: str        # GREEN | YELLOW | ORANGE | RED
    data_source: str        # IDSP | WHO | STATE_HEALTH_DEPT
    data_freshness_days: int
    reliability: str        # HIGH | MEDIUM | LOW (reflects source quality)


@dataclass
class WeatherForecast:
    city: str
    date: str
    temp_min_c: float
    temp_max_c: float
    humidity_pct: float
    rainfall_probability: float
    severe_weather_alert: bool
    health_risk_indicators: list[str]   # DENGUE_RISK | RESPIRATORY_RISK | GASTRO_RISK etc.


@dataclass
class AirQualityReading:
    city: str
    district: str
    aqi: int
    pm25: float
    pm10: float
    respiratory_risk_level: str  # LOW | MODERATE | HIGH | VERY_HIGH | SEVERE


@dataclass
class DrugRecallNotice:
    recall_id: str
    drug_name: str
    manufacturer: str
    batch_numbers: list[str]
    recall_reason: str
    urgency: str             # CLASS_I | CLASS_II | CLASS_III (I = most severe)
    action_required: str
    compliance_deadline_hours: int
    issued_by: str           # CDSCO | STATE_FDA | WHO
    issued_at_utc: str


class ExternalIntelMCPServer:
    """
    Interface between the AI reasoning layer and external intelligence feeds.
    All responses include data freshness and reliability metadata so
    PULSE and CRITIQUE can properly weight the signals.
    """

    def __init__(self, base_url: str = settings.mcp_external_intel_url) -> None:
        self._base = base_url.rstrip("/")

    # ── Disease surveillance ────────────────────────────────────────────────────

    async def get_disease_surveillance(
        self,
        district: str,
        state: str,
        time_range_days: int = 30,
    ) -> list[DiseaseSurveillanceReport]:
        """
        Returns latest IDSP + state health department disease data.
        Includes data_freshness_days and reliability so agents can
        explicitly weight this in confidence scoring.
        """
        raw = await self._get("/surveillance/disease", {
            "district": district,
            "state": state,
            "days": time_range_days,
        })
        return [DiseaseSurveillanceReport(**r) for r in raw.get("reports", [])]

    async def get_health_search_trends(
        self,
        region: str,
        keywords: list[str],
        time_range_days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Google Trends health search data.
        Fast epidemic proxy signal but noisy — always paired with other sources.
        """
        raw = await self._get("/trends/health", {
            "region": region,
            "keywords": ",".join(keywords),
            "days": time_range_days,
        })
        return raw.get("trends", [])

    # ── Weather & environment ──────────────────────────────────────────────────

    async def get_weather_forecast(
        self,
        city: str,
        days_ahead: int = 7,
    ) -> list[WeatherForecast]:
        """IMD weather forecasts with embedded health risk indicators."""
        raw = await self._get("/weather/forecast", {"city": city, "days": days_ahead})
        return [WeatherForecast(**w) for w in raw.get("forecasts", [])]

    async def get_air_quality(self, city: str, district: str | None = None) -> AirQualityReading | None:
        """CPCB real-time AQI data with respiratory risk classification."""
        params: dict[str, Any] = {"city": city}
        if district:
            params["district"] = district
        raw = await self._get("/environment/aqi", params)
        return AirQualityReading(**raw) if raw else None

    # ── Regulatory intelligence ────────────────────────────────────────────────

    async def get_drug_recall_notices(
        self,
        last_checked_utc: str,
    ) -> list[DrugRecallNotice]:
        """
        Returns all CDSCO and state FDA drug recall notices since last_checked_utc.
        Recall compliance action (shelf removal) must complete within 2 hours for Class I.
        """
        raw = await self._get("/regulatory/recalls", {"since_utc": last_checked_utc})
        return [DrugRecallNotice(**r) for r in raw.get("recalls", [])]

    async def get_who_outbreak_alerts(self) -> list[dict[str, Any]]:
        """Returns current WHO Disease Outbreak News relevant to India."""
        raw = await self._get("/regulatory/who-outbreaks", {})
        return raw.get("alerts", [])

    async def get_cdsco_drug_approvals(self, since_utc: str) -> list[dict[str, Any]]:
        """
        Returns recent CDSCO drug approvals including generic launches.
        Used by PULSE to track brand cannibalisation curves.
        """
        raw = await self._get("/regulatory/cdsco-approvals", {"since_utc": since_utc})
        return raw.get("approvals", [])

    # ── Market intelligence ────────────────────────────────────────────────────

    async def get_competitor_signals(self, zone_id: str) -> list[dict[str, Any]]:
        """
        Returns known competitor store openings/closures in a zone.
        Affects addressable patient base calculations.
        """
        raw = await self._get("/market/competitors", {"zone_id": zone_id})
        return raw.get("signals", [])

    # ── Internal HTTP helpers ──────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("mcp_external_intel_get_failed", path=path, error=str(exc))
            return {}
