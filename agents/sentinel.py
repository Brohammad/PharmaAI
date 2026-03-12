"""
SENTINEL – Cold Chain Guardian (Tier 1 Operational Agent)

Sole responsibility: Continuous monitoring and protection of temperature-sensitive
pharmaceutical inventory across all MedChain stores.

SENTINEL does NOT execute quarantines directly.
It produces recommendations that flow through CRITIQUE → COMPLIANCE → NEXUS → Execution.

Temporal mode: Real-time reactive (seconds to minutes).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from config.drug_stability import classify_excursion, get_stability_profile, ExcursionType
from graph.state import PharmaIQState, ColdChainAlert
from tools.mcp.cold_chain import ColdChainMCPServer
from tools.mcp.erp import ERPMCPServer
from utils.logger import get_logger

logger = get_logger("agent.sentinel")

from prompts.sentinel import SENTINEL_SYSTEM_PROMPT  # noqa: E402


class SentinelAgent:
    """
    LangGraph node for SENTINEL cold chain monitoring.
    Called on: real-time IoT events, scheduled compliance sweeps, CDSCO recall processing.
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model
        self._cold_chain_mcp = ColdChainMCPServer()
        self._erp_mcp = ERPMCPServer()

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """
        LangGraph node entry point.
        Processes active cold chain signals in the current state.
        Adds ColdChainAlert objects to state.cold_chain_alerts.
        """
        store_id = state.store_id
        if not store_id:
            logger.warning("sentinel_no_store_id")
            return state

        logger.info("sentinel_running", store_id=store_id, cycle=state.cycle_type)

        # ── 1. Fetch all current readings ──────────────────────────────────────
        readings = await self._cold_chain_mcp.get_current_readings(store_id)
        if not readings:
            logger.warning("sentinel_no_readings", store_id=store_id)
            return state

        new_alerts: list[ColdChainAlert] = []

        for reading in readings:
            # Sensor offline check
            if reading.sensor_status in ("OFFLINE", "DEGRADED"):
                alert = self._create_sensor_offline_alert(store_id, reading)
                new_alerts.append(alert)
                continue

            # Only process units with readings outside normal range
            if reading.temperature_c <= settings.cold_chain_normal_max_temp and reading.temperature_c >= 2.0:
                continue

            # ── 2. Fetch batch contents of this fridge unit ────────────────────
            batches = await self._cold_chain_mcp.get_batch_fridge_mapping(
                store_id, reading.unit_id
            )
            if not batches:
                continue

            # ── 3. For each batch, classify the excursion ──────────────────────
            for batch in batches:
                excursion_type = classify_excursion(
                    drug_id=batch.stability_profile_id,
                    current_temp=reading.temperature_c,
                    duration_minutes=0,  # Real-time — duration calculated from history
                    cumulative_excursion_minutes=batch.cumulative_excursion_minutes,
                )

                # ── 4. Build prompt context for Gemini reasoning ───────────────
                prompt_context = self._build_reasoning_prompt(
                    reading=reading.__dict__,
                    batch=batch.__dict__,
                    excursion_type=excursion_type.value,
                    store_id=store_id,
                )

                # ── 5. Call Gemini for nuanced assessment ─────────────────────
                response_text = await _llm_generate(
                    model=self._model,
                    system_prompt=SENTINEL_SYSTEM_PROMPT,
                    user_prompt=prompt_context,
                )

                # ── 6. Build ColdChainAlert from response ──────────────────────
                alert = ColdChainAlert(
                    alert_id=str(uuid.uuid4()),
                    store_id=store_id,
                    unit_id=reading.unit_id,
                    batch_ids=[batch.batch_id],
                    current_temp=reading.temperature_c,
                    trend_c_per_min=0.0,  # Populated from IoT trend data
                    excursion_type=excursion_type.value,
                    drug_profiles=[batch.stability_profile_id],
                    cumulative_excursion_minutes=batch.cumulative_excursion_minutes,
                    sentinel_recommendation=response_text,
                    status="PENDING",
                )
                new_alerts.append(alert)

                logger.info(
                    "sentinel_alert_generated",
                    store_id=store_id,
                    unit_id=reading.unit_id,
                    batch_id=batch.batch_id,
                    excursion_type=excursion_type.value,
                    temp=reading.temperature_c,
                )

        # ── 7. Update state ────────────────────────────────────────────────────
        updated_alerts = state.cold_chain_alerts + new_alerts

        # Compute aggregate risk level
        risk_level = "normal"
        if any(a.excursion_type in ("SEVERE", "FREEZE") for a in updated_alerts):
            risk_level = "critical"
        elif any(a.excursion_type == "MODERATE" for a in updated_alerts):
            risk_level = "elevated"
        elif any(a.excursion_type == "MINOR" for a in updated_alerts):
            risk_level = "watch"

        return state.model_copy(update={
            "cold_chain_alerts": updated_alerts,
            "cold_chain_risk_level": risk_level,
            "route_to_critique": bool(new_alerts),
        })

    def _build_reasoning_prompt(
        self,
        reading: dict[str, Any],
        batch: dict[str, Any],
        excursion_type: str,
        store_id: str,
    ) -> str:
        profile = get_stability_profile(batch.get("stability_profile_id", "default_cold_chain"))
        return f"""
COLD CHAIN EVENT ASSESSMENT REQUIRED

Store: {store_id}
Fridge Unit: {reading.get('unit_id')}
Current Temperature: {reading.get('temperature_c')}°C
Humidity: {reading.get('humidity_pct')}%
Door Status: {'OPEN' if reading.get('door_open') else 'CLOSED'}
Power Source: {reading.get('power_source')}
Sensor Status: {reading.get('sensor_status')}
Timestamp: {reading.get('timestamp_utc')}

AFFECTED BATCH:
Batch ID: {batch.get('batch_id')}
Drug: {batch.get('drug_name')} (Drug ID: {batch.get('drug_id')})
Quantity: {batch.get('quantity')} units
Cumulative Excursion History: {batch.get('cumulative_excursion_minutes')} minutes

DRUG STABILITY PROFILE:
Normal Range: {profile.normal_min_temp}°C – {profile.normal_max_temp}°C
Minor Excursion Tolerance: up to {profile.minor_excursion_max_temp}°C for {profile.minor_excursion_max_minutes} min
Moderate Tolerance: up to {profile.moderate_excursion_max_temp}°C for {profile.moderate_excursion_max_minutes} min
Cumulative Budget: {profile.cumulative_excursion_max_minutes} minutes total
Freeze Sensitive: {profile.freeze_sensitive}
Patient Notification Required if Compromised: {profile.patient_notification_required}

PRELIMINARY EXCURSION CLASSIFICATION: {excursion_type}

Please provide:
1. A refined risk assessment for this batch
2. Specific recommended actions with priority order
3. Patient impact assessment
4. Any data quality concerns
5. Your full reasoning chain
"""

    def _create_sensor_offline_alert(self, store_id: str, reading: Any) -> ColdChainAlert:
        return ColdChainAlert(
            alert_id=str(uuid.uuid4()),
            store_id=store_id,
            unit_id=reading.unit_id,
            batch_ids=[],
            current_temp=0.0,
            trend_c_per_min=0.0,
            excursion_type="SEVERE",  # Absence of signal = potential breach
            drug_profiles=[],
            cumulative_excursion_minutes=0.0,
            sentinel_recommendation=(
                f"Sensor OFFLINE/DEGRADED on unit {reading.unit_id}. "
                "Absence of signal treated as potential excursion per WHO cold chain protocol. "
                "Immediate physical check required. Unit flagged as UNMONITORED."
            ),
            status="PENDING",
        )


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = SentinelAgent()


async def sentinel_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function — returns a partial state dict for graph merging."""
    updated = await _agent.run(state)
    return {
        "cold_chain_alerts": updated.cold_chain_alerts,
        "cold_chain_risk_level": updated.cold_chain_risk_level,
        "route_to_critique": updated.route_to_critique,
        "messages": updated.messages,
    }
