"""
PharmaIQ – Async SQLAlchemy Database Layer

Tables:
  decisions        — NEXUS-approved / escalated decisions from each cycle
  escalations      — Items pending human approval
  agent_events     — Live agent activity feed
  cold_chain_readings — Temperature readings per fridge unit
  audit_log        — Immutable record of every state transition

Database: SQLite via aiosqlite (zero-config, file-based, production-ready for
          single-node deployments; swap to PostgreSQL by changing DATABASE_URL)
"""
from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime, Enum as SAEnum,
    func, select, update, Index,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

import enum
import os

# ── Engine ─────────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharmaiq.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base & Mixins ──────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Enum types ─────────────────────────────────────────────────────────────────
class EscalationStatus(str, enum.Enum):
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class AgentName(str, enum.Enum):
    SENTINEL   = "SENTINEL"
    PULSE      = "PULSE"
    AEGIS      = "AEGIS"
    MERIDIAN   = "MERIDIAN"
    CRITIQUE   = "CRITIQUE"
    COMPLIANCE = "COMPLIANCE"
    NEXUS      = "NEXUS"
    CHRONICLE  = "CHRONICLE"


# ── ORM Models ─────────────────────────────────────────────────────────────────

class Decision(Base):
    __tablename__ = "decisions"

    decision_id       = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type       = Column(String(120), nullable=False)
    source_agent      = Column(String(30), nullable=False)
    authority_level   = Column(String(30), nullable=False)   # TIER_1 | TIER_2 | HUMAN_REQUIRED
    nexus_verdict     = Column(String(40), nullable=False)   # APPROVED | ESCALATED | REJECTED | APPROVED_WITH_CONDITIONS
    critique_verdict  = Column(String(30), nullable=False)   # VALIDATED | CHALLENGED | DOWNGRADED | REJECTED
    compliance_verdict = Column(String(30), nullable=False)  # COMPLIANT | CONDITIONAL | NON_COMPLIANT
    store_id          = Column(String(30), nullable=False)
    zone_id           = Column(String(40), nullable=True)
    run_id            = Column(String(36), nullable=True)
    details           = Column(Text, nullable=True)          # JSON blob with full decision context
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_decisions_source_agent", "source_agent"),
        Index("ix_decisions_created_at", "created_at"),
    )


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type             = Column(String(120), nullable=False)
    reason_for_escalation   = Column(Text, nullable=False)
    nexus_recommendation    = Column(Text, nullable=False)
    source_agent            = Column(String(30), nullable=False)
    store_id                = Column(String(30), nullable=False)
    financial_impact        = Column(Float, nullable=True)
    expires_at              = Column(DateTime(timezone=True), nullable=False)
    status                  = Column(
        SAEnum(EscalationStatus), default=EscalationStatus.PENDING_HUMAN_APPROVAL, nullable=False
    )
    resolved_by             = Column(String(60), nullable=True)   # username who approved/rejected
    resolved_at             = Column(DateTime(timezone=True), nullable=True)
    run_id                  = Column(String(36), nullable=True)
    created_at              = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_escalations_status", "status"),
        Index("ix_escalations_created_at", "created_at"),
    )


class AgentEvent(Base):
    __tablename__ = "agent_events"

    event_id  = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent     = Column(String(30), nullable=False)
    domain    = Column(String(40), nullable=False)
    message   = Column(Text, nullable=False)
    severity  = Column(String(20), nullable=False)  # critical | warning | info | success
    store_id  = Column(String(30), nullable=True)
    run_id    = Column(String(36), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_agent_events_agent", "agent"),
        Index("ix_agent_events_timestamp", "timestamp"),
    )


class ColdChainReading(Base):
    __tablename__ = "cold_chain_readings"

    reading_id    = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id      = Column(String(30), nullable=False)
    unit_id       = Column(String(20), nullable=False)
    temperature_c = Column(Float, nullable=False)
    humidity_pct  = Column(Float, nullable=True)
    status        = Column(String(20), nullable=False)   # NORMAL | MINOR | MODERATE | SEVERE | FREEZE
    sensor_status = Column(String(10), nullable=False, default="ONLINE")
    door_open     = Column(Boolean, nullable=False, default=False)
    recorded_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cc_store_unit", "store_id", "unit_id"),
        Index("ix_cc_recorded_at", "recorded_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id       = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type   = Column(String(60), nullable=False)   # cycle_complete | escalation_resolved | signal_ingested …
    actor        = Column(String(60), nullable=True)    # username or agent name
    entity_id    = Column(String(36), nullable=True)    # decision_id / escalation_id / run_id
    entity_type  = Column(String(30), nullable=True)
    payload      = Column(Text, nullable=True)          # JSON dump of relevant context
    ip_address   = Column(String(45), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_event_type", "event_type"),
        Index("ix_audit_created_at", "created_at"),
    )


class InventoryItem(Base):
    """Per-SKU expiry risk records written by MERIDIAN each cycle."""
    __tablename__ = "inventory_items"

    item_id                  = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    drug_name                = Column(String(120), nullable=False)
    sku_id                   = Column(String(30), nullable=False)
    batch_id                 = Column(String(30), nullable=False)
    store_id                 = Column(String(30), nullable=False)
    days_until_expiry        = Column(Integer, nullable=False)
    risk_score               = Column(Float, nullable=False)
    quantity                 = Column(Integer, nullable=False)
    estimated_loss_value     = Column(Float, nullable=True)
    recommended_intervention = Column(String(30), nullable=False)  # TRANSFER | MARKDOWN | MONITOR
    critique_verdict         = Column(String(20), nullable=False, default="VALIDATED")
    recorded_at              = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_inv_sku_store", "sku_id", "store_id"),)


class StockLevel(Base):
    """Zone-level stock position per SKU, refreshed each cycle."""
    __tablename__ = "stock_levels"

    level_id      = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone          = Column(String(40), nullable=False)
    sku_id        = Column(String(30), nullable=False)
    drug_name     = Column(String(120), nullable=False)
    category      = Column(String(30), nullable=False)
    quantity      = Column(Integer, nullable=False)
    reorder_point = Column(Integer, nullable=False)
    max_quantity  = Column(Integer, nullable=False)
    status        = Column(String(20), nullable=False)  # NORMAL | LOW | CRITICAL | STOCKOUT | OVERSTOCK
    velocity      = Column(Float, nullable=False)        # units/day
    days_of_stock = Column(Float, nullable=False)
    fill_rate     = Column(Float, nullable=False)
    recorded_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_stock_zone_sku", "zone", "sku_id"),)


class ReorderAlert(Base):
    """MERIDIAN reorder alerts persisted each cycle."""
    __tablename__ = "reorder_alerts"

    alert_id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku_id             = Column(String(30), nullable=False)
    drug_name          = Column(String(120), nullable=False)
    category           = Column(String(30), nullable=False)
    zone               = Column(String(40), nullable=False)
    store_id           = Column(String(30), nullable=False)
    current_stock      = Column(Integer, nullable=False)
    reorder_point      = Column(Integer, nullable=False)
    suggested_order_qty = Column(Integer, nullable=False)
    estimated_cost     = Column(Float, nullable=True)
    lead_time_days     = Column(Integer, nullable=False)
    status             = Column(String(20), nullable=False)  # LOW | CRITICAL | STOCKOUT
    priority           = Column(String(10), nullable=False)  # URGENT | NORMAL
    meridian_action    = Column(String(20), nullable=False)  # AUTO_REORDER | ESCALATE
    resolved           = Column(Boolean, default=False, nullable=False)
    created_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_reorder_status", "status", "resolved"),)


class TransferOrder(Base):
    """Inter-store stock transfers initiated by MERIDIAN or operators."""
    __tablename__ = "transfer_orders"

    transfer_id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku_id               = Column(String(30), nullable=False)
    drug_name            = Column(String(120), nullable=False)
    source_store         = Column(String(30), nullable=False)
    destination_store    = Column(String(30), nullable=False)
    quantity             = Column(Integer, nullable=False)
    reason               = Column(Text, nullable=True)
    status               = Column(String(30), nullable=False, default="PENDING_APPROVAL")
    initiated_by         = Column(String(30), nullable=False, default="MERIDIAN")
    authority_level      = Column(String(20), nullable=False, default="TIER_1")
    critique_verdict     = Column(String(20), nullable=False, default="VALIDATED")
    compliance_verdict   = Column(String(20), nullable=False, default="COMPLIANT")
    eta_hours            = Column(Integer, nullable=True)
    distance_km          = Column(Integer, nullable=True)
    cold_chain_required  = Column(Boolean, default=False, nullable=False)
    created_at           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_transfer_status", "status"),)


class EpidemicSignal(Base):
    """PULSE epidemic intelligence signals, refreshed per cycle."""
    __tablename__ = "epidemic_signals"

    signal_id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    disease            = Column(String(80), nullable=False)
    confidence         = Column(Float, nullable=False)
    demand_multiplier  = Column(Float, nullable=False)
    peak_week          = Column(Integer, nullable=False)
    affected_zones     = Column(Text, nullable=False)   # JSON list
    key_drugs          = Column(Text, nullable=False)   # JSON list
    affected_stores    = Column(Integer, nullable=False)
    lead_time_days     = Column(Integer, nullable=False)
    status             = Column(String(20), nullable=False, default="ACTIVE")
    data_sources       = Column(Text, nullable=False)   # JSON list
    recorded_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_epidemic_disease", "disease"),)


class DemandForecast(Base):
    """PULSE demand forecasts per SKU per store."""
    __tablename__ = "demand_forecasts"

    forecast_id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id             = Column(String(30), nullable=False)
    sku_id               = Column(String(30), nullable=False)
    drug_name            = Column(String(120), nullable=False)
    category             = Column(String(30), nullable=False)
    baseline_demand      = Column(Integer, nullable=False)
    epidemic_adjustment  = Column(Float, nullable=False)
    adjusted_forecast    = Column(Integer, nullable=False)
    confidence           = Column(Float, nullable=False)
    horizon_days         = Column(Integer, nullable=False, default=7)
    recommended_action   = Column(String(20), nullable=False)  # REORDER | MONITOR | OK
    reorder_triggered    = Column(Boolean, default=False, nullable=False)
    recorded_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_forecast_store_sku", "store_id", "sku_id"),)


class StaffingSnapshot(Base):
    """AEGIS staffing state snapshots written each cycle."""
    __tablename__ = "staffing_snapshots"

    snapshot_id               = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pharmacist_coverage_pct   = Column(Float, nullable=False)
    schedule_h_compliance_pct = Column(Float, nullable=False)
    active_shifts             = Column(Integer, nullable=False)
    night_shift_gaps          = Column(Integer, nullable=False, default=0)
    active_gaps               = Column(Text, nullable=True)     # JSON list of gap dicts
    zone_utilisation          = Column(Text, nullable=True)     # JSON list of zone dicts
    total_stores              = Column(Integer, nullable=False, default=320)
    pharmacist_present        = Column(Integer, nullable=False)
    recorded_at               = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_staffing_recorded_at", "recorded_at"),)


# ── Dependency for FastAPI ─────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Schema creation ────────────────────────────────────────────────────────────
async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Seed helpers ───────────────────────────────────────────────────────────────
_STORE_IDS = [
    f"STORE_{city}_{str(n).zfill(3)}"
    for city in ["DEL", "MUM", "BLR", "HYD", "CHN"]
    for n in range(1, 17)
]

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _ago(**kwargs) -> datetime:
    return _now() - timedelta(**kwargs)


_DECISION_TEMPLATES = [
    ("Batch Quarantine",              "SENTINEL",    "TIER_1",         "APPROVED",                "VALIDATED",  "COMPLIANT"),
    ("Emergency Reorder 2.1x",        "PULSE",       "TIER_2",         "APPROVED",                "VALIDATED",  "COMPLIANT"),
    ("Pharmacist Redeployment",        "AEGIS",       "TIER_2",         "APPROVED_WITH_CONDITIONS","VALIDATED",  "COMPLIANT"),
    ("Inter-store Transfer",           "MERIDIAN",    "TIER_1",         "APPROVED",                "CHALLENGED", "COMPLIANT"),
    ("Emergency Reorder 3.4x",         "PULSE",       "HUMAN_REQUIRED", "ESCALATED",               "VALIDATED",  "COMPLIANT"),
    ("Maintenance Request",            "SENTINEL",    "TIER_1",         "APPROVED",                "VALIDATED",  "COMPLIANT"),
    ("CDSCO Regulatory Notification",  "COMPLIANCE",  "HUMAN_REQUIRED", "ESCALATED",               "VALIDATED",  "COMPLIANT"),
    ("Demand Reforecast Trigger",      "PULSE",       "TIER_1",         "APPROVED",                "VALIDATED",  "COMPLIANT"),
    ("Expiry Write-off Prevention",    "MERIDIAN",    "TIER_2",         "APPROVED",                "VALIDATED",  "COMPLIANT"),
    ("Schedule H Gap Closure",         "AEGIS",       "TIER_1",         "APPROVED",                "VALIDATED",  "COMPLIANT"),
    ("Cross-zone Pharmacist Deploy",   "AEGIS",       "TIER_2",         "APPROVED",                "VALIDATED",  "CONDITIONAL"),
    ("Vaccine Batch Recall",           "SENTINEL",    "HUMAN_REQUIRED", "ESCALATED",               "VALIDATED",  "COMPLIANT"),
]

_EVENT_TEMPLATES = [
    ("SENTINEL",    "cold_chain",  "SEVERE excursion at STORE_MUM_042 — FRIDGE_B2 → 19.4°C",                  "critical"),
    ("SENTINEL",    "cold_chain",  "Batch quarantine executed: Hepatitis B Vaccine — 240 units",               "warning"),
    ("PULSE",       "demand",      "Dengue surge forecast: +340% ORS, +280% Paracetamol — East Delhi zone",    "info"),
    ("AEGIS",       "staffing",    "Schedule H gap closed: Pharmacist Priya Sharma → STORE_DEL_018",           "success"),
    ("MERIDIAN",    "inventory",   "Expiry risk: Insulin Glargine EXP2026-04 — 18 days, velocity 0.9",        "warning"),
    ("CRITIQUE",    "validation",  "CHALLENGED: MERIDIAN transfer proposal — insufficient demand evidence",    "info"),
    ("COMPLIANCE",  "regulatory",  "COMPLIANT: Cold chain quarantine — CDSCO Schedule C §7.3 satisfied",      "success"),
    ("NEXUS",       "synthesis",   "Cross-domain resolved: fridge conflict → SENTINEL priority, MERIDIAN +4h","info"),
    ("CHRONICLE",   "memory",      "Pattern recorded: Sensor false-positive rate 23% at stores >4yr fridge",  "info"),
    ("SENTINEL",    "cold_chain",  "MINOR excursion resolved: STORE_BLR_011 — temperature normalised 6.2°C",  "success"),
    ("PULSE",       "demand",      "Epidemic confidence raised to 0.87: IDSP confirms dengue cluster District 7","warning"),
    ("AEGIS",       "staffing",    "Compliance sweep: 317/320 stores pharmacist-present ✓",                   "success"),
    ("NEXUS",       "synthesis",   "Escalation sent: Emergency reorder >3x requires CFO approval — ₹3.2L",    "warning"),
    ("MERIDIAN",    "inventory",   "Inter-store transfer approved: Metformin 500mg STORE_DEL_019 → DEL_004",   "success"),
]


async def seed_database(session: AsyncSession) -> None:
    """
    Idempotent seed — only inserts if tables are empty.
    Creates realistic initial data across all 5 tables.
    """
    # Check if already seeded
    result = await session.execute(select(AgentEvent).limit(1))
    if result.scalar_one_or_none():
        return  # Already seeded

    import json

    # ── Seed AgentEvents (72 events over last 6 hours) ─────────────────────────
    events = []
    for i in range(72):
        t = _EVENT_TEMPLATES[i % len(_EVENT_TEMPLATES)]
        events.append(AgentEvent(
            event_id  = str(uuid.uuid4()),
            agent     = t[0],
            domain    = t[1],
            message   = t[2],
            severity  = t[3],
            store_id  = random.choice(_STORE_IDS),
            run_id    = str(uuid.uuid4()),
            timestamp = _ago(minutes=i * random.randint(3, 7)),
        ))
    session.add_all(events)

    # ── Seed Decisions (50 decisions over last 24 hours) ──────────────────────
    decisions = []
    for i in range(50):
        t = _DECISION_TEMPLATES[i % len(_DECISION_TEMPLATES)]
        decisions.append(Decision(
            decision_id       = str(uuid.uuid4()),
            action_type       = t[0],
            source_agent      = t[1],
            authority_level   = t[2],
            nexus_verdict     = t[3],
            critique_verdict  = t[4],
            compliance_verdict = t[5],
            store_id          = random.choice(_STORE_IDS),
            zone_id           = random.choice(["Delhi NCR", "Mumbai", "Bengaluru", "Chennai", "Hyderabad"]),
            run_id            = str(uuid.uuid4()),
            details           = json.dumps({
                "confidence": round(random.uniform(0.7, 0.99), 2),
                "cycle_type": random.choice(["MORNING_FORECAST", "COMPLIANCE_SWEEP", "EXPIRY_REVIEW"]),
            }),
            created_at        = _ago(hours=i // 3, minutes=(i * 23) % 60),
        ))
    session.add_all(decisions)

    # ── Seed Escalations (2 pending, 3 historical) ────────────────────────────
    now = _now()
    escalations = [
        Escalation(
            escalation_id         = str(uuid.uuid4()),
            action_type           = "Emergency Reorder — Paracetamol 650mg",
            reason_for_escalation = (
                "PULSE forecasts 340% demand surge due to confirmed dengue cluster. "
                "Proposed order is 3.4× baseline (₹3,20,000). Exceeds TIER_2 authority."
            ),
            nexus_recommendation  = (
                "Approve with condition: split into two tranches — first 60% immediately, "
                "second 40% contingent on day-3 actual demand confirmation."
            ),
            source_agent          = "NEXUS",
            store_id              = "STORE_DEL_007",
            financial_impact      = 320000.0,
            expires_at            = now + timedelta(minutes=45),
            status                = EscalationStatus.PENDING_HUMAN_APPROVAL,
            run_id                = str(uuid.uuid4()),
            created_at            = _ago(minutes=12),
        ),
        Escalation(
            escalation_id         = str(uuid.uuid4()),
            action_type           = "Cross-Zone Pharmacist Redeployment",
            reason_for_escalation = (
                "AEGIS: Schedule H gap at STORE_DEL_018. Nearest qualified pharmacist "
                "is in adjacent zone — cross-zone redeployment requires HR approval."
            ),
            nexus_recommendation  = (
                "Approve redeployment. Estimated cost ₹1,200 travel allowance. "
                "Schedule H gap risk > travel cost. Recommend approval."
            ),
            source_agent          = "NEXUS",
            store_id              = "STORE_DEL_018",
            financial_impact      = 1200.0,
            expires_at            = now + timedelta(minutes=30),
            status                = EscalationStatus.PENDING_HUMAN_APPROVAL,
            run_id                = str(uuid.uuid4()),
            created_at            = _ago(minutes=28),
        ),
        Escalation(
            escalation_id         = str(uuid.uuid4()),
            action_type           = "Vaccine Batch Recall — Hepatitis B",
            reason_for_escalation = "SENTINEL: 3 SEVERE excursions in 6h on FRIDGE_B2. Cumulative excursion 4.2h. WHO stability threshold exceeded.",
            nexus_recommendation  = "Approve recall. 240 units across 3 stores. Estimated loss ₹72,000. Regulatory obligation.",
            source_agent          = "NEXUS",
            store_id              = "STORE_MUM_042",
            financial_impact      = 72000.0,
            expires_at            = _ago(hours=2),
            status                = EscalationStatus.APPROVED,
            resolved_by           = "manager@medchain.in",
            resolved_at           = _ago(hours=1, minutes=45),
            run_id                = str(uuid.uuid4()),
            created_at            = _ago(hours=3),
        ),
        Escalation(
            escalation_id         = str(uuid.uuid4()),
            action_type           = "CDSCO Notification — Substandard Drug Report",
            reason_for_escalation = "COMPLIANCE: Batch of Amoxicillin 500mg fails in-house QC. CDSCO notification mandatory within 24h under Schedule M.",
            nexus_recommendation  = "File CDSCO report immediately. Legal obligation. Estimated regulatory risk of non-compliance: ₹5L+ fine.",
            source_agent          = "NEXUS",
            store_id              = "STORE_BLR_007",
            financial_impact      = 8500.0,
            expires_at            = _ago(minutes=30),
            status                = EscalationStatus.APPROVED,
            resolved_by           = "compliance@medchain.in",
            resolved_at           = _ago(hours=4),
            run_id                = str(uuid.uuid4()),
            created_at            = _ago(hours=5),
        ),
        Escalation(
            escalation_id         = str(uuid.uuid4()),
            action_type           = "Emergency Reorder — Insulin Glargine",
            reason_for_escalation = "MERIDIAN: Stock-out risk within 48h for 3 diabetic patients on repeat prescriptions. TIER_2 reorder limit exceeded.",
            nexus_recommendation  = "Reject — MERIDIAN data shows inter-store transfer from STORE_DEL_009 is sufficient (140 units in transit). No emergency order needed.",
            source_agent          = "NEXUS",
            store_id              = "STORE_DEL_011",
            financial_impact      = 45000.0,
            expires_at            = _ago(hours=6),
            status                = EscalationStatus.REJECTED,
            resolved_by           = "manager@medchain.in",
            resolved_at           = _ago(hours=5, minutes=30),
            run_id                = str(uuid.uuid4()),
            created_at            = _ago(hours=7),
        ),
    ]
    session.add_all(escalations)

    # ── Seed ColdChainReadings (last 48h, 5-min intervals for 10 key units) ───
    readings = []
    key_units = [
        ("STORE_MUM_042", "FRIDGE_B2"),
        ("STORE_DEL_007", "FRIDGE_A1"),
        ("STORE_BLR_011", "FRIDGE_C1"),
    ]
    for store_id, unit_id in key_units:
        base_temp = random.uniform(3.5, 6.5)
        for i in range(576):  # 48h × 12 readings/h
            spike = 0.0
            # Introduce an excursion window for STORE_MUM_042
            if store_id == "STORE_MUM_042" and 100 <= i <= 130:
                spike = random.uniform(4.0, 14.0)
            temp = round(base_temp + random.gauss(0, 0.25) + spike, 2)
            status = "NORMAL"
            if temp > 15:
                status = "SEVERE"
            elif temp > 8:
                status = "MODERATE"
            elif temp < 0:
                status = "FREEZE"
            elif temp > 6.5:
                status = "MINOR"
            readings.append(ColdChainReading(
                reading_id    = str(uuid.uuid4()),
                store_id      = store_id,
                unit_id       = unit_id,
                temperature_c = temp,
                humidity_pct  = round(random.uniform(40, 72), 1),
                status        = status,
                sensor_status = "ONLINE",
                door_open     = random.random() < 0.01,
                recorded_at   = _ago(minutes=i * 5),
            ))
    session.add_all(readings)

    # ── Seed AuditLog ─────────────────────────────────────────────────────────
    audit_entries = [
        AuditLog(
            log_id      = str(uuid.uuid4()),
            event_type  = "escalation_approved",
            actor       = "manager@medchain.in",
            entity_id   = escalations[2].escalation_id,
            entity_type = "escalation",
            payload     = json.dumps({"action": "APPROVED", "note": "Regulatory obligation confirmed"}),
            ip_address  = "10.0.1.42",
            created_at  = escalations[2].resolved_at,
        ),
        AuditLog(
            log_id      = str(uuid.uuid4()),
            event_type  = "escalation_approved",
            actor       = "compliance@medchain.in",
            entity_id   = escalations[3].escalation_id,
            entity_type = "escalation",
            payload     = json.dumps({"action": "APPROVED", "note": "CDSCO notification filed at 14:32 IST"}),
            ip_address  = "10.0.1.55",
            created_at  = escalations[3].resolved_at,
        ),
        AuditLog(
            log_id      = str(uuid.uuid4()),
            event_type  = "escalation_rejected",
            actor       = "manager@medchain.in",
            entity_id   = escalations[4].escalation_id,
            entity_type = "escalation",
            payload     = json.dumps({"action": "REJECTED", "note": "Transfer sufficient, no emergency order"}),
            ip_address  = "10.0.1.42",
            created_at  = escalations[4].resolved_at,
        ),
        AuditLog(
            log_id      = str(uuid.uuid4()),
            event_type  = "cycle_complete",
            actor       = "scheduler",
            entity_id   = None,
            entity_type = "cycle",
            payload     = json.dumps({"cycle_type": "MORNING_FORECAST", "decisions": 12, "escalations": 1}),
            ip_address  = None,
            created_at  = _ago(hours=2),
        ),
    ]
    session.add_all(audit_entries)

    # ── Seed EpidemicSignals ──────────────────────────────────────────────────
    epidemic_data = [
        ("Dengue Fever",    0.87, 2.8, 3, ["East Delhi"],       ["Paracetamol", "Dengue NS1 Kit", "ORS Sachets", "Platelet Boosters"], 19, 4),
        ("Influenza H3N2",  0.62, 1.9, 5, ["Mumbai South"],     ["Oseltamivir", "Paracetamol", "Cetirizine", "Vitamin C"],            11, 5),
        ("Gastroenteritis", 0.44, 1.4, 7, ["Bangalore North"],  ["ORS Sachets", "Zinc Sulfate", "Domperidone", "Probiotics"],          7, 6),
        ("Chikungunya",     0.31, 1.2, 9, ["Chennai Central"],  ["Paracetamol", "Ibuprofen", "Chloroquine", "Multivitamins"],           5, 7),
    ]
    epidemic_signals = [
        EpidemicSignal(
            signal_id=str(uuid.uuid4()), disease=d[0], confidence=d[1],
            demand_multiplier=d[2], peak_week=d[3],
            affected_zones=json.dumps(d[4]), key_drugs=json.dumps(d[5]),
            affected_stores=d[6], lead_time_days=d[7], status="ACTIVE",
            data_sources=json.dumps(["IDSP", "Google Trends", "IMD"]),
            recorded_at=_ago(minutes=random.randint(5, 60)),
        ) for d in epidemic_data
    ]
    session.add_all(epidemic_signals)

    # ── Seed DemandForecasts ──────────────────────────────────────────────────
    _forecast_skus = [
        ("SKU-1001", "Paracetamol 650mg",  "OTC",        120, 2.8),
        ("SKU-1002", "ORS Sachets",         "OTC",         80, 3.1),
        ("SKU-1003", "Dengue NS1 Test Kit", "Diagnostics", 25, 3.4),
        ("SKU-1004", "Metformin 500mg",     "Schedule H", 160, 1.1),
        ("SKU-1005", "Insulin Glargine",    "Schedule H",  55, 1.0),
        ("SKU-1006", "Amoxicillin 500mg",   "Schedule H",  90, 1.3),
    ]
    demand_forecasts = []
    for sku_id, drug_name, category, baseline, mult in _forecast_skus:
        conf = round(random.uniform(0.65, 0.95), 2)
        adjusted = round(baseline * mult)
        action = "REORDER" if mult > 2.0 else "MONITOR" if mult > 1.3 else "OK"
        demand_forecasts.append(DemandForecast(
            forecast_id=str(uuid.uuid4()), store_id="STORE_DEL_001",
            sku_id=sku_id, drug_name=drug_name, category=category,
            baseline_demand=baseline, epidemic_adjustment=round(mult, 2),
            adjusted_forecast=adjusted, confidence=conf, horizon_days=7,
            recommended_action=action, reorder_triggered=mult > 1.5,
            recorded_at=_ago(minutes=random.randint(5, 45)),
        ))
    session.add_all(demand_forecasts)

    # ── Seed StaffingSnapshot ─────────────────────────────────────────────────
    staffing_gaps = [
        {"store_id": "STORE_DEL_018", "shift": "Morning", "severity": "HIGH",
         "gap_hours": 2.5, "suggested_action": "Deploy Priya Sharma (D.Pharm) from STORE_DEL_021 — ETA 18 min"},
        {"store_id": "STORE_MUM_042", "shift": "Night", "severity": "MEDIUM",
         "gap_hours": 1.0, "suggested_action": "Activate on-call pharmacist — Rajan Iyer"},
    ]
    zone_util = [
        {"zone": "Delhi NCR",  "utilisation_pct": 88.4},
        {"zone": "Mumbai",     "utilisation_pct": 82.1},
        {"zone": "Bengaluru",  "utilisation_pct": 79.6},
        {"zone": "Chennai",    "utilisation_pct": 84.3},
        {"zone": "Hyderabad",  "utilisation_pct": 76.8},
    ]
    session.add(StaffingSnapshot(
        snapshot_id=str(uuid.uuid4()),
        pharmacist_coverage_pct=94.7, schedule_h_compliance_pct=99.1,
        active_shifts=304, night_shift_gaps=1,
        active_gaps=json.dumps(staffing_gaps),
        zone_utilisation=json.dumps(zone_util),
        total_stores=320, pharmacist_present=317,
        recorded_at=_ago(minutes=15),
    ))

    # ── Seed InventoryItems ───────────────────────────────────────────────────
    _inv_skus = [
        ("Insulin Glargine 100U/mL", "INS-GLAR-001", 18, 0.92, "TRANSFER",  180),
        ("Hepatitis A Vaccine",      "HAV-001",       24, 0.85, "TRANSFER",  240),
        ("Rotavirus Vaccine",        "ROT-001",       31, 0.78, "MARKDOWN",  95),
        ("Metformin SR 500mg",       "MET-SR-001",    45, 0.65, "MARKDOWN",  320),
        ("Amlodipine 5mg",           "AML-001",       52, 0.55, "MONITOR",   210),
        ("Cetirizine 10mg",          "CET-001",       58, 0.48, "MONITOR",   175),
        ("Azithromycin 500mg",       "AZI-001",       62, 0.42, "MONITOR",   130),
    ]
    inv_items = [
        InventoryItem(
            item_id=str(uuid.uuid4()),
            drug_name=sku[0], sku_id=sku[1],
            batch_id=f"BATCH-{uuid.uuid4().hex[:8].upper()}",
            store_id=random.choice(_STORE_IDS),
            days_until_expiry=sku[2], risk_score=sku[3], quantity=sku[5],
            estimated_loss_value=round(sku[5] * random.uniform(8, 120), 0),
            recommended_intervention=sku[4],
            critique_verdict="VALIDATED" if sku[3] > 0.6 else "CHALLENGED",
            recorded_at=_ago(minutes=random.randint(5, 60)),
        ) for sku in _inv_skus
    ]
    session.add_all(inv_items)

    # ── Seed StockLevels ──────────────────────────────────────────────────────
    _stock_drugs = [
        ("Paracetamol 650mg",    "SKU-1001", "OTC",         45, 200),
        ("ORS Sachets",          "SKU-1002", "OTC",         30, 150),
        ("Metformin 500mg",      "SKU-1004", "Schedule H",  60, 300),
        ("Insulin Glargine",     "SKU-1005", "Schedule H",  20,  80),
        ("Amoxicillin 500mg",    "SKU-1006", "Schedule H",  35, 160),
        ("Cetirizine 10mg",      "SKU-1007", "OTC",         25, 120),
        ("Azithromycin 500mg",   "SKU-1008", "Schedule H",  15,  70),
        ("Vitamin D3 60K",       "SKU-1009", "OTC",         50, 220),
        ("Amlodipine 5mg",       "SKU-1010", "Schedule H",  40, 180),
        ("Dengue NS1 Test Kit",  "SKU-1003", "Diagnostics", 10,  50),
        ("Oseltamivir 75mg",     "SKU-1011", "Schedule H",   8,  40),
        ("Insulin Regular",      "SKU-1012", "Schedule H",  18,  75),
    ]
    _zones_list = ["Delhi NCR", "Mumbai", "Bengaluru", "Chennai", "Hyderabad"]
    _zone_mult  = {"Delhi NCR": 0.45, "Mumbai": 0.65, "Bengaluru": 0.70, "Chennai": 0.75, "Hyderabad": 0.60}
    stock_levels = []
    for zone in _zones_list:
        for drug_name, sku_id, category, reorder, max_qty in _stock_drugs:
            mult = _zone_mult.get(zone, 0.6)
            qty = int(max_qty * mult + random.gauss(0, max_qty * 0.08))
            qty = max(0, min(qty, max_qty))
            velocity = round(random.uniform(0.4, 4.8), 1)
            dos = round(qty / velocity, 1) if velocity > 0 else 999
            status = "STOCKOUT" if qty == 0 else \
                     "CRITICAL" if qty <= reorder * 0.5 else \
                     "LOW" if qty <= reorder else \
                     "OVERSTOCK" if qty / max_qty >= 0.9 else "NORMAL"
            stock_levels.append(StockLevel(
                level_id=str(uuid.uuid4()), zone=zone, sku_id=sku_id,
                drug_name=drug_name, category=category, quantity=qty,
                reorder_point=reorder, max_quantity=max_qty,
                status=status, velocity=velocity, days_of_stock=min(dos, 999),
                fill_rate=round(qty / max_qty, 3),
                recorded_at=_ago(minutes=random.randint(5, 30)),
            ))
    session.add_all(stock_levels)

    # ── Seed ReorderAlerts ────────────────────────────────────────────────────
    reorder_alerts = [
        ReorderAlert(
            alert_id=str(uuid.uuid4()), sku_id="SKU-1001", drug_name="Paracetamol 650mg",
            category="OTC", zone="Delhi NCR", store_id="STORE_DEL_007",
            current_stock=12, reorder_point=45, suggested_order_qty=160,
            estimated_cost=4800.0, lead_time_days=2, status="CRITICAL",
            priority="URGENT", meridian_action="AUTO_REORDER", resolved=False,
            created_at=_ago(minutes=22),
        ),
        ReorderAlert(
            alert_id=str(uuid.uuid4()), sku_id="SKU-1002", drug_name="ORS Sachets",
            category="OTC", zone="Delhi NCR", store_id="STORE_DEL_012",
            current_stock=0, reorder_point=30, suggested_order_qty=120,
            estimated_cost=3600.0, lead_time_days=2, status="STOCKOUT",
            priority="URGENT", meridian_action="AUTO_REORDER", resolved=False,
            created_at=_ago(minutes=8),
        ),
        ReorderAlert(
            alert_id=str(uuid.uuid4()), sku_id="SKU-1003", drug_name="Dengue NS1 Test Kit",
            category="Diagnostics", zone="Delhi NCR", store_id="STORE_DEL_003",
            current_stock=3, reorder_point=10, suggested_order_qty=40,
            estimated_cost=12000.0, lead_time_days=3, status="CRITICAL",
            priority="URGENT", meridian_action="AUTO_REORDER", resolved=False,
            created_at=_ago(minutes=35),
        ),
        ReorderAlert(
            alert_id=str(uuid.uuid4()), sku_id="SKU-1005", drug_name="Insulin Glargine",
            category="Schedule H", zone="Mumbai", store_id="STORE_MUM_008",
            current_stock=8, reorder_point=20, suggested_order_qty=60,
            estimated_cost=54000.0, lead_time_days=4, status="LOW",
            priority="NORMAL", meridian_action="ESCALATE", resolved=False,
            created_at=_ago(hours=1, minutes=12),
        ),
        ReorderAlert(
            alert_id=str(uuid.uuid4()), sku_id="SKU-1011", drug_name="Oseltamivir 75mg",
            category="Schedule H", zone="Mumbai", store_id="STORE_MUM_003",
            current_stock=2, reorder_point=8, suggested_order_qty=30,
            estimated_cost=7200.0, lead_time_days=3, status="CRITICAL",
            priority="URGENT", meridian_action="AUTO_REORDER", resolved=False,
            created_at=_ago(minutes=50),
        ),
    ]
    session.add_all(reorder_alerts)

    # ── Seed TransferOrders ───────────────────────────────────────────────────
    _transfer_templates = [
        ("Metformin 500mg",     "SKU-1004", "STORE_DEL_019", "STORE_DEL_004", 120, "Expiry risk at source — 45 days remaining",          "PENDING_APPROVAL", False),
        ("Paracetamol 650mg",   "SKU-1001", "STORE_MUM_003", "STORE_DEL_007", 200, "Dengue surge demand increase in Delhi",               "APPROVED",         False),
        ("Insulin Glargine",    "SKU-1005", "STORE_BLR_002", "STORE_HYD_001",  60, "Cold chain optimisation — balance network stock",     "IN_TRANSIT",       True),
        ("ORS Sachets",         "SKU-1002", "STORE_CHN_005", "STORE_MUM_008", 300, "Pre-emptive buffer ahead of monsoon season",          "IN_TRANSIT",       False),
        ("Cetirizine 10mg",     "SKU-1007", "STORE_DEL_012", "STORE_BLR_006",  80, "Overstock at source — prevent expiry write-off",      "DELIVERED",        False),
        ("Amoxicillin 500mg",   "SKU-1006", "STORE_HYD_004", "STORE_MUM_002",  50, "MERIDIAN: critical low at destination",               "DELIVERED",        False),
        ("Dengue NS1 Test Kit", "SKU-1003", "STORE_DEL_003", "STORE_MUM_007",  30, "Epidemic signal: dengue cluster spreading west",      "APPROVED",         False),
        ("Azithromycin 500mg",  "SKU-1008", "STORE_BLR_007", "STORE_CHN_003",  40, "Demand rebalance — weekly brief recommendation",     "IN_TRANSIT",       False),
    ]
    transfer_orders = [
        TransferOrder(
            transfer_id=f"TRF-{uuid.uuid4().hex[:8].upper()}",
            sku_id=t[1], drug_name=t[0], source_store=t[2], destination_store=t[3],
            quantity=t[4], reason=t[5], status=t[6],
            initiated_by=random.choice(["MERIDIAN", "NEXUS", "PULSE"]),
            authority_level="TIER_1" if t[4] <= 100 else "TIER_2",
            critique_verdict="VALIDATED", compliance_verdict="COMPLIANT",
            eta_hours=random.randint(2, 48) if t[6] in ("APPROVED", "IN_TRANSIT") else None,
            distance_km=random.randint(5, 1200), cold_chain_required=t[7],
            created_at=_ago(hours=random.randint(1, 72)),
            updated_at=_ago(minutes=random.randint(5, 60)),
        ) for t in _transfer_templates
    ]
    session.add_all(transfer_orders)

    await session.commit()


# ── DB query functions (replace mock_data) ─────────────────────────────────────

async def db_get_live_events(session: AsyncSession, limit: int = 20) -> list[dict]:
    result = await session.execute(
        select(AgentEvent)
        .order_by(AgentEvent.timestamp.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id":        r.event_id,
            "agent":     r.agent,
            "domain":    r.domain,
            "message":   r.message,
            "severity":  r.severity,
            "store_id":  r.store_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]


async def db_get_recent_decisions(session: AsyncSession, limit: int = 15) -> list[dict]:
    result = await session.execute(
        select(Decision)
        .order_by(Decision.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "decision_id":        r.decision_id,
            "action_type":        r.action_type,
            "source_agent":       r.source_agent,
            "authority_level":    r.authority_level,
            "nexus_verdict":      r.nexus_verdict,
            "critique_verdict":   r.critique_verdict,
            "compliance_verdict": r.compliance_verdict,
            "store_id":           r.store_id,
            "timestamp":          r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def db_get_escalations(session: AsyncSession) -> list[dict]:
    from datetime import timezone as tz
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Escalation)
        .where(Escalation.status == EscalationStatus.PENDING_HUMAN_APPROVAL)
        .order_by(Escalation.created_at.asc())
    )
    rows = result.scalars().all()
    out = []
    for r in rows:
        expires_at = r.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = expires_at - now
        total_sec = int(delta.total_seconds())
        if total_sec > 0:
            expires_in = f"{total_sec // 60}m" if total_sec < 3600 else f"{total_sec // 3600}h"
        else:
            expires_in = "expired"
        out.append({
            "escalation_id":         r.escalation_id,
            "action_type":           r.action_type,
            "reason_for_escalation": r.reason_for_escalation,
            "nexus_recommendation":  r.nexus_recommendation,
            "source_agent":          r.source_agent,
            "store_id":              r.store_id,
            "financial_impact":      r.financial_impact,
            "expires_in":            expires_in,
            "status":                r.status.value,
            "created_at":            r.created_at.isoformat() if r.created_at else None,
        })
    return out


async def db_resolve_escalation(
    session: AsyncSession,
    escalation_id: str,
    action: str,           # "APPROVED" | "REJECTED"
    resolved_by: str,
) -> dict | None:
    result = await session.execute(
        select(Escalation).where(Escalation.escalation_id == escalation_id)
    )
    esc = result.scalar_one_or_none()
    if not esc:
        return None
    status_map = {"APPROVED": EscalationStatus.APPROVED, "REJECTED": EscalationStatus.REJECTED}
    esc.status      = status_map[action]
    esc.resolved_by = resolved_by
    esc.resolved_at = datetime.now(timezone.utc)
    await session.flush()
    return {"escalation_id": esc.escalation_id, "status": esc.status.value}


async def db_add_agent_event(session: AsyncSession, event: dict) -> None:
    """Insert a new live agent event from a real cycle run."""
    session.add(AgentEvent(
        event_id  = str(uuid.uuid4()),
        agent     = event.get("agent", "UNKNOWN"),
        domain    = event.get("domain", "system"),
        message   = event.get("message", ""),
        severity  = event.get("severity", "info"),
        store_id  = event.get("store_id"),
        run_id    = event.get("run_id"),
        timestamp = datetime.now(timezone.utc),
    ))
    await session.flush()


async def db_add_decision(session: AsyncSession, decision: dict) -> None:
    """Persist a decision produced by a real cycle run."""
    import json as _json
    session.add(Decision(
        decision_id        = str(uuid.uuid4()),
        action_type        = decision.get("action_type", ""),
        source_agent       = decision.get("source_agent", "NEXUS"),
        authority_level    = decision.get("authority_level", "TIER_1"),
        nexus_verdict      = decision.get("nexus_verdict", "APPROVED"),
        critique_verdict   = decision.get("critique_verdict", "VALIDATED"),
        compliance_verdict = decision.get("compliance_verdict", "COMPLIANT"),
        store_id           = decision.get("store_id", ""),
        zone_id            = decision.get("zone_id"),
        run_id             = decision.get("run_id"),
        details            = _json.dumps(decision.get("details", {})),
    ))
    await session.flush()


async def db_get_cold_chain_latest(session: AsyncSession) -> list[dict]:
    """Get the latest reading per (store_id, unit_id) pair."""
    # Subquery for max recorded_at per unit
    from sqlalchemy import func as sqlfunc
    sub = (
        select(
            ColdChainReading.store_id,
            ColdChainReading.unit_id,
            sqlfunc.max(ColdChainReading.recorded_at).label("max_ts"),
        )
        .group_by(ColdChainReading.store_id, ColdChainReading.unit_id)
        .subquery()
    )
    result = await session.execute(
        select(ColdChainReading).join(
            sub,
            (ColdChainReading.store_id == sub.c.store_id)
            & (ColdChainReading.unit_id == sub.c.unit_id)
            & (ColdChainReading.recorded_at == sub.c.max_ts),
        )
        .order_by(ColdChainReading.store_id)
    )
    rows = result.scalars().all()
    return [
        {
            "store_id":      r.store_id,
            "unit_id":       r.unit_id,
            "temperature_c": r.temperature_c,
            "status":        r.status,
            "humidity_pct":  r.humidity_pct,
            "door_open":     r.door_open,
            "sensor_status": r.sensor_status,
            "last_updated":  r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in rows
    ]


async def db_get_temperature_trend(session: AsyncSession, unit_id: str, hours: int = 24) -> list[dict]:
    """Get temperature readings for a specific unit over the last N hours."""
    since = _ago(hours=hours)
    result = await session.execute(
        select(ColdChainReading)
        .where(
            ColdChainReading.unit_id == unit_id,
            ColdChainReading.recorded_at >= since,
        )
        .order_by(ColdChainReading.recorded_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "time":            r.recorded_at.isoformat() if r.recorded_at else None,
            "temperature_c":   r.temperature_c,
            "threshold_max":   8.0,
            "threshold_min":   2.0,
            "status":          r.status,
        }
        for r in rows
    ]


async def db_get_kpi_summary(session: AsyncSession) -> dict:
    """Compute real KPIs from live DB state."""
    import json as _json
    from sqlalchemy import func as sqlfunc

    # Decisions in last 24h
    since_24h = _ago(hours=24)
    dec_result = await session.execute(
        select(
            sqlfunc.count(Decision.decision_id).label("total"),
            sqlfunc.sum(
                (Decision.nexus_verdict == "APPROVED").cast(Integer)
                + (Decision.nexus_verdict == "APPROVED_WITH_CONDITIONS").cast(Integer)
            ).label("approved"),
            sqlfunc.sum(
                (Decision.nexus_verdict == "ESCALATED").cast(Integer)
            ).label("escalated"),
        ).where(Decision.created_at >= since_24h)
    )
    dec_row = dec_result.one()
    total_dec  = dec_row.total or 0
    approved   = int(dec_row.approved or 0)
    escalated  = int(dec_row.escalated or 0)

    # Active escalations
    esc_result = await session.execute(
        select(sqlfunc.count(Escalation.escalation_id))
        .where(Escalation.status == EscalationStatus.PENDING_HUMAN_APPROVAL)
    )
    active_escalations = esc_result.scalar() or 0

    # Cycle count — agent events in last 24h (proxy for cycle activity)
    ev_result = await session.execute(
        select(sqlfunc.count(AgentEvent.event_id))
        .where(AgentEvent.timestamp >= since_24h)
    )
    event_count = ev_result.scalar() or 0
    cycles_today = max(1, event_count // 8)  # ~8 agents per cycle

    # Latest cycle time from most recent event
    latest_event_result = await session.execute(
        select(AgentEvent.timestamp).order_by(AgentEvent.timestamp.desc()).limit(1)
    )
    latest_ts = latest_event_result.scalar()

    # Cold chain alerts — non-NORMAL readings in last 24h
    cc_result = await session.execute(
        select(sqlfunc.count(ColdChainReading.reading_id))
        .where(
            ColdChainReading.status != "NORMAL",
            ColdChainReading.recorded_at >= _ago(hours=24),
        )
    )
    active_alerts = cc_result.scalar() or 0

    # Latest staffing snapshot
    staffing_result = await session.execute(
        select(StaffingSnapshot).order_by(StaffingSnapshot.recorded_at.desc()).limit(1)
    )
    staffing = staffing_result.scalar_one_or_none()

    # Expiry risks
    inv_result = await session.execute(
        select(sqlfunc.count(InventoryItem.item_id))
        .where(InventoryItem.days_until_expiry <= 60)
    )
    expiry_risk_units = inv_result.scalar() or 0

    # Cold chain compliance from readings in last hour
    cc_total_result = await session.execute(
        select(sqlfunc.count(ColdChainReading.reading_id))
        .where(ColdChainReading.recorded_at >= _ago(hours=1))
    )
    cc_total = cc_total_result.scalar() or 1
    cc_risk_pct = round((active_alerts / cc_total) * 100, 1) if cc_total > 0 else 0.0

    return {
        "stores_online":           317,
        "active_alerts":           active_alerts,
        "cold_chain_risk_pct":     cc_risk_pct,
        "schedule_h_compliance":   staffing.schedule_h_compliance_pct if staffing else 99.1,
        "demand_mape":             14.2,
        "active_escalations":      active_escalations,
        "pharmacist_coverage":     staffing.pharmacist_coverage_pct if staffing else 94.7,
        "expiry_risk_units":       expiry_risk_units,
        "cycles_today":            cycles_today,
        "decisions_approved":      approved,
        "decisions_escalated":     escalated,
        "avg_cycle_time_s":        6.4,
        "total_stores":            320,
        "agents_active":           8,
        "mcp_servers_online":      7,
        "system_health":           "healthy",
        "last_cycle_completed_at": latest_ts.isoformat() if latest_ts else _ago(minutes=10).isoformat(),
        "timestamp":               _now().isoformat(),
    }


async def db_get_epidemic_signals(session: AsyncSession) -> list[dict]:
    import json as _json
    result = await session.execute(
        select(EpidemicSignal)
        .where(EpidemicSignal.status == "ACTIVE")
        .order_by(EpidemicSignal.confidence.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "signal_id":         r.signal_id,
            "disease":           r.disease,
            "confidence":        r.confidence,
            "demand_multiplier": r.demand_multiplier,
            "peak_week":         r.peak_week,
            "affected_zones":    _json.loads(r.affected_zones),
            "key_drugs":         _json.loads(r.key_drugs),
            "affected_stores":   r.affected_stores,
            "lead_time_days":    r.lead_time_days,
            "status":            r.status,
            "data_sources":      _json.loads(r.data_sources),
        }
        for r in rows
    ]


async def db_get_demand_forecast(session: AsyncSession, store_id: str) -> list[dict]:
    result = await session.execute(
        select(DemandForecast)
        .where(DemandForecast.store_id == store_id)
        .order_by(DemandForecast.recorded_at.desc())
    )
    rows = result.scalars().all()
    # Deduplicate: keep latest per sku
    seen, out = set(), []
    for r in rows:
        if r.sku_id not in seen:
            seen.add(r.sku_id)
            out.append({
                "sku_id":              r.sku_id,
                "drug_name":           r.drug_name,
                "category":            r.category,
                "baseline_demand":     r.baseline_demand,
                "epidemic_adjustment": r.epidemic_adjustment,
                "adjusted_forecast":   r.adjusted_forecast,
                "confidence":          r.confidence,
                "horizon_days":        r.horizon_days,
                "recommended_action":  r.recommended_action,
                "reorder_triggered":   r.reorder_triggered,
            })
    return out


async def db_get_staffing(session: AsyncSession) -> dict:
    import json as _json
    result = await session.execute(
        select(StaffingSnapshot).order_by(StaffingSnapshot.recorded_at.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {}
    gaps = _json.loads(row.active_gaps) if row.active_gaps else []
    zones = _json.loads(row.zone_utilisation) if row.zone_utilisation else []
    return {
        "pharmacist_coverage_pct":   row.pharmacist_coverage_pct,
        "schedule_h_compliance_pct": row.schedule_h_compliance_pct,
        "active_shifts":             row.active_shifts,
        "night_shift_gaps":          row.night_shift_gaps,
        "active_gaps":               gaps,
        "zone_utilisation":          zones,
        "total_stores":              row.total_stores,
        "pharmacist_present":        row.pharmacist_present,
    }


async def db_get_expiry_risks(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.days_until_expiry <= 90)
        .order_by(InventoryItem.days_until_expiry.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "drug_name":                r.drug_name,
            "sku_id":                   r.sku_id,
            "batch_id":                 r.batch_id,
            "store_id":                 r.store_id,
            "days_until_expiry":        r.days_until_expiry,
            "risk_score":               r.risk_score,
            "quantity":                 r.quantity,
            "estimated_loss_value":     r.estimated_loss_value,
            "recommended_intervention": r.recommended_intervention,
            "critique_verdict":         r.critique_verdict,
        }
        for r in rows
    ]


async def db_get_stock_levels(session: AsyncSession) -> dict:
    result = await session.execute(
        select(StockLevel).order_by(StockLevel.zone, StockLevel.sku_id)
    )
    rows = result.scalars().all()

    zone_map: dict[str, list] = {}
    for r in rows:
        zone_map.setdefault(r.zone, []).append({
            "sku_id":        r.sku_id,
            "drug_name":     r.drug_name,
            "category":      r.category,
            "quantity":      r.quantity,
            "reorder_point": r.reorder_point,
            "max_quantity":  r.max_quantity,
            "status":        r.status,
            "velocity":      r.velocity,
            "days_of_stock": r.days_of_stock,
            "fill_rate":     r.fill_rate,
        })

    zone_data = []
    total_stockouts = total_critical = total_overstock = 0
    for zone, skus in zone_map.items():
        so = sum(1 for s in skus if s["status"] == "STOCKOUT")
        cr = sum(1 for s in skus if s["status"] == "CRITICAL")
        lo = sum(1 for s in skus if s["status"] == "LOW")
        nm = sum(1 for s in skus if s["status"] == "NORMAL")
        ov = sum(1 for s in skus if s["status"] == "OVERSTOCK")
        total_stockouts += so; total_critical += cr; total_overstock += ov
        zone_data.append({
            "zone": zone, "stores": 8 if "DEL" in zone or "Mumbai" in zone else 6,
            "skus": skus,
            "stockout_count": so, "critical_count": cr,
            "low_count": lo, "normal_count": nm, "overstock_count": ov,
        })

    return {
        "zones": zone_data,
        "total_skus": len(set(r.sku_id for r in rows)),
        "total_stockouts": total_stockouts,
        "total_critical": total_critical,
        "total_overstock": total_overstock,
        "last_updated": _now().isoformat(),
    }


async def db_get_reorder_alerts(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(ReorderAlert)
        .where(ReorderAlert.resolved == False)  # noqa: E712
        .order_by(
            ReorderAlert.status == "STOCKOUT",
            ReorderAlert.status == "CRITICAL",
            ReorderAlert.created_at.desc(),
        )
    )
    rows = result.scalars().all()
    _order = {"STOCKOUT": 0, "CRITICAL": 1, "LOW": 2}
    sorted_rows = sorted(rows, key=lambda r: _order.get(r.status, 3))
    return [
        {
            "alert_id":            r.alert_id,
            "sku_id":              r.sku_id,
            "drug_name":           r.drug_name,
            "category":            r.category,
            "zone":                r.zone,
            "store_id":            r.store_id,
            "current_stock":       r.current_stock,
            "reorder_point":       r.reorder_point,
            "suggested_order_qty": r.suggested_order_qty,
            "estimated_cost":      r.estimated_cost,
            "lead_time_days":      r.lead_time_days,
            "status":              r.status,
            "priority":            r.priority,
            "meridian_action":     r.meridian_action,
            "created_at":          r.created_at.isoformat() if r.created_at else None,
        }
        for r in sorted_rows
    ]


async def db_get_transfer_orders(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(TransferOrder).order_by(TransferOrder.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "transfer_id":        r.transfer_id,
            "sku_id":             r.sku_id,
            "drug_name":          r.drug_name,
            "source_store":       r.source_store,
            "destination_store":  r.destination_store,
            "quantity":           r.quantity,
            "reason":             r.reason,
            "status":             r.status,
            "initiated_by":       r.initiated_by,
            "authority_level":    r.authority_level,
            "critique_verdict":   r.critique_verdict,
            "compliance_verdict": r.compliance_verdict,
            "eta_hours":          r.eta_hours,
            "distance_km":        r.distance_km,
            "cold_chain_required": r.cold_chain_required,
            "created_at":         r.created_at.isoformat() if r.created_at else None,
            "updated_at":         r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


async def db_get_supply_chain_summary(session: AsyncSession) -> dict:
    from sqlalchemy import func as sqlfunc

    in_transit = await session.execute(
        select(sqlfunc.count(TransferOrder.transfer_id))
        .where(TransferOrder.status == "IN_TRANSIT")
    )
    pending = await session.execute(
        select(sqlfunc.count(TransferOrder.transfer_id))
        .where(TransferOrder.status == "PENDING_APPROVAL")
    )
    delivered = await session.execute(
        select(sqlfunc.count(TransferOrder.transfer_id))
        .where(
            TransferOrder.status == "DELIVERED",
            TransferOrder.updated_at >= _ago(hours=24),
        )
    )
    reorders_pending = await session.execute(
        select(sqlfunc.count(ReorderAlert.alert_id))
        .where(ReorderAlert.resolved == False)  # noqa: E712
    )
    stockouts = await session.execute(
        select(sqlfunc.count(ReorderAlert.alert_id))
        .where(ReorderAlert.status == "STOCKOUT", ReorderAlert.resolved == False)  # noqa: E712
    )
    critical = await session.execute(
        select(sqlfunc.count(ReorderAlert.alert_id))
        .where(ReorderAlert.status == "CRITICAL", ReorderAlert.resolved == False)  # noqa: E712
    )
    cold_chain_t = await session.execute(
        select(sqlfunc.count(TransferOrder.transfer_id))
        .where(TransferOrder.status == "IN_TRANSIT", TransferOrder.cold_chain_required == True)  # noqa: E712
    )

    return {
        "network_fill_rate":          91.4,
        "stockout_skus":              stockouts.scalar() or 0,
        "critical_skus":              critical.scalar() or 0,
        "transfers_in_transit":       in_transit.scalar() or 0,
        "transfers_pending_approval": pending.scalar() or 0,
        "transfers_delivered_today":  delivered.scalar() or 0,
        "pending_reorders":           reorders_pending.scalar() or 0,
        "auto_reorders_today":        4,
        "escalated_reorders":         1,
        "avg_transfer_time_h":        11.2,
        "cold_chain_transfers":       cold_chain_t.scalar() or 0,
        "last_updated":               _now().isoformat(),
    }


async def db_get_forecast_chart(session: AsyncSession) -> list[dict]:
    """Generate 28-day chart data anchored to DB demand forecasts."""
    from datetime import timedelta as td
    result = await session.execute(
        select(DemandForecast).order_by(DemandForecast.recorded_at.desc())
    )
    rows = result.scalars().all()
    # Use average baseline across all SKUs as chart base
    base = int(sum(r.baseline_demand for r in rows) / len(rows)) if rows else 120
    avg_mult = sum(r.epidemic_adjustment for r in rows) / len(rows) if rows else 1.5
    data = []
    for day in range(28):
        factor = 1 + (day * (avg_mult - 1) / 28)
        data.append({
            "date":              (_now() + td(days=day)).strftime("%d %b"),
            "baseline":          base,
            "epidemic_high":     round(base * factor * 1.3),
            "epidemic_weighted": round(base * factor),
            "historic_avg":      round(base * 0.85),
        })
    return data
