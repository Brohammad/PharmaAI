"""
tests/test_db.py — Async SQLAlchemy database layer unit tests
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-db-testing!!!")


from api.database import (
    Base,
    Decision,
    Escalation,
    AgentEvent,
    ColdChainReading,
    AuditLog,
    EscalationStatus,
    seed_database,
    db_get_live_events,
    db_get_recent_decisions,
    db_get_escalations,
    db_resolve_escalation,
    db_get_cold_chain_latest,
    db_get_temperature_trend,
    db_add_agent_event,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def db_session():
    """Provide a fully seeded in-memory SQLite session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        await seed_database(session)

    async with Session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Seed verification ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_creates_agent_events(db_session):
    events = await db_get_live_events(db_session, limit=100)
    assert len(events) > 0, "Seed should create AgentEvent rows"


@pytest.mark.asyncio
async def test_seed_creates_decisions(db_session):
    decisions = await db_get_recent_decisions(db_session, limit=100)
    assert len(decisions) > 0, "Seed should create Decision rows"


@pytest.mark.asyncio
async def test_seed_creates_cold_chain_readings(db_session):
    readings = await db_get_cold_chain_latest(db_session)
    assert len(readings) > 0, "Seed should create ColdChainReading rows"


@pytest.mark.asyncio
async def test_seed_creates_escalations(db_session):
    from sqlalchemy import select
    result = await db_session.execute(select(Escalation))
    escalations = result.scalars().all()
    assert len(escalations) > 0, "Seed should create Escalation rows"


# ── db_get_live_events ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_live_events_respects_limit(db_session):
    events = await db_get_live_events(db_session, limit=5)
    assert len(events) <= 5


@pytest.mark.asyncio
async def test_get_live_events_structure(db_session):
    events = await db_get_live_events(db_session, limit=1)
    assert len(events) == 1
    e = events[0]
    assert "agent" in e
    assert "message" in e
    assert "severity" in e


# ── db_get_recent_decisions ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_recent_decisions_limit(db_session):
    decisions = await db_get_recent_decisions(db_session, limit=3)
    assert len(decisions) <= 3


@pytest.mark.asyncio
async def test_get_recent_decisions_fields(db_session):
    decisions = await db_get_recent_decisions(db_session, limit=1)
    d = decisions[0]
    assert "store_id" in d
    assert "nexus_verdict" in d
    assert "authority_level" in d


# ── db_get_escalations ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_escalations_returns_only_pending(db_session):
    pending = await db_get_escalations(db_session)
    for esc in pending:
        assert esc["status"] == EscalationStatus.PENDING_HUMAN_APPROVAL.value


@pytest.mark.asyncio
async def test_escalations_have_expires_in(db_session):
    pending = await db_get_escalations(db_session)
    for esc in pending:
        assert "expires_in" in esc


# ── db_resolve_escalation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_escalation_approve(db_session):
    pending = await db_get_escalations(db_session)
    if not pending:
        pytest.skip("No pending escalations to test resolution")

    esc_id = pending[0]["escalation_id"]
    result = await db_resolve_escalation(db_session, esc_id, "APPROVED", "test-user")
    assert result is not None
    assert result["status"] == EscalationStatus.APPROVED.value


@pytest.mark.asyncio
async def test_resolve_escalation_reject(db_session):
    pending = await db_get_escalations(db_session)
    if not pending:
        pytest.skip("No remaining pending escalations")

    esc_id = pending[0]["escalation_id"]
    result = await db_resolve_escalation(db_session, esc_id, "REJECTED", "test-user-2")
    assert result["status"] == EscalationStatus.REJECTED.value


@pytest.mark.asyncio
async def test_resolve_nonexistent_escalation(db_session):
    result = await db_resolve_escalation(db_session, "00000000-0000-0000-0000-000000000000", "approve", "nobody")
    assert result is None


# ── db_get_cold_chain_latest ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cold_chain_latest_structure(db_session):
    readings = await db_get_cold_chain_latest(db_session)
    assert len(readings) > 0
    r = readings[0]
    assert "unit_id" in r
    assert "temperature_c" in r
    assert "store_id" in r


# ── db_get_temperature_trend ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_temperature_trend_returns_readings(db_session):
    # Use a unit_id that was seeded
    readings = await db_get_temperature_trend(db_session, "COLD-DEL-007-A", hours=48)
    assert isinstance(readings, list)


@pytest.mark.asyncio
async def test_temperature_trend_unknown_unit(db_session):
    readings = await db_get_temperature_trend(db_session, "NONEXISTENT-UNIT", hours=24)
    assert readings == []


# ── db_add_agent_event ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_agent_event(db_session):
    before = await db_get_live_events(db_session, limit=1000)
    count_before = len(before)

    await db_add_agent_event(db_session, {
        "agent": "TEST_AGENT",
        "domain": "testing",
        "message": "Integration test event",
        "severity": "INFO",
        "store_id": "STORE_TEST",
        "run_id": "test-run-999",
    })

    after = await db_get_live_events(db_session, limit=1000)
    assert len(after) == count_before + 1
    assert after[0]["agent"] == "TEST_AGENT"
    assert after[0]["message"] == "Integration test event"
