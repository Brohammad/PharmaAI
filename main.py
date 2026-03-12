"""
PharmaIQ FastAPI Application Entry Point.

Lifecycle:
  startup  → configure logging, compile graph, start APScheduler
  running  → serve API requests, execute scheduled cycles
  shutdown → flush audit logs, stop scheduler cleanly

Scheduled cycles (all times IST = UTC+5:30):
  05:00  → Morning Forecast (MORNING_FORECAST)
  every 2h → Compliance Sweep (COMPLIANCE_SWEEP)
  13:00  → Midday Reforecast (MIDDAY_REFORECAST)
  22:00  → Expiry Review (EXPIRY_REVIEW)
  Mon 07:00 → Weekly Brief (WEEKLY_BRIEF)
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import asyncio
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.settings import settings
from graph.ingestion import (
    SignalType,
    CycleType,
    classify_signal,
    determine_cycle_type,
    build_initial_state,
    compute_signal_significance,
    passes_significance_gate,
)
from graph.state import PharmaIQState
from graph.workflow import graph
from utils.logger import configure_logging, get_logger
from api.mock_data import (
    get_kpi_summary,
    get_live_events,
    get_cold_chain_overview,
    get_cold_chain_alerts,
    get_temperature_trend,
    get_epidemic_signals,
    get_demand_forecast,
    get_forecast_chart_data,
    get_staffing_overview,
    get_expiry_risks,
    get_recent_decisions,
    get_escalation_queue,
)

configure_logging()
logger = get_logger("main")

# ── WebSocket broadcast manager ───────────────────────────────────────────────
class _WSManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast(self, payload: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

ws_manager = _WSManager()

# ── Scheduler ──────────────────────────────────────────────────────────────────
_scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


# ── Lifespan context manager ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("pharmaiq_starting", version="1.0.0", env=settings.environment)

    # Start scheduled cycles
    _scheduler.add_job(
        _run_scheduled_cycle,
        CronTrigger(hour=settings.morning_forecast_hour, minute=0),
        args=["MORNING_FORECAST"],
        id="morning_forecast",
        name="Morning Demand Forecast",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_scheduled_cycle,
        CronTrigger(minute="0"),  # Every hour at :00 — subset decided inside handler
        args=["COMPLIANCE_SWEEP"],
        id="compliance_sweep",
        name="Compliance Sweep (every 2h)",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_scheduled_cycle,
        CronTrigger(hour=settings.midday_reforecast_hour, minute=0),
        args=["MIDDAY_REFORECAST"],
        id="midday_reforecast",
        name="Midday Demand Reforecast",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_scheduled_cycle,
        CronTrigger(hour=settings.expiry_review_hour, minute=0),
        args=["EXPIRY_REVIEW"],
        id="expiry_review",
        name="Daily Expiry Review",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_scheduled_cycle,
        CronTrigger(day_of_week="mon", hour=settings.weekly_brief_hour, minute=0),
        args=["WEEKLY_BRIEF"],
        id="weekly_brief",
        name="Weekly Intelligence Brief",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("scheduler_started", jobs=len(_scheduler.get_jobs()))

    # Background task: push live events to WebSocket clients every 4 seconds
    async def _live_push_loop():
        while True:
            await asyncio.sleep(4)
            try:
                events = get_live_events(limit=1)
                await ws_manager.broadcast({"type": "agent_event", "data": events[0]})
            except Exception:
                pass

    _push_task = asyncio.create_task(_live_push_loop())

    yield

    _push_task.cancel()
    _scheduler.shutdown(wait=False)
    logger.info("pharmaiq_shutdown")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PharmaIQ",
    description=(
        "Autonomous Health Retail Intelligence System for MedChain India. "
        "8-agent LangGraph orchestration across 320 pharmacies."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────
class SignalIngestionRequest(BaseModel):
    store_id: str
    zone_id: str
    event_type: str
    source: str = "api"
    data: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class SignalIngestionResponse(BaseModel):
    run_id: str
    cycle_type: str
    signal_type: str
    significance: float
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    graph_nodes: int
    scheduler_jobs: int


class CycleRunResponse(BaseModel):
    run_id: str
    cycle_type: str
    store_id: str
    zone_id: str
    status: str
    approved_actions: int
    escalations: int
    cold_chain_risk: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        graph_nodes=10,
        scheduler_jobs=len(_scheduler.get_jobs()),
    )


@app.post(
    "/signals/ingest",
    response_model=SignalIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Signals"],
)
async def ingest_signal(request: SignalIngestionRequest):
    """
    Ingest an external signal (IoT cold chain event, IDSP report, HR event, etc.)
    and trigger the appropriate PharmaIQ decision cycle.
    """
    raw_event = {
        "event_type": request.event_type,
        "source": request.source,
        "data": request.data,
        "metadata": request.metadata,
    }

    signal_type = classify_signal(raw_event)
    cycle_type = determine_cycle_type(signal_type, raw_event)
    significance = compute_signal_significance(signal_type, raw_event)

    if not passes_significance_gate(signal_type, significance):
        return SignalIngestionResponse(
            run_id=str(uuid.uuid4()),
            cycle_type=cycle_type.value,
            signal_type=signal_type.value,
            significance=significance,
            status="DROPPED",
            message=(
                f"Signal significance {significance:.2f} below threshold "
                f"for {signal_type.value}. Logged and discarded."
            ),
        )

    run_id = str(uuid.uuid4())
    initial_state = build_initial_state(
        raw_event=raw_event,
        store_id=request.store_id,
        zone_id=request.zone_id,
        signal_type=signal_type,
        cycle_type=cycle_type,
    )

    # Run graph asynchronously (non-blocking)
    import asyncio
    asyncio.create_task(
        _run_graph(run_id=run_id, initial_state=initial_state)
    )

    logger.info(
        "signal_ingested",
        run_id=run_id,
        store_id=request.store_id,
        signal_type=signal_type.value,
        cycle_type=cycle_type.value,
        significance=significance,
    )

    return SignalIngestionResponse(
        run_id=run_id,
        cycle_type=cycle_type.value,
        signal_type=signal_type.value,
        significance=significance,
        status="ACCEPTED",
        message=f"Decision cycle {cycle_type.value} queued with run_id {run_id}",
    )


@app.post(
    "/cycles/trigger",
    response_model=CycleRunResponse,
    tags=["Cycles"],
)
async def trigger_cycle_manually(
    store_id: str,
    zone_id: str,
    cycle_type: str = "MANUAL_TRIGGER",
):
    """
    Manually trigger a PharmaIQ decision cycle for a specific store.
    Useful for testing and on-demand analysis.
    """
    try:
        ct = CycleType(cycle_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown cycle_type: {cycle_type}. Valid: {[c.value for c in CycleType]}",
        )

    initial_state = build_initial_state(
        raw_event={"event_type": "manual_trigger", "source": "api"},
        store_id=store_id,
        zone_id=zone_id,
        signal_type=SignalType.SCHEDULED_FORECAST,
        cycle_type=ct,
    )

    final_state = await _run_graph_sync(initial_state)

    return CycleRunResponse(
        run_id=str(uuid.uuid4()),
        cycle_type=ct.value,
        store_id=store_id,
        zone_id=zone_id,
        status="COMPLETED",
        approved_actions=len(getattr(final_state, "nexus_priority_decisions", [])),
        escalations=len(getattr(final_state, "pending_escalations", [])),
        cold_chain_risk=getattr(final_state, "cold_chain_risk_level", "unknown"),
    )


@app.get("/cycles/status", tags=["Cycles"])
async def get_scheduler_status():
    """Return current APScheduler job status and next run times."""
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"scheduler_running": _scheduler.running, "jobs": jobs}


@app.get("/graph/topology", tags=["System"])
async def get_graph_topology():
    """Return the PharmaIQ agent graph topology."""
    return {
        "nodes": [
            "chronicle_entry", "sentinel", "pulse", "aegis", "meridian",
            "critique", "compliance", "nexus", "execution", "chronicle_exit"
        ],
        "tiers": {
            "tier3_meta_entry": ["chronicle_entry"],
            "tier1_operational": ["sentinel", "pulse", "aegis", "meridian"],
            "tier2_validation": ["critique", "compliance"],
            "tier3_synthesis": ["nexus"],
            "execution": ["execution"],
            "tier3_meta_exit": ["chronicle_exit"],
        },
        "execution_order": "sequential (chronicle_entry → sentinel → pulse → aegis → meridian → critique → compliance → nexus → execution → chronicle_exit)",
    }


# ── WebSocket live feed ────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint — streams live agent events to the frontend."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive pings from client
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── REST API v1 ───────────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard/kpis", tags=["Dashboard"])
async def api_kpis():
    return get_kpi_summary()


@app.get("/api/v1/dashboard/events", tags=["Dashboard"])
async def api_events(limit: int = 20):
    return {"events": get_live_events(limit=limit)}


@app.get("/api/v1/cold-chain/overview", tags=["Cold Chain"])
async def api_cold_chain_overview():
    return get_cold_chain_overview()


@app.get("/api/v1/cold-chain/alerts", tags=["Cold Chain"])
async def api_cold_chain_alerts():
    return {"alerts": get_cold_chain_alerts()}


@app.get("/api/v1/cold-chain/trend/{unit_id}", tags=["Cold Chain"])
async def api_temperature_trend(unit_id: str):
    return {"unit_id": unit_id, "trend": get_temperature_trend(unit_id)}


@app.get("/api/v1/demand/epidemic-signals", tags=["Demand"])
async def api_epidemic_signals():
    return {"signals": get_epidemic_signals()}


@app.get("/api/v1/demand/forecast", tags=["Demand"])
async def api_demand_forecast(store_id: str = "STORE_DEL_001"):
    return {"store_id": store_id, "forecasts": get_demand_forecast(store_id)}


@app.get("/api/v1/demand/forecast-chart", tags=["Demand"])
async def api_forecast_chart():
    return {"data": get_forecast_chart_data()}


@app.get("/api/v1/staffing/overview", tags=["Staffing"])
async def api_staffing_overview():
    return get_staffing_overview()


@app.get("/api/v1/inventory/expiry-risks", tags=["Inventory"])
async def api_expiry_risks():
    return {"items": get_expiry_risks()}


@app.get("/api/v1/decisions/recent", tags=["Decisions"])
async def api_recent_decisions(limit: int = 15):
    return {"decisions": get_recent_decisions(limit=limit)}


@app.get("/api/v1/decisions/escalations", tags=["Decisions"])
async def api_escalation_queue():
    return {"escalations": get_escalation_queue()}


@app.post("/api/v1/decisions/escalations/{escalation_id}/approve", tags=["Decisions"])
async def api_approve_escalation(escalation_id: str):
    await ws_manager.broadcast({
        "type": "escalation_resolved",
        "data": {"escalation_id": escalation_id, "action": "APPROVED"},
    })
    return {"escalation_id": escalation_id, "status": "APPROVED"}


@app.post("/api/v1/decisions/escalations/{escalation_id}/reject", tags=["Decisions"])
async def api_reject_escalation(escalation_id: str):
    await ws_manager.broadcast({
        "type": "escalation_resolved",
        "data": {"escalation_id": escalation_id, "action": "REJECTED"},
    })
    return {"escalation_id": escalation_id, "status": "REJECTED"}


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _run_graph(run_id: str, initial_state: dict[str, Any]) -> None:
    """Non-blocking graph execution (called via asyncio.create_task)."""
    try:
        logger.info("graph_run_start", run_id=run_id)
        state = PharmaIQState(**initial_state)
        final = await graph.ainvoke(state)
        logger.info(
            "graph_run_complete",
            run_id=run_id,
            approved=len(getattr(final, "nexus_priority_decisions", [])),
        )
    except Exception as exc:
        logger.error("graph_run_failed", run_id=run_id, error=str(exc))


async def _run_graph_sync(initial_state: dict[str, Any]) -> PharmaIQState:
    """Blocking graph execution (for synchronous API endpoints)."""
    state = PharmaIQState(**initial_state)
    return await graph.ainvoke(state)


async def _run_scheduled_cycle(cycle_type_str: str) -> None:
    """
    Called by APScheduler for each scheduled cycle.
    In production, this would iterate over all stores in the network.
    For demonstration, runs for a representative set.
    """
    # In production: fetch active store list from ERP
    # For now: single representative execution
    logger.info("scheduled_cycle_start", cycle_type=cycle_type_str)

    ct = CycleType(cycle_type_str)

    # Skip compliance sweep if not on the 2-hour mark
    if ct == CycleType.COMPLIANCE_SWEEP:
        current_hour = datetime.now(timezone.utc).hour
        if current_hour % 2 != 0:
            return

    initial_state = build_initial_state(
        raw_event={"event_type": "scheduled", "source": "scheduler"},
        store_id="MEDCHAIN_HQ",  # In production: iterate over all stores
        zone_id="DELHI_NCR",
        signal_type=SignalType.SCHEDULED_FORECAST,
        cycle_type=ct,
    )

    await _run_graph(run_id=str(uuid.uuid4()), initial_state=initial_state)
    logger.info("scheduled_cycle_complete", cycle_type=cycle_type_str)


# ── Serve built frontend (production) ─────────────────────────────────────────
import os as _os
_dist = _os.path.join(_os.path.dirname(__file__), "frontend", "dist")
if _os.path.exists(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")


# ── Dev entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info",
    )
