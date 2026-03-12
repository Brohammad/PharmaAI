"""
tests/test_api.py — FastAPI endpoint integration tests
Uses httpx.AsyncClient against the real app (in-memory SQLite).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# ── App under test ────────────────────────────────────────────────────────
# Override the DB URL to use an in-memory SQLite instance so tests are
# hermetically isolated from any on-disk pharmaiq.db.
import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only!!")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    """Async HTTP client wired to the FastAPI app with a fresh in-memory DB."""
    from main import app
    from api.database import Base, engine
    from sqlalchemy.ext.asyncio import create_async_engine
    import api.database as db_module

    # Swap the engine to in-memory SQLite for the test session
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    db_module.engine = test_engine
    db_module.async_session_factory = None  # force recreation below

    from sqlalchemy.ext.asyncio import async_sessionmaker
    db_module.async_session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False
    )

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test data
    async with db_module.async_session_factory() as session:
        await db_module.seed_database(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── /health ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "2.0.0"
    assert "db_status" in body


# ── /auth/token ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_manager(client):
    r = await client.post(
        "/auth/token",
        data={"username": "manager@medchain.in", "password": "pharmaiq-demo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "MANAGER"


@pytest.mark.asyncio
async def test_login_admin(client):
    r = await client.post(
        "/auth/token",
        data={"username": "admin@medchain.in", "password": "pharmaiq-admin"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_login_viewer(client):
    r = await client.post(
        "/auth/token",
        data={"username": "viewer@medchain.in", "password": "pharmaiq-view"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "VIEWER"


@pytest.mark.asyncio
async def test_login_bad_password(client):
    r = await client.post(
        "/auth/token",
        data={"username": "manager@medchain.in", "password": "wrong-password"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    r = await client.post(
        "/auth/token",
        data={"username": "nobody@nowhere.com", "password": "anything"},
    )
    assert r.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_authenticated(client):
    # Login first
    login = await client.post(
        "/auth/token",
        data={"username": "viewer@medchain.in", "password": "pharmaiq-view"},
    )
    token = login.json()["access_token"]

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "viewer@medchain.in"


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


# ── /api/v1/dashboard/events ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_events_returns_list(client):
    r = await client.get("/api/v1/dashboard/events")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert isinstance(body["events"], list)
    assert len(body["events"]) > 0


@pytest.mark.asyncio
async def test_events_structure(client):
    r = await client.get("/api/v1/dashboard/events")
    event = r.json()["events"][0]
    assert "agent" in event
    assert "message" in event
    assert "severity" in event


# ── /api/v1/decisions/recent ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_decisions_recent(client):
    r = await client.get("/api/v1/decisions/recent")
    assert r.status_code == 200
    body = r.json()
    assert "decisions" in body
    assert isinstance(body["decisions"], list)
    assert len(body["decisions"]) > 0


@pytest.mark.asyncio
async def test_decisions_limit_param(client):
    r = await client.get("/api/v1/decisions/recent?limit=5")
    assert r.status_code == 200
    decisions = r.json()["decisions"]
    assert len(decisions) <= 5


# ── /api/v1/decisions/escalations ────────────────────────────────────────

@pytest.mark.asyncio
async def test_escalations_list(client):
    r = await client.get("/api/v1/decisions/escalations")
    assert r.status_code == 200
    body = r.json()
    assert "escalations" in body
    assert isinstance(body["escalations"], list)


@pytest.mark.asyncio
async def test_escalation_approve_requires_manager(client):
    """VIEWER role should get 403 when trying to approve."""
    login = await client.post(
        "/auth/token",
        data={"username": "viewer@medchain.in", "password": "pharmaiq-view"},
    )
    token = login.json()["access_token"]

    r = await client.post(
        "/api/v1/decisions/escalations/1/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_escalation_approve_manager(client):
    """MANAGER role should be able to approve (returns 200 or 404 if ID not found)."""
    login = await client.post(
        "/auth/token",
        data={"username": "manager@medchain.in", "password": "pharmaiq-demo"},
    )
    token = login.json()["access_token"]

    # Get a pending escalation first
    esc_r = await client.get("/api/v1/decisions/escalations")
    escalations = esc_r.json()["escalations"]
    if not escalations:
        pytest.skip("No pending escalations in test DB")

    esc_id = escalations[0]["id"]
    r = await client.post(
        f"/api/v1/decisions/escalations/{esc_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


# ── /api/v1/cold-chain/overview ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cold_chain_overview(client):
    r = await client.get("/api/v1/cold-chain/overview")
    assert r.status_code == 200
    body = r.json()
    assert "units" in body
    assert isinstance(body["units"], list)
    assert len(body["units"]) > 0


@pytest.mark.asyncio
async def test_cold_chain_trend(client):
    r = await client.get("/api/v1/cold-chain/trend/COLD-001")
    assert r.status_code == 200
    body = r.json()
    assert "readings" in body


# ── /api/v1/kpis ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kpis_structure(client):
    r = await client.get("/api/v1/kpis")
    assert r.status_code == 200
    body = r.json()
    for key in [
        "stores_online", "active_alerts", "cold_chain_risk_pct",
        "schedule_h_compliance", "cycles_today",
    ]:
        assert key in body, f"Missing KPI key: {key}"


# ── /metrics ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prometheus_metrics(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "pharmaiq_http_requests_total" in text or "python_info" in text


# ── /api/v1/audit-log ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_requires_manager(client):
    r = await client.get("/api/v1/audit-log")
    assert r.status_code == 401  # no token


@pytest.mark.asyncio
async def test_audit_log_manager_can_read(client):
    login = await client.post(
        "/auth/token",
        data={"username": "manager@medchain.in", "password": "pharmaiq-demo"},
    )
    token = login.json()["access_token"]
    r = await client.get(
        "/api/v1/audit-log", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert "logs" in r.json()
