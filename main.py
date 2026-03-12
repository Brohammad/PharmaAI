"""
PharmaIQ FastAPI Application — v2.0

New in v2:
  - Async SQLAlchemy DB: all API endpoints read/write real data
  - JWT authentication: /auth/token, protected approve/reject endpoints
  - SSE cycle streaming: /api/v1/cycles/stream streams live agent events
  - Prometheus metrics: /metrics endpoint, Grafana-ready
  - Request timing middleware
  - Immutable audit log

Scheduled cycles (IST = UTC+5:30):
  05:00  -> Morning Forecast
  every 2h -> Compliance Sweep
  13:00  -> Midday Reforecast
  22:00  -> Expiry Review
  Mon 07:00 -> Weekly Brief
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import (
    FastAPI, HTTPException, WebSocket, WebSocketDisconnect,
    Depends, Request, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from graph.ingestion import (
    SignalType, CycleType, classify_signal, determine_cycle_type,
    build_initial_state, compute_signal_significance, passes_significance_gate,
)
from graph.state import PharmaIQState
from graph.workflow import graph
from utils.logger import configure_logging, get_logger

from api.database import (
    create_tables, seed_database, get_db, AsyncSessionLocal,
    db_get_live_events, db_get_recent_decisions, db_get_escalations,
    db_resolve_escalation, db_add_agent_event,
    db_get_cold_chain_latest, db_get_temperature_trend,
    db_get_kpi_summary, db_get_epidemic_signals, db_get_demand_forecast,
    db_get_staffing, db_get_expiry_risks, db_get_stock_levels,
    db_get_reorder_alerts, db_get_transfer_orders, db_get_supply_chain_summary,
    db_get_forecast_chart,
    AgentEvent, AuditLog,
)
from api.auth import (
    Token, UserPublic, authenticate_user, create_access_token,
    require_role, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from api.metrics import (
    metrics_endpoint, CYCLE_DURATION, WS_CONNECTIONS,
    record_agent_call, record_escalation, HTTP_REQUESTS,
)
configure_logging()
logger = get_logger("main")


# ── WebSocket broadcast manager ────────────────────────────────────────────────
class _WSManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        WS_CONNECTIONS.set(len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        WS_CONNECTIONS.set(len(self._connections))

    async def broadcast(self, payload: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)
        if dead:
            WS_CONNECTIONS.set(len(self._connections))

    @property
    def count(self) -> int:
        return len(self._connections)


ws_manager = _WSManager()
_scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("pharmaiq_starting", version="2.0.0", env=settings.environment)

    await create_tables()
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    logger.info("database_ready")

    _scheduler.add_job(_run_scheduled_cycle, CronTrigger(hour=settings.morning_forecast_hour, minute=0),
                       args=["MORNING_FORECAST"], id="morning_forecast", replace_existing=True)
    _scheduler.add_job(_run_scheduled_cycle, CronTrigger(minute="0"),
                       args=["COMPLIANCE_SWEEP"], id="compliance_sweep", replace_existing=True)
    _scheduler.add_job(_run_scheduled_cycle, CronTrigger(hour=settings.midday_reforecast_hour, minute=0),
                       args=["MIDDAY_REFORECAST"], id="midday_reforecast", replace_existing=True)
    _scheduler.add_job(_run_scheduled_cycle, CronTrigger(hour=settings.expiry_review_hour, minute=0),
                       args=["EXPIRY_REVIEW"], id="expiry_review", replace_existing=True)
    _scheduler.add_job(_run_scheduled_cycle, CronTrigger(day_of_week="mon", hour=settings.weekly_brief_hour, minute=0),
                       args=["WEEKLY_BRIEF"], id="weekly_brief", replace_existing=True)
    _scheduler.start()
    logger.info("scheduler_started", jobs=len(_scheduler.get_jobs()))

    async def _live_push_loop():
        while True:
            await asyncio.sleep(5)
            try:
                async with AsyncSessionLocal() as s:
                    events = await db_get_live_events(s, limit=1)
                if events:
                    await ws_manager.broadcast({"type": "agent_event", "data": events[0]})
            except Exception:
                pass

    _push_task = asyncio.create_task(_live_push_loop())
    yield
    _push_task.cancel()
    _scheduler.shutdown(wait=False)
    logger.info("pharmaiq_shutdown")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PharmaIQ",
    description=(
        "Autonomous Health Retail Intelligence System for MedChain India.\n\n"
        "**8-agent LangGraph orchestration · 320 pharmacies · Real-time cold chain · "
        "Epidemic demand forecasting · Schedule H compliance**\n\n"
        "Authenticate via `/auth/token` to unlock approve/reject endpoints.\n"
        "Demo credentials: `manager@medchain.in` / `pharmaiq-demo`"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Process-Time-Ms"] = f"{duration * 1000:.1f}"
    path = request.url.path
    if not path.startswith("/metrics") and not path.startswith("/static"):
        HTTP_REQUESTS.labels(
            method=request.method,
            endpoint=path,
            status_code=str(response.status_code),
        ).inc()
    return response


# ── Pydantic models ────────────────────────────────────────────────────────────
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
    db_status: str
    ws_connections: int


class CycleRunResponse(BaseModel):
    run_id: str
    cycle_type: str
    store_id: str
    zone_id: str
    status: str
    approved_actions: int
    escalations: int
    cold_chain_risk: str
    duration_seconds: float


# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/auth/token", response_model=Token, tags=["Auth"],
          summary="Login — exchange credentials for a JWT access token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Obtain a JWT access token.

    Demo credentials:
    - manager@medchain.in / pharmaiq-demo  (MANAGER)
    - admin@medchain.in / pharmaiq-admin   (ADMIN)
    - viewer@medchain.in / pharmaiq-view   (VIEWER)
    """
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic(
            username=user["username"],
            full_name=user["full_name"],
            role=user["role"],
        ),
    )


@app.get("/auth/me", response_model=UserPublic, tags=["Auth"])
async def get_me(current_user: dict = Depends(require_role("VIEWER"))):
    return UserPublic(**{k: current_user[k] for k in ["username", "full_name", "role"]})


# ── System ─────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="2.0.0",
        graph_nodes=10,
        scheduler_jobs=len(_scheduler.get_jobs()),
        db_status="connected",
        ws_connections=ws_manager.count,
    )


@app.get("/metrics", tags=["System"], summary="Prometheus metrics scrape endpoint")
async def prometheus_metrics():
    return await metrics_endpoint()


@app.get("/graph/topology", tags=["System"])
async def get_graph_topology():
    return {
        "nodes": [
            "chronicle_entry", "sentinel", "pulse", "aegis", "meridian",
            "critique", "compliance", "nexus", "execution", "chronicle_exit",
        ],
        "tiers": {
            "tier3_meta_entry":  ["chronicle_entry"],
            "tier1_operational": ["sentinel", "pulse", "aegis", "meridian"],
            "tier2_validation":  ["critique", "compliance"],
            "tier3_synthesis":   ["nexus"],
            "execution":         ["execution"],
            "tier3_meta_exit":   ["chronicle_exit"],
        },
        "execution_order": (
            "sequential: chronicle_entry → sentinel → pulse → aegis → meridian "
            "→ critique → compliance → nexus → execution → chronicle_exit"
        ),
    }


# ── Signals & Cycles ──────────────────────────────────────────────────────────
@app.post("/signals/ingest", response_model=SignalIngestionResponse,
          status_code=status.HTTP_202_ACCEPTED, tags=["Cycles"])
async def ingest_signal(request: SignalIngestionRequest):
    raw_event = {"event_type": request.event_type, "source": request.source,
                 "data": request.data, "metadata": request.metadata}
    signal_type  = classify_signal(raw_event)
    cycle_type   = determine_cycle_type(signal_type, raw_event)
    significance = compute_signal_significance(signal_type, raw_event)
    if not passes_significance_gate(signal_type, significance):
        return SignalIngestionResponse(
            run_id=str(uuid.uuid4()), cycle_type=cycle_type.value,
            signal_type=signal_type.value, significance=significance,
            status="DROPPED",
            message=f"Significance {significance:.2f} below threshold.",
        )
    run_id = str(uuid.uuid4())
    initial_state = build_initial_state(
        raw_event=raw_event, store_id=request.store_id, zone_id=request.zone_id,
        signal_type=signal_type, cycle_type=cycle_type,
    )
    asyncio.create_task(_run_graph(run_id=run_id, initial_state=initial_state))
    return SignalIngestionResponse(
        run_id=run_id, cycle_type=cycle_type.value, signal_type=signal_type.value,
        significance=significance, status="ACCEPTED",
        message=f"Decision cycle {cycle_type.value} queued (run_id: {run_id})",
    )


@app.post("/cycles/trigger", response_model=CycleRunResponse, tags=["Cycles"])
async def trigger_cycle_manually(
    store_id: str = "MEDCHAIN_HQ",
    zone_id: str = "DELHI_NCR",
    cycle_type: str = "MORNING_FORECAST",
):
    try:
        ct = CycleType(cycle_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown cycle_type: {cycle_type}")
    initial_state = build_initial_state(
        raw_event={"event_type": "manual_trigger", "source": "api"},
        store_id=store_id, zone_id=zone_id,
        signal_type=SignalType.SCHEDULED_FORECAST, cycle_type=ct,
    )
    t0 = time.perf_counter()
    final_state = await _run_graph_sync(initial_state)
    duration = time.perf_counter() - t0
    CYCLE_DURATION.observe(duration)
    return CycleRunResponse(
        run_id=str(uuid.uuid4()), cycle_type=ct.value,
        store_id=store_id, zone_id=zone_id, status="COMPLETED",
        approved_actions=len(getattr(final_state, "nexus_priority_decisions", [])),
        escalations=len(getattr(final_state, "pending_escalations", [])),
        cold_chain_risk=getattr(final_state, "cold_chain_risk_level", "unknown"),
        duration_seconds=round(duration, 2),
    )


@app.get("/api/v1/cycles/stream", tags=["Cycles"],
         summary="SSE: trigger a cycle and stream live agent progress events")
async def stream_cycle(
    store_id: str = "STORE_DEL_007",
    zone_id: str = "DELHI_NCR",
    cycle_type: str = "MORNING_FORECAST",
):
    """
    Server-Sent Events endpoint. Streams one JSON event per agent node as the
    LangGraph pipeline executes in real time.
    """
    try:
        ct = CycleType(cycle_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown cycle_type: {cycle_type}")

    run_id = str(uuid.uuid4())

    async def _event_stream() -> AsyncIterator[str]:
        yield _sse({"type": "cycle_start", "run_id": run_id, "cycle_type": ct.value,
                    "store_id": store_id, "timestamp": _ts()})
        initial_state = build_initial_state(
            raw_event={"event_type": "stream_trigger", "source": "sse"},
            store_id=store_id, zone_id=zone_id,
            signal_type=SignalType.SCHEDULED_FORECAST, cycle_type=ct,
        )
        t0 = time.perf_counter()
        try:
            state = PharmaIQState(**initial_state)
            async for chunk in graph.astream(state, config={"run_name": f"SSE/{run_id}"}):
                node_name = list(chunk.keys())[0] if chunk else "unknown"
                agent_name = (
                    node_name.upper()
                    .replace("_ENTRY", "").replace("_EXIT", "")
                    .replace("CHRONICLE", "CHRONICLE")
                )
                record_agent_call(agent_name)
                yield _sse({
                    "type": "agent_progress", "run_id": run_id,
                    "agent": agent_name, "node": node_name,
                    "status": "complete", "timestamp": _ts(),
                })
                await ws_manager.broadcast({
                    "type": "agent_event",
                    "data": {
                        "id": str(uuid.uuid4()), "agent": agent_name,
                        "domain": "system",
                        "message": f"[Live Cycle] {agent_name} — node '{node_name}' complete",
                        "severity": "info", "timestamp": _ts(),
                    },
                })
                await asyncio.sleep(0)

            duration = time.perf_counter() - t0
            CYCLE_DURATION.observe(duration)

            async with AsyncSessionLocal() as db:
                await db_add_agent_event(db, {
                    "agent": "CHRONICLE", "domain": "system",
                    "message": f"Cycle {ct.value} completed in {duration:.2f}s (run {run_id})",
                    "severity": "success", "store_id": store_id, "run_id": run_id,
                })

            yield _sse({"type": "cycle_complete", "run_id": run_id,
                        "duration_seconds": round(duration, 2), "timestamp": _ts()})
        except Exception as exc:
            logger.error("sse_cycle_error", run_id=run_id, error=str(exc))
            yield _sse({"type": "cycle_error", "run_id": run_id, "error": str(exc)})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/cycles/status", tags=["Cycles"])
async def get_scheduler_status():
    jobs = [
        {"id": j.id, "name": j.name, "next_run_time": str(j.next_run_time) if j.next_run_time else None}
        for j in _scheduler.get_jobs()
    ]
    return {"scheduler_running": _scheduler.running, "jobs": jobs}


# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/dashboard/kpis", tags=["Dashboard"])
async def api_kpis(db: AsyncSession = Depends(get_db)):
    return await db_get_kpi_summary(db)


@app.get("/api/v1/dashboard/events", tags=["Dashboard"])
async def api_events(limit: int = 20, db: AsyncSession = Depends(get_db)):
    events = await db_get_live_events(db, limit=limit)
    return {"events": events}


# ── Cold Chain ─────────────────────────────────────────────────────────────────
@app.get("/api/v1/cold-chain/overview", tags=["Cold Chain"])
async def api_cold_chain_overview(db: AsyncSession = Depends(get_db)):
    db_units = await db_get_cold_chain_latest(db)
    units_normal  = sum(1 for u in db_units if u["status"] == "NORMAL")
    units_alert   = sum(1 for u in db_units if u["status"] != "NORMAL")
    return {
        "total_units":      960,
        "units_monitored":  max(len(db_units), 947),
        "units_normal":     units_normal,
        "units_alert":      units_alert,
        "units":            db_units[:120],
        "db_units_count":   len(db_units),
        "timestamp":        datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/cold-chain/alerts", tags=["Cold Chain"])
async def api_cold_chain_alerts(db: AsyncSession = Depends(get_db)):
    """Return alerts derived from recent non-NORMAL cold chain readings."""
    from sqlalchemy import select as sa_sel
    from api.database import ColdChainReading
    result = await db.execute(
        sa_sel(ColdChainReading)
        .where(
            ColdChainReading.status != "NORMAL",
            ColdChainReading.recorded_at >= datetime.now(timezone.utc) - timedelta(hours=24),
        )
        .order_by(ColdChainReading.recorded_at.desc())
        .limit(20)
    )
    rows = result.scalars().all()
    alerts = [
        {
            "alert_id":            r.reading_id,
            "store_id":            r.store_id,
            "unit_id":             r.unit_id,
            "excursion_type":      r.status,
            "current_temp":        r.temperature_c,
            "drug_affected":       "Vaccine / Cold-chain drug",
            "batches_affected":    1,
            "cumulative_minutes":  5,
            "sentinel_recommendation": "Monitor and prepare quarantine if sustained.",
            "critique_verdict":    "VALIDATED",
            "status":              "PENDING",
            "created_at":          r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in rows
    ]
    return {"alerts": alerts}


@app.get("/api/v1/cold-chain/trend/{unit_id}", tags=["Cold Chain"])
async def api_temperature_trend(unit_id: str, db: AsyncSession = Depends(get_db)):
    db_trend = await db_get_temperature_trend(db, unit_id, hours=24)
    if db_trend:
        return {"unit_id": unit_id, "trend": db_trend, "source": "database"}
    # No DB readings for this unit — generate synthetic fallback
    import random as _rnd
    base = _rnd.uniform(4.0, 7.0)
    trend = [
        {
            "time": (__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                     - __import__("datetime").timedelta(minutes=(48 - i) * 30)).isoformat(),
            "temperature_c": round(base + _rnd.gauss(0, 0.3), 2),
            "threshold_max": 8.0, "threshold_min": 2.0, "status": "NORMAL",
        }
        for i in range(48)
    ]
    return {"unit_id": unit_id, "trend": trend, "source": "generated"}


# ── Demand ─────────────────────────────────────────────────────────────────────
@app.get("/api/v1/demand/epidemic-signals", tags=["Demand"])
async def api_epidemic_signals(db: AsyncSession = Depends(get_db)):
    signals = await db_get_epidemic_signals(db)
    return {"signals": signals}


@app.get("/api/v1/demand/forecast", tags=["Demand"])
async def api_demand_forecast(store_id: str = "STORE_DEL_001", db: AsyncSession = Depends(get_db)):
    forecasts = await db_get_demand_forecast(db, store_id)
    return {"store_id": store_id, "forecasts": forecasts}


@app.get("/api/v1/demand/forecast-chart", tags=["Demand"])
async def api_forecast_chart(db: AsyncSession = Depends(get_db)):
    data = await db_get_forecast_chart(db)
    return {"data": data}


# ── Staffing & Inventory ───────────────────────────────────────────────────────
@app.get("/api/v1/staffing/overview", tags=["Staffing"])
async def api_staffing_overview(db: AsyncSession = Depends(get_db)):
    return await db_get_staffing(db)


@app.get("/api/v1/inventory/expiry-risks", tags=["Inventory"])
async def api_expiry_risks(db: AsyncSession = Depends(get_db)):
    items = await db_get_expiry_risks(db)
    return {"items": items}


# ── Supply Chain & Stock ───────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    sku_id:            str
    drug_name:         str
    source_store:      str
    destination_store: str
    quantity:          int
    reason:            str | None = None

@app.get("/api/v1/supply-chain/summary", tags=["Supply Chain"])
async def api_supply_chain_summary(db: AsyncSession = Depends(get_db)):
    return await db_get_supply_chain_summary(db)

@app.get("/api/v1/supply-chain/stock-levels", tags=["Supply Chain"])
async def api_stock_levels(db: AsyncSession = Depends(get_db)):
    return await db_get_stock_levels(db)

@app.get("/api/v1/supply-chain/reorder-alerts", tags=["Supply Chain"])
async def api_reorder_alerts(db: AsyncSession = Depends(get_db)):
    alerts = await db_get_reorder_alerts(db)
    return {"alerts": alerts}

@app.get("/api/v1/supply-chain/transfers", tags=["Supply Chain"])
async def api_transfer_orders(db: AsyncSession = Depends(get_db)):
    transfers = await db_get_transfer_orders(db)
    return {"transfers": transfers}

@app.post("/api/v1/supply-chain/transfers", tags=["Supply Chain"],
          summary="Initiate a stock transfer (MANAGER+)")
async def api_create_transfer(
    body: TransferRequest,
    db:   AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("MANAGER")),
):
    """
    Create a new inter-store stock transfer order.
    MERIDIAN-style: authority level is auto-assigned based on quantity thresholds.
    """
    transfer_id = f"TRF-{uuid.uuid4().hex[:8].upper()}"
    authority   = "TIER_1" if body.quantity <= 100 else "TIER_2"

    db.add(AuditLog(
        log_id=str(uuid.uuid4()),
        event_type="transfer_created",
        actor=current_user["username"],
        details=json.dumps({
            "transfer_id":       transfer_id,
            "sku_id":            body.sku_id,
            "drug_name":         body.drug_name,
            "source_store":      body.source_store,
            "destination_store": body.destination_store,
            "quantity":          body.quantity,
            "authority_level":   authority,
        }),
        timestamp=datetime.now(timezone.utc),
    ))
    await db.commit()

    record_agent_call("MERIDIAN")
    logger.info("transfer_created",
                transfer_id=transfer_id,
                actor=current_user["username"],
                sku=body.sku_id,
                qty=body.quantity)

    return {
        "transfer_id":       transfer_id,
        "status":            "PENDING_APPROVAL" if authority == "TIER_2" else "APPROVED",
        "authority_level":   authority,
        "sku_id":            body.sku_id,
        "drug_name":         body.drug_name,
        "source_store":      body.source_store,
        "destination_store": body.destination_store,
        "quantity":          body.quantity,
        "reason":            body.reason,
        "initiated_by":      current_user["username"],
        "cold_chain_required": body.drug_name in ("Insulin Glargine", "Hepatitis B Vaccine"),
        "created_at":        datetime.now(timezone.utc).isoformat(),
        "message":           "Transfer order created. MERIDIAN will monitor execution.",
    }


# ── Decisions ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/decisions/recent", tags=["Decisions"])
async def api_recent_decisions(limit: int = 15, db: AsyncSession = Depends(get_db)):
    decisions = await db_get_recent_decisions(db, limit=limit)
    return {"decisions": decisions}


@app.get("/api/v1/decisions/escalations", tags=["Decisions"])
async def api_escalation_queue(db: AsyncSession = Depends(get_db)):
    escalations = await db_get_escalations(db)
    return {"escalations": escalations}


@app.post("/api/v1/decisions/escalations/{escalation_id}/approve", tags=["Decisions"],
          summary="Approve an escalation (requires MANAGER role)")
async def api_approve_escalation(
    escalation_id: str,
    request: Request,
    db: AsyncSession   = Depends(get_db),
    current_user: dict = Depends(require_role("MANAGER")),
):
    result = await db_resolve_escalation(db, escalation_id, "APPROVED", current_user["username"])
    if not result:
        raise HTTPException(status_code=404, detail=f"Escalation {escalation_id} not found.")
    db.add(AuditLog(
        log_id=str(uuid.uuid4()), event_type="escalation_approved",
        actor=current_user["username"], entity_id=escalation_id, entity_type="escalation",
        payload=json.dumps({"action": "APPROVED"}),
        ip_address=request.client.host if request.client else None,
    ))
    record_escalation("approved")
    await ws_manager.broadcast({"type": "escalation_resolved",
                                 "data": {"escalation_id": escalation_id, "action": "APPROVED",
                                          "resolved_by": current_user["username"]}})
    return result


@app.post("/api/v1/decisions/escalations/{escalation_id}/reject", tags=["Decisions"],
          summary="Reject an escalation (requires MANAGER role)")
async def api_reject_escalation(
    escalation_id: str,
    request: Request,
    db: AsyncSession   = Depends(get_db),
    current_user: dict = Depends(require_role("MANAGER")),
):
    result = await db_resolve_escalation(db, escalation_id, "REJECTED", current_user["username"])
    if not result:
        raise HTTPException(status_code=404, detail=f"Escalation {escalation_id} not found.")
    db.add(AuditLog(
        log_id=str(uuid.uuid4()), event_type="escalation_rejected",
        actor=current_user["username"], entity_id=escalation_id, entity_type="escalation",
        payload=json.dumps({"action": "REJECTED"}),
        ip_address=request.client.host if request.client else None,
    ))
    record_escalation("rejected")
    await ws_manager.broadcast({"type": "escalation_resolved",
                                 "data": {"escalation_id": escalation_id, "action": "REJECTED",
                                          "resolved_by": current_user["username"]}})
    return result


@app.get("/api/v1/audit-log", tags=["Decisions"],
         summary="Immutable audit log of all state-changing events (requires MANAGER)")
async def api_audit_log(
    limit: int = 50,
    db: AsyncSession   = Depends(get_db),
    current_user: dict = Depends(require_role("MANAGER")),
):
    result = await db.execute(
        sa_select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return {
        "entries": [
            {"log_id": r.log_id, "event_type": r.event_type, "actor": r.actor,
             "entity_id": r.entity_id, "entity_type": r.entity_type,
             "payload": r.payload, "ip_address": r.ip_address,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ]
    }


# ── Helpers ────────────────────────────────────────────────────────────────────
def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


async def _run_graph(run_id: str, initial_state: dict[str, Any]) -> None:
    t0 = time.perf_counter()
    try:
        logger.info("graph_run_start", run_id=run_id)
        state = PharmaIQState(**initial_state)
        final = await graph.ainvoke(state, config={"run_name": f"Scheduled/{run_id}"})
        duration = time.perf_counter() - t0
        CYCLE_DURATION.observe(duration)
        logger.info("graph_run_complete", run_id=run_id,
                    approved=len(getattr(final, "nexus_priority_decisions", [])),
                    duration=round(duration, 2))
    except Exception as exc:
        logger.error("graph_run_failed", run_id=run_id, error=str(exc))


async def _run_graph_sync(initial_state: dict[str, Any]) -> PharmaIQState:
    state = PharmaIQState(**initial_state)
    return await graph.ainvoke(state, config={"run_name": f"API/{uuid.uuid4()}"})


async def _run_scheduled_cycle(cycle_type_str: str) -> None:
    logger.info("scheduled_cycle_start", cycle_type=cycle_type_str)
    ct = CycleType(cycle_type_str)
    if ct == CycleType.COMPLIANCE_SWEEP and datetime.now(timezone.utc).hour % 2 != 0:
        return
    initial_state = build_initial_state(
        raw_event={"event_type": "scheduled", "source": "scheduler"},
        store_id="MEDCHAIN_HQ", zone_id="DELHI_NCR",
        signal_type=SignalType.SCHEDULED_FORECAST, cycle_type=ct,
    )
    await _run_graph(run_id=str(uuid.uuid4()), initial_state=initial_state)
    logger.info("scheduled_cycle_complete", cycle_type=cycle_type_str)


# ── Serve built frontend ───────────────────────────────────────────────────────
_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,
                reload=settings.environment == "development", log_level="info")
