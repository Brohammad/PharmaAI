# PharmaIQ — Autonomous Health Retail Intelligence System

[![CI](https://github.com/Brohammad/PharmaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Brohammad/PharmaAI/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Industry-grade multi-agent AI for MedChain India**  
> 320 pharmacies · 4.2M patients/year · ₹480Cr annual revenue  
> LangGraph + **Gemini 3.1 Pro** · 8 agents · 7 MCP servers · 5 scheduled cycles

PharmaIQ is a **production-grade autonomous decision engine** for pharmaceutical retail networks. It combines a 3-tier agent architecture with adversarial validation, regulatory compliance enforcement, and institutional memory — achieving full automation for routine decisions while escalating high-impact actions for human review.

---

## ✨ What's New in v2.0

| Feature | Detail |
|---------|--------|
| 🔐 **JWT Authentication** | Role-based access (MANAGER / ADMIN / VIEWER), bcrypt password hashing |
| 🗄️ **Async SQLite Database** | SQLAlchemy 2.0 async + aiosqlite — decisions, escalations, audit log, cold-chain readings |
| 📡 **SSE Streaming** | `/api/v1/cycles/stream` — real-time agent output pushed to the UI as events arrive |
| 📊 **Prometheus Metrics** | `/metrics` endpoint — cycle latency, agent call counters, active WebSocket gauge |
| 🐳 **Docker + Compose** | Single `docker-compose up` starts API + optional Prometheus/Grafana stack |
| 🤖 **CI/CD** | GitHub Actions — pytest matrix (3.10 + 3.11), frontend Vite build, Docker smoke test |
| ⚡ **Gemini 3.1 Models** | `gemini-3.1-flash-lite-preview` (fast agents) · `gemini-3.1-pro-preview` (NEXUS + CHRONICLE) |
| 🎨 **React Dashboard v2** | Login page, cycle runner with live SSE feed, demand/cold-chain/staffing/escalations views |

---

## 🏗️ Architecture

### System Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REACT FRONTEND (Vite)                        │
│  Login · Dashboard · Demand · Cold Chain · Staffing · Escalations   │
│                  Tailwind CSS · Recharts · SSE stream               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────────────┐
│                   FASTAPI BACKEND  v2.0                             │
│  JWT auth · REST endpoints · SSE stream · Prometheus metrics        │
│  APScheduler (5 cycles) · SQLAlchemy async DB · Audit log           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ LangGraph StateGraph
┌───────────────────────────▼─────────────────────────────────────────┐
│                     PHARMAIQ AGENT GRAPH                            │
│                                                                     │
│  CHRONICLE ENTRY ──► SENTINEL ──► PULSE ──► AEGIS ──► MERIDIAN     │
│                                     │                               │
│                               CRITIQUE ──► COMPLIANCE               │
│                                     │                               │
│                                   NEXUS                             │
│                             ┌───────┴───────┐                       │
│                         EXECUTE        ESCALATE                     │
│                                     │                               │
│                            CHRONICLE EXIT                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ MCP tool calls
┌───────────────────────────▼─────────────────────────────────────────┐
│                      7 MCP SERVERS                                  │
│  cold_chain · erp · hrms · distributor · external_intel             │
│  regulatory_kb · communication                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Graph (detailed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PHARMAIQ AGENT GRAPH                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐                                                       │
│  │  CHRONICLE ENTRY │  ← Inject institutional memory before cycle starts   │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│  ┌────────▼────────────────────────────────────────────────────────┐       │
│  │                    TIER 1 — OPERATIONAL                         │       │
│  │                  (Domain experts, propose only)                 │       │
│  │                                                                 │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │       │
│  │  │ SENTINEL │→ │  PULSE   │→ │  AEGIS   │→ │  MERIDIAN    │   │       │
│  │  │ Cold     │  │ Demand & │  │ Staffing │  │ Expiry &     │   │       │
│  │  │ Chain    │  │ Epidemic │  │Compliance│  │ Inventory    │   │       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   │                                         │
│  ┌────────────────────────────────▼────────────────────────────────┐       │
│  │                    TIER 2 — VALIDATION                          │       │
│  │                                                                 │       │
│  │  ┌──────────────────────────┐  ┌──────────────────────────────┐ │       │
│  │  │         CRITIQUE         │→ │        COMPLIANCE            │ │       │
│  │  │  5-dimension adversarial │  │  Regulatory verification     │ │       │
│  │  │  VALIDATED/CHALLENGED/   │  │  CDSCO · DPCO · Shops Act   │ │       │
│  │  │  DOWNGRADED/REJECTED     │  │  COMPLIANT/CONDITIONAL/NON   │ │       │
│  │  └──────────────────────────┘  └──────────────────────────────┘ │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   │                                         │
│  ┌────────────────────────────────▼────────────────────────────────┐       │
│  │                    TIER 3 — META                                │       │
│  │                                                                 │       │
│  │  ┌──────────────────────────────────────────────────────────┐   │       │
│  │  │                        NEXUS                             │   │       │
│  │  │  Cross-domain synthesis · Authority matrix enforcer      │   │       │
│  │  │  Priority: Patient Safety > Regulatory > Commercial >    │   │       │
│  │  │           Efficiency                                     │   │       │
│  │  └──────────────────────────────┬───────────────────────────┘   │       │
│  └────────────────────────────────┼────────────────────────────────┘       │
│                                   │                                         │
│              ┌────────────────────┴────────────────────┐                   │
│              ▼                                         ▼                   │
│    ┌─────────────────┐                    ┌─────────────────────────┐      │
│    │   EXECUTION     │                    │   HUMAN ESCALATION      │      │
│    │  MCP write ops  │                    │  approval request sent  │      │
│    └────────┬────────┘                    └─────────────────────────┘      │
│             │                                                               │
│  ┌──────────▼───────────────┐                                              │
│  │     CHRONICLE EXIT       │  ← Record outcomes, update pattern library   │
│  └──────────────────────────┘                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Reference

### Tier 1 — Operational (Domain Experts)

| Agent | Model | Responsibility | Temporal Mode |
|-------|-------|---------------|---------------|
| **SENTINEL** | Flash-Lite | Cold chain guardian — WHO PQS excursion classification, quarantine proposals | Real-time reactive |
| **PULSE** | Flash-Lite | Demand & epidemic intelligence — scenario-weighted forecasts, IDSP surveillance | Predictive (hours to weeks) |
| **AEGIS** | Flash-Lite | Staffing & Schedule H compliance — pharmacist coverage, overtime alerts | Real-time + planning |
| **MERIDIAN** | Flash-Lite | Expiry risk scoring via Lifecycle State Machine — write-off minimisation | Continuous monitoring |

### Tier 2 — Validation (Adversarial)

| Agent | Model | Method | Verdicts |
|-------|-------|--------|---------|
| **CRITIQUE** | Flash-Lite | 5-dimension adversarial: Data Quality → Assumption Stress → Historical Match → Second-Order Effects → Proportionality | VALIDATED / CHALLENGED / DOWNGRADED / REJECTED |
| **COMPLIANCE** | Flash-Lite | Regulatory verification: CDSCO · DPCO · Shops Act · GST | COMPLIANT / CONDITIONALLY_COMPLIANT / NON_COMPLIANT |

### Tier 3 — Meta (Synthesis & Learning)

| Agent | Model | Function |
|-------|-------|---------|
| **NEXUS** | **Pro** | Cross-domain conflict resolution · Authority matrix enforcement · Network-level resource allocation |
| **CHRONICLE** | **Pro** | Decision outcome tracking · Pattern library · Agent calibration · Contextual memory injection |

---

## 🔧 MCP Server Reference

| Server | Integration | Data |
|--------|------------|------|
| `cold_chain` | 960 IoT fridge units | Real-time temperatures, excursion history, batch mapping |
| `erp` | SAP Business One | Inventory positions, sales velocity, expiry reports, purchase orders |
| `hrms` | Zoho People + scheduling | Staff roster, pharmacist pool, compliance status |
| `distributor` | Top 8 API + structured email | Stock availability, pricing, delivery status |
| `external_intel` | IDSP · IMD · CPCB · WHO · Google Trends | Disease surveillance, weather, AQI, recalls |
| `regulatory_kb` | Version-controlled rule store | CDSCO rules, DPCO ceilings, drug schedules |
| `communication` | Multi-channel notification | SMS, push, email, phone for CRITICAL alerts |

---

## 🛡️ Authority Matrix

| Level | Condition | Example Actions |
|-------|-----------|----------------|
| **AUTO** | Within thresholds, fully validated | Severe excursion quarantine, ≤2.5× reorder |
| **HUMAN_INFORMED** | Executes + notifies simultaneously | 2.5–3× reorder, cross-store transfer |
| **HUMAN_REQUIRED** | Queued until human approves | >3× reorder, >₹2L cost, batch destruction |
| **HUMAN_ONLY** | No automated path | Store closure, narcotic disposal, CDSCO formal notification |

---

## ⏰ Scheduled Cycles (IST)

| Time | Cycle | Agents |
|------|-------|--------|
| 05:00 daily | Morning Forecast | All 8 (full pipeline) |
| Every 2h | Compliance Sweep | CHRONICLE → AEGIS → SENTINEL |
| 13:00 daily | Midday Reforecast | CHRONICLE → PULSE → MERIDIAN |
| 22:00 daily | Expiry Review | CHRONICLE → MERIDIAN → PULSE |
| Monday 07:00 | Weekly Brief | All 8 (network-wide review) |

---

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
git clone https://github.com/Brohammad/PharmaAI.git
cd PharmaAI
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

docker-compose up --build
# API:      http://localhost:8000
# Frontend: http://localhost:5173
# Docs:     http://localhost:8000/docs

# With Prometheus + Grafana:
docker-compose --profile observability up
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000
```

### Option B — Local Development

**Prerequisites:** Python 3.10+, Node.js 20+

```bash
git clone https://github.com/Brohammad/PharmaAI.git
cd PharmaAI

# Backend
python -m venv .venv
source .venv/bin/activate
pip install bcrypt==4.0.1          # pin before requirements
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set GOOGLE_API_KEY and JWT_SECRET_KEY

uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Environment Variables

Copy `.env.example` to `.env` and set:

```ini
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Models (defaults shown)
GEMINI_MODEL=gemini-3.1-flash-lite-preview
GEMINI_MODEL_VALIDATION=gemini-3.1-flash-lite-preview
GEMINI_MODEL_SYNTHESIS=gemini-3.1-pro-preview

# Auth (change in production)
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

---

## 🔑 Demo Credentials

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Manager** | `manager@medchain.in` | `pharmaiq-demo` | Full dashboard, approve escalations |
| **Admin** | `admin@medchain.in` | `pharmaiq-admin` | Full dashboard + system config |
| **Viewer** | `viewer@medchain.in` | `pharmaiq-view` | Read-only dashboard |

---

## 📡 API Reference

### Authentication

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/auth/token` | POST | Login — returns JWT (form: `username`, `password`) |
| `/auth/me` | GET | Current user info (requires Bearer token) |

### Core Endpoints

| Endpoint | Method | Auth | Description |
|---------|--------|------|-------------|
| `/health` | GET | None | System health + version |
| `/metrics` | GET | None | Prometheus metrics |
| `/cycles/trigger` | POST | Bearer | Manually trigger a decision cycle |
| `/cycles/status` | GET | Bearer | APScheduler jobs + next run times |
| `/graph/topology` | GET | Bearer | Agent graph topology |
| `/signals/ingest` | POST | Bearer | Ingest external signal (IoT, IDSP, HR) |

### Dashboard API (`/api/v1/`)

| Endpoint | Description |
|---------|-------------|
| `GET /api/v1/dashboard/kpis` | Live KPI metrics |
| `GET /api/v1/dashboard/events` | Recent agent events |
| `GET /api/v1/cycles/stream` | SSE stream of live cycle output |
| `GET /api/v1/demand/forecast` | Demand forecast table |
| `GET /api/v1/demand/epidemic-signals` | Active epidemic signals |
| `GET /api/v1/demand/forecast-chart` | 28-day chart data |
| `GET /api/v1/cold-chain/overview` | Network cold-chain status |
| `GET /api/v1/cold-chain/alerts` | Active temperature alerts |
| `GET /api/v1/inventory/expiry-risks` | Expiry risk SKUs |
| `GET /api/v1/staffing/overview` | Zone-level staffing |
| `GET /api/v1/decisions/recent` | Recent decisions |
| `GET /api/v1/decisions/escalations` | Pending escalations |
| `POST /api/v1/decisions/escalations/{id}/approve` | Approve escalation (MANAGER+) |
| `POST /api/v1/decisions/escalations/{id}/reject` | Reject escalation (MANAGER+) |
| `GET /api/v1/audit-log` | Immutable audit log |

### Example — Trigger a Cycle

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=manager@medchain.in&password=pharmaiq-demo" \
  | jq -r .access_token)

# 2. Trigger cycle
curl -X POST http://localhost:8000/cycles/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"store_id":"STORE_DEL_007","cycle_type":"MORNING_FORECAST"}'
```

### Example — Ingest an IoT Signal

```bash
curl -X POST http://localhost:8000/signals/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_id": "STORE_042",
    "zone_id": "DELHI_NCR",
    "event_type": "cold_chain_temperature_breach",
    "source": "iot_gateway",
    "data": {
      "unit_id": "FRIDGE_A3",
      "current_temp": 18.5,
      "trend": "rising"
    }
  }'
```

---

## 🧪 Testing

```bash
# All tests with coverage
pytest tests/ -v --cov=. --cov-report=term-missing

# Specific suites
pytest tests/test_auth.py -v        # 16 tests — JWT, roles, bcrypt
pytest tests/test_db.py -v          # 17 tests — DB CRUD, escalations, audit log

# HTML coverage report
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

**Test matrix:** CI runs on Python 3.10 and 3.11.

---

## 📁 Project Structure

```
PharmaAI/
├── main.py                     # FastAPI v2.0 — all routes, scheduler, lifespan
├── pyproject.toml              # Build config + pytest/coverage settings
├── requirements.txt
├── Dockerfile                  # Multi-stage: node:20 (build) + python:3.10-slim
├── docker-compose.yml          # API + optional Prometheus/Grafana profile
├── prometheus.yml              # Scrape config for /metrics
├── .env.example
├── .github/
│   └── workflows/ci.yml        # Backend tests (3.10+3.11) + frontend build + Docker
│
├── api/
│   ├── auth.py                 # JWT auth, bcrypt, role middleware, demo users
│   ├── database.py             # SQLAlchemy async — Decision/Escalation/AuditLog/ColdChain
│   ├── metrics.py              # Prometheus counters, histograms, gauges
│   └── mock_data.py            # Realistic demo data for all dashboard endpoints
│
├── config/
│   ├── settings.py             # Pydantic Settings — all env vars + model names
│   ├── authority_matrix.py     # AUTO/HUMAN_INFORMED/REQUIRED/ONLY thresholds
│   └── drug_stability.py       # WHO PQS stability profiles + excursion classifier
│
├── agents/
│   ├── sentinel.py             # SENTINEL — cold chain guardian (Flash-Lite)
│   ├── pulse.py                # PULSE — demand & epidemic intelligence (Flash-Lite)
│   ├── aegis.py                # AEGIS — staffing & compliance (Flash-Lite)
│   ├── meridian.py             # MERIDIAN — expiry lifecycle (Flash-Lite)
│   ├── critique.py             # CRITIQUE — adversarial validation (Flash-Lite)
│   ├── compliance.py           # COMPLIANCE — regulatory check (Flash-Lite)
│   ├── nexus.py                # NEXUS — synthesis & conflict resolution (Pro)
│   └── chronicle.py            # CHRONICLE — memory & learning (Pro)
│
├── graph/
│   ├── state.py                # PharmaIQState Pydantic model (full cycle context)
│   ├── ingestion.py            # Signal classifier, router, significance gate
│   ├── workflow.py             # LangGraph StateGraph compilation (10 nodes)
│   ├── execution.py            # MCP write-op execution engine
│   └── audit.py                # Audit trail integration
│
├── tools/mcp/
│   ├── cold_chain.py           # ColdChainMCPServer (960 IoT units)
│   ├── erp.py                  # ERPMCPServer (SAP Business One)
│   ├── hrms.py                 # HRMSMCPServer (Zoho People)
│   ├── distributor.py          # DistributorMCPServer (8 suppliers)
│   ├── external_intel.py       # ExternalIntelMCPServer (IDSP/IMD/WHO)
│   ├── regulatory_kb.py        # RegulatoryKBMCPServer (CDSCO/DPCO)
│   └── communication.py        # CommunicationMCPServer (SMS/push/email)
│
├── frontend/
│   ├── src/
│   │   ├── pages/              # Dashboard, Demand, ColdChain, Staffing, Escalations
│   │   ├── components/         # Sidebar, KPI cards, charts, CycleRunner
│   │   ├── api/                # axios instances (api.jsx, auth.jsx)
│   │   └── context/            # AuthContext with JWT token management
│   ├── vite.config.js          # Proxy: /api /auth /metrics /ws → localhost:8000
│   └── tailwind.config.js      # Brand colour palette + dark mode
│
├── utils/
│   └── logger.py               # structlog + immutable JSONL audit trail
│
└── tests/
    ├── test_auth.py            # 16 tests — login, JWT encode/decode, role checks
    └── test_db.py              # 17 tests — all async DB operations
```

---

## 🏛️ Design Principles

1. **Tier 1 agents only propose** — they never call MCP write operations directly
2. **CRITIQUE before COMPLIANCE** — quality gate before regulatory gate
3. **NEXUS sees all** — only agent with full network-wide view and conflict authority
4. **Fail closed** — COMPLIANCE returns NON_COMPLIANT when regulatory KB is unavailable
5. **Patient safety is absolute** — SEVERE/FREEZE excursions bypass CRITIQUE delays
6. **Every decision is audited** — async SQLite + immutable JSONL trail
7. **Scenario forecasts, not point estimates** — PULSE always provides confidence intervals
8. **Human escalation is not optional** — HUMAN_REQUIRED actions cannot be auto-approved

---

## 📈 KPI Targets

| Metric | Target | Measured By |
|--------|--------|-------------|
| Cold chain compliance | ≥99.8% | Hours in range / total hours |
| Expiry write-off rate | <0.8% | Write-off value / total inventory value |
| Stockout rate | <0.2% | SKU-hours out of stock / total SKU-hours |
| Schedule H compliance | 100% | Pharmacist-present hours / operating hours |
| Demand forecast MAPE | <12% | Measured weekly by CHRONICLE |

---

## 🔒 Security Notes

- JWT tokens expire after 8 hours (configurable via `JWT_EXPIRE_MINUTES`)
- Passwords hashed with bcrypt (cost factor 12)
- `GOOGLE_API_KEY` and `JWT_SECRET_KEY` must never be committed — use `.env` (gitignored)
- Role-based endpoint protection: escalation approve/reject requires `MANAGER` or `ADMIN`
- All state-changing operations are audit-logged with actor, timestamp, and outcome

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Run tests: `pytest tests/ -v`
4. Ensure frontend builds: `cd frontend && npm run build`
5. Open a PR — CI will run automatically

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

*PharmaIQ — Built to make pharmaceutical supply chains safer, smarter, and fully auditable.*
