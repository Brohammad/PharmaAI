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
