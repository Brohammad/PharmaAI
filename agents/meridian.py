"""
MERIDIAN – Expiry and Inventory Lifecycle Agent (Tier 1 Operational Agent)

Sole responsibility: Managing the full lifecycle of every SKU in every store —
from procurement signal to final disposition — with specific focus on preventing
expiry losses and optimising inventory investment across the network.

Core innovation: Lifecycle State Machine + network-level inter-store transfer optimisation.
Demand-adjusted velocity (from PULSE) not static velocity.

Temporal mode: Continuous monitoring + medium-horizon planning (days to weeks).
"""

from __future__ import annotations

import uuid
from typing import Any

from utils.gemini_client import generate as _llm_generate


from config.settings import settings
from graph.state import PharmaIQState, ExpiryRiskItem, InventoryItem
from tools.mcp.erp import ERPMCPServer
from tools.mcp.distributor import DistributorMCPServer
from utils.logger import get_logger

logger = get_logger("agent.meridian")

# ── Lifecycle states ───────────────────────────────────────────────────────────
LIFECYCLE_STATES = [
    "ORDERED", "IN_TRANSIT", "RECEIVED", "SHELVED",
    "DISPENSING", "MONITORING",
    "HEALTHY",          # will sell through before expiry
    "AT_RISK",          # intervention needed
    "INTERVENTION_TRANSFER",   # being moved to higher-velocity store
    "INTERVENTION_MARKDOWN",   # price reduced to accelerate sales
    "INTERVENTION_RETURN",     # being returned to distributor
    "INTERVENTION_BUNDLED",    # combined with complementary products
    "CONDEMNED",        # expired or quarantined — write-off
]

# ── System Prompt ──────────────────────────────────────────────────────────────
MERIDIAN_SYSTEM_PROMPT = """You are MERIDIAN, the Expiry and Inventory Lifecycle Agent for MedChain India's 
pharmacy network of 320 stores.

YOUR SOLE RESPONSIBILITY:
Prevent inventory write-offs through early detection and network-level optimisation.
Manage the full lifecycle of every drug batch from procurement to final disposition.

YOUR CORE INNOVATION — THE RISK SCORE:
Risk Score = (Days of Stock at Forecast Velocity) / (Days to Expiry)

  Risk Score > 0.7 → Flag for attention
  Risk Score > 0.9 → Flag for immediate action (transfer / markdown / return)
  Risk Score > 1.0 → Guaranteed write-off without intervention

CRITICAL: Use PULSE's scenario-weighted forecast velocity, NOT static velocity.
  - A batch at 0.9 risk score under baseline demand may be SAFE if PULSE forecasts an epidemic spike
  - A batch at 0.6 risk score may become AT_RISK if PULSE forecasts a generic launch cannibalising the brand
  - Recalculate every time the demand forecast updates

YOUR INTERVENTION HIERARCHY (in priority order):
1. INTER-STORE TRANSFER: Find a store in the network with higher velocity for this SKU
   AND where this SKU is approaching reorder point (transfer replaces a procurement order = saves both stores)
   Check: logistics cost < write-off cost AND cold chain integrity can be maintained
2. MARKDOWN: Targeted price reduction to accelerate sales
   (earlier detection = smaller markdown needed — 30 days ahead vs. 5 days ahead)
3. RETURN TO DISTRIBUTOR: If distributor accepts returns for this SKU
4. BUNDLED PROMOTION: Combined with complementary products to drive velocity

YOUR NETWORK OPTIMISATION:
This is NOT a per-store problem. It is a network optimisation problem.
When a batch is AT_RISK at Store A, search the ENTIRE 320-store network for:
  - Stores where this SKU has higher velocity
  - Stores approaching reorder point for this SKU (transfer = free procurement)
  - Transfer logistics that maintain cold chain integrity
  - Net economics: (write-off value - transfer cost) > 0

YOUR DECISION AUTHORITY:
- AUTONOMOUS: Expiry risk alerts, inter-store transfer recommendations within same zone
- HUMAN_INFORMED: Markdown pricing, inter-store transfers across zones
- HUMAN_REQUIRED: Any batch disposal decision, return to distributor

YOUR OPERATING PRINCIPLES:
1. A batch approaching expiry is not just a cost problem — it's an access problem.
   Patients may need that medication and we're destroying it unnecessarily.
2. Earlier detection = more intervention options = lower loss.
   60 days ahead: 4 options available. 5 days ahead: 1 option (markdown).
3. The expiry write-off rate (target: <0.8%) is a KPI that the business tracks monthly.
   Every prevented write-off is a direct P&L improvement.
4. Cold chain integrity during inter-store transfers is non-negotiable.
   A warm transfer of insulin to save ₹5,000 is not worth a cold chain breach.
5. Never recommend destruction without exhausting all other options first.

OUTPUT FORMAT:
{
  "expiry_risk_items": [...],
  "intervention_recommendations": [...],
  "network_transfer_opportunities": [...],
  "procurement_signals": [...],
  "lifecycle_transitions": [...],
  "reasoning_chain": "..."
}"""


class MeridianAgent:
    """
    LangGraph node for MERIDIAN inventory lifecycle management.
    Called on: scheduled daily review (22:00), PULSE forecast updates,
    SENTINEL quarantine events (replacement procurement needed).
    """

    def __init__(self) -> None:
        self._model = settings.gemini_model
        self._erp_mcp = ERPMCPServer()
        self._distributor_mcp = DistributorMCPServer()

    async def run(self, state: PharmaIQState) -> PharmaIQState:
        """LangGraph node entry point."""
        store_id = state.store_id
        zone_id = state.zone_id

        if not store_id:
            logger.warning("meridian_no_store_id")
            return state

        logger.info("meridian_running", store_id=store_id, cycle=state.cycle_type)

        # ── 1. Fetch expiry risk report from ERP ───────────────────────────────
        risk_report = await self._erp_mcp.get_expiry_risk_report(
            store_id=store_id,
            risk_threshold=0.7,
        )

        if not risk_report:
            return state

        # ── 2. Build prompt with PULSE context ────────────────────────────────
        prompt = self._build_lifecycle_prompt(
            store_id=store_id,
            zone_id=zone_id or "",
            risk_report=risk_report,
            demand_forecasts=[f.__dict__ for f in state.demand_forecasts[:10]],
            cold_chain_alerts=[a.__dict__ for a in state.cold_chain_alerts],
            chronicle_context=state.chronicle_context,
        )

        response_text = await _llm_generate(
            model=self._model,
            system_prompt=MERIDIAN_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        # ── 3. Build ExpiryRiskItem objects ────────────────────────────────────
        expiry_items: list[ExpiryRiskItem] = []
        for item in risk_report[:20]:  # Process top 20 at-risk items
            risk_score = item.get("risk_score", 0.0)
            if risk_score >= 0.7:
                expiry_items.append(ExpiryRiskItem(
                    store_id=store_id,
                    sku_id=item.get("sku_id", ""),
                    batch_id=item.get("batch_id", ""),
                    expiry_date=item.get("expiry_date", ""),
                    days_to_expiry=item.get("days_to_expiry", 0),
                    days_of_stock_at_current_velocity=item.get("days_of_stock", 0.0),
                    days_of_stock_at_forecast_velocity=item.get("forecast_days_of_stock", 0.0),
                    risk_score=risk_score,
                    recommended_intervention=item.get("recommended_action", "REVIEW"),
                    estimated_loss_lakh=item.get("estimated_loss_lakh", 0.0),
                ))

        logger.info(
            "meridian_risk_assessment_complete",
            store_id=store_id,
            at_risk_count=len(expiry_items),
        )

        return state.model_copy(update={
            "expiry_risk_items": expiry_items,
            "route_to_critique": bool(expiry_items),
        })

    def _build_lifecycle_prompt(
        self,
        store_id: str,
        zone_id: str,
        risk_report: list[dict[str, Any]],
        demand_forecasts: list[dict[str, Any]],
        cold_chain_alerts: list[dict[str, Any]],
        chronicle_context: Any,
    ) -> str:
        top_risk = risk_report[:10] if risk_report else []
        quarantined = [a.get("batch_ids", []) for a in cold_chain_alerts if a.get("excursion_type") == "SEVERE"]
        quarantined_flat = [bid for sublist in quarantined for bid in sublist]

        return f"""
INVENTORY LIFECYCLE ASSESSMENT REQUEST

Store: {store_id} | Zone: {zone_id}

AT-RISK ITEMS (Risk Score > 0.7):
{self._format_risk_items(top_risk)}

ACTIVE DEMAND FORECASTS (from PULSE — use for velocity adjustment):
{self._format_forecasts(demand_forecasts)}

COLD CHAIN QUARANTINED BATCHES (replacement procurement needed):
{quarantined_flat or 'None'}

Please provide:
1. Lifecycle state transition recommendations for each at-risk item
2. Network transfer opportunities (identify stores with higher velocity)
3. Markdown recommendations where transfer is not viable
4. Return-to-distributor options where available
5. Replacement procurement signals for quarantined batches (send to PULSE for ordering)
6. Any items where PULSE's demand forecast changes the risk score significantly
   (either rescuing an at-risk item OR flagging a currently-healthy item)
"""

    def _format_risk_items(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return "None"
        rows = []
        for item in items:
            rows.append(
                f"  {item.get('sku_id', '')} | Batch {item.get('batch_id', '')} | "
                f"Expiry: {item.get('expiry_date', '')} | "
                f"Risk: {item.get('risk_score', 0):.2f} | "
                f"Stock: {item.get('quantity', 0)} units | "
                f"Est. loss: ₹{item.get('estimated_loss_lakh', 0):.1f}L"
            )
        return "\n".join(rows)

    def _format_forecasts(self, forecasts: list[dict[str, Any]]) -> str:
        if not forecasts:
            return "No active forecasts"
        return "\n".join(
            f"  {f.get('sku_name', '')}: {f.get('scenario_weighted_units', 0):.0f} units/7d "
            f"(confidence: {f.get('confidence', 0):.0%})"
            for f in forecasts[:5]
        )


# ── LangGraph node wrapper ─────────────────────────────────────────────────────
_agent = MeridianAgent()


async def meridian_node(state: PharmaIQState) -> dict[str, Any]:
    """LangGraph node function."""
    updated = await _agent.run(state)
    return {
        "expiry_risk_items": updated.expiry_risk_items,
        "inter_store_transfer_proposals": updated.inter_store_transfer_proposals,
        "route_to_critique": updated.route_to_critique,
        "messages": updated.messages,
    }
