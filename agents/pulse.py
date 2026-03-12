"""
PULSE – Demand and Epidemic Intelligence Agent (Tier 1 Operational Agent)

Sole responsibility: Anticipating demand changes across the store network by
fusing internal sales signals, epidemiological intelligence, environmental data,
and market dynamics.

PULSE produces scenario-weighted forecasts with explicit confidence scoring.
It does NOT produce point estimates.

Temporal mode: Predictive / forecasting (hours to weeks ahead).
"""

from __future__ import annotations

import uuid
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from graph.state import PharmaIQState, DemandForecast, EpidemicSignal
from tools.mcp.erp import ERPMCPServer
from tools.mcp.external_intel import ExternalIntelMCPServer
from utils.logger import get_logger

logger = get_logger("agent.pulse")

from prompts.pulse import PULSE_SYSTEM_PROMPT  # noqa: E402


class PulseAgent:
    """
    LangGraph node for PULSE demand and epidemic intelligence.
    Called on: scheduled cycles (05:00, 13:00, 22:00), demand anomaly triggers,
    epidemic signal updates, IDSP data refreshes.
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model
        self._erp_mcp = ERPMCPServer()
        self._ext_mcp = ExternalIntelMCPServer()

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """
        LangGraph node entry point.
        Generates scenario-weighted demand forecasts and epidemic signals.
        """
        store_id = state.store_id
        zone_id = state.zone_id

        if not store_id or not zone_id:
            logger.warning("pulse_missing_context", store_id=store_id, zone_id=zone_id)
            return state

        logger.info("pulse_running", store_id=store_id, zone_id=zone_id, cycle=state.cycle_type)

        # ── 1. Gather all signal layers ────────────────────────────────────────
        internal_signals = await self._gather_internal_signals(store_id)
        environmental_signals = await self._gather_environmental_signals(store_id, zone_id)
        epi_signals = await self._gather_epidemiological_signals(store_id, zone_id)
        market_signals = await self._gather_market_signals(zone_id)

        # ── 2. Inject CHRONICLE context if available ───────────────────────────
        chronicle_ctx = ""
        if state.chronicle_context:
            chronicle_ctx = self._format_chronicle_context(state.chronicle_context)

        # ── 3. Build Gemini prompt ─────────────────────────────────────────────
        prompt = self._build_forecast_prompt(
            store_id=store_id,
            zone_id=zone_id,
            cycle_type=state.cycle_type or "SCHEDULED",
            internal_signals=internal_signals,
            environmental_signals=environmental_signals,
            epi_signals=epi_signals,
            market_signals=market_signals,
            chronicle_context=chronicle_ctx,
            current_epidemic_signals=state.epidemic_signals,
        )

        # ── 4. Invoke Gemini ───────────────────────────────────────────────────
        response_text = await _llm_generate(
            model=self._model,
            system_prompt=PULSE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        logger.info("pulse_forecast_generated", store_id=store_id, zone_id=zone_id)

        # ── 5. Update state ────────────────────────────────────────────────────
        # In production, the response JSON is parsed into typed objects.
        # Here we store the raw LLM output and set routing signals.
        updated_demand_anomalies = list(state.demand_anomalies)
        if internal_signals.get("anomaly_detected"):
            updated_demand_anomalies.append({
                "signal_id": str(uuid.uuid4()),
                "store_id": store_id,
                "zone_id": zone_id,
                "anomaly_type": internal_signals.get("anomaly_type", "DEMAND_SPIKE"),
                "magnitude": internal_signals.get("anomaly_magnitude", 0.0),
                "timestamp_utc": state.timestamp_utc,
                "pulse_assessment": response_text,
            })

        return state.model_copy(update={
            "demand_anomalies": updated_demand_anomalies,
            "route_to_critique": True,   # All PULSE outputs go through CRITIQUE
        })

    async def _gather_internal_signals(self, store_id: str) -> dict[str, Any]:
        """Layer 1: MedChain's own POS data — fastest and most reliable signal."""
        try:
            # In production: fetch top SKUs velocity + detect anomalies
            # Using placeholder structure matching the real data contract
            return {
                "store_id": store_id,
                "anomaly_detected": False,
                "anomaly_type": None,
                "anomaly_magnitude": 0.0,
                "top_movers": [],
                "prescription_upload_rate": 0.0,
            }
        except Exception as exc:
            logger.warning("pulse_internal_signals_failed", error=str(exc))
            return {"store_id": store_id, "anomaly_detected": False}

    async def _gather_environmental_signals(self, store_id: str, zone_id: str) -> dict[str, Any]:
        """Layer 2: IMD weather + CPCB AQI."""
        try:
            # AQI > 300 = 2.5x respiratory demand historically
            aqi_reading = await self._ext_mcp.get_air_quality(city=zone_id)
            return {
                "aqi": aqi_reading.aqi if aqi_reading else None,
                "aqi_risk_level": aqi_reading.respiratory_risk_level if aqi_reading else "UNKNOWN",
                "weather_forecasts": [],
            }
        except Exception as exc:
            logger.warning("pulse_env_signals_failed", error=str(exc))
            return {"aqi": None, "aqi_risk_level": "UNKNOWN"}

    async def _gather_epidemiological_signals(self, store_id: str, zone_id: str) -> dict[str, Any]:
        """Layer 3: IDSP + WHO + Google Trends."""
        try:
            disease_reports = await self._ext_mcp.get_disease_surveillance(
                district=zone_id, state="Delhi"  # In production: from store metadata
            )
            return {
                "disease_reports": [r.__dict__ for r in disease_reports],
                "data_freshness_days": min(
                    (r.data_freshness_days for r in disease_reports), default=999
                ),
            }
        except Exception as exc:
            logger.warning("pulse_epi_signals_failed", error=str(exc))
            return {"disease_reports": [], "data_freshness_days": 999}

    async def _gather_market_signals(self, zone_id: str) -> dict[str, Any]:
        """Layer 4: Generic launches, competitor signals, doctor mix changes."""
        try:
            competitor_signals = await self._ext_mcp.get_competitor_signals(zone_id=zone_id)
            return {"competitor_signals": competitor_signals, "generic_launches": []}
        except Exception as exc:
            logger.warning("pulse_market_signals_failed", error=str(exc))
            return {"competitor_signals": [], "generic_launches": []}

    def _format_chronicle_context(self, ctx: Any) -> str:
        patterns = ctx.relevant_patterns or []
        adjustments = ctx.calibration_adjustments or {}
        return f"""
CHRONICLE INSTITUTIONAL MEMORY (inject into this forecast):
Relevant historical patterns:
{chr(10).join(f"  • {p}" for p in patterns[:5])}

Calibration adjustments:
{chr(10).join(f"  • {k}: {v:+.1%}" for k, v in adjustments.items())}

Recent forecast accuracy (MAPE): {ctx.recent_accuracy_metrics.get('mape', 'N/A')}
"""

    def _build_forecast_prompt(
        self,
        store_id: str,
        zone_id: str,
        cycle_type: str,
        internal_signals: dict[str, Any],
        environmental_signals: dict[str, Any],
        epi_signals: dict[str, Any],
        market_signals: dict[str, Any],
        chronicle_context: str,
        current_epidemic_signals: list[Any],
    ) -> str:
        active_epis = [s.disease for s in current_epidemic_signals if s.status == "ACTIVE"]
        return f"""
DEMAND FORECAST REQUEST

Store: {store_id} | Zone: {zone_id} | Cycle: {cycle_type}

{chronicle_context}

SIGNAL LAYER 1 — INTERNAL (MedChain POS, Real-time):
Anomaly Detected: {internal_signals.get('anomaly_detected')}
Anomaly Type: {internal_signals.get('anomaly_type', 'None')}
Magnitude: {internal_signals.get('anomaly_magnitude', 0):.1%}

SIGNAL LAYER 2 — ENVIRONMENTAL:
AQI: {environmental_signals.get('aqi', 'N/A')} ({environmental_signals.get('aqi_risk_level', 'UNKNOWN')})
Weather health risk indicators: {environmental_signals.get('weather_health_risks', 'N/A')}

SIGNAL LAYER 3 — EPIDEMIOLOGICAL (IDSP + WHO):
Disease reports ({epi_signals.get('data_freshness_days', 'N/A')} days old): 
{len(epi_signals.get('disease_reports', []))} districts reporting

Current active epidemic signals in system: {active_epis or 'None'}

SIGNAL LAYER 4 — MARKET:
Competitor signals: {len(market_signals.get('competitor_signals', []))} in zone
Generic launches: {len(market_signals.get('generic_launches', []))} recent

Please produce:
1. Scenario-weighted 7-day demand forecasts for the top 50 SKUs most likely affected
2. Epidemic signal assessment (disease, probability, confidence, lead-time estimate)
3. Procurement recommendations with multipliers and confidence thresholds
4. Staffing implications for AEGIS
5. Cold chain capacity implications for SENTINEL
6. Explicit data quality notes (especially for IDSP freshness)
7. Recheck triggers for each forecast
"""


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = PulseAgent()


async def pulse_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _agent.run(state)
    return {
        "demand_forecasts": updated.demand_forecasts,
        "epidemic_signals": updated.epidemic_signals,
        "demand_anomalies": updated.demand_anomalies,
        "epidemic_confidence": updated.epidemic_confidence,
        "route_to_critique": updated.route_to_critique,
        "messages": updated.messages,
    }
