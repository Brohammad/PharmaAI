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

## � Decision Cycle Workflow

### Overview

Every decision cycle flows through **three validation gates** before execution:

```
SIGNAL → INGESTION → TIER 1 (propose) → TIER 2 (validate) → TIER 3 (decide) → EXECUTE/ESCALATE
```

### Complete Workflow (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: SIGNAL INGESTION & ROUTING                                    │
└─────────────────────────────────────────────────────────────────────────┘

1. External Signal Arrives
   ├─ Source: IoT sensor / Scheduled cron / Manual trigger / External API
   ├─ Classified: cold_chain | demand_forecast | staffing_alert | etc.
   └─ Significance Check: Must exceed threshold to trigger cycle

2. CHRONICLE ENTRY (Context Injection)
   ├─ Retrieves: Recent similar events, historical outcomes, agent calibration
   ├─ Injects: Pattern library, seasonal adjustments, known failure modes
   └─ Output: Enriched state with institutional memory

┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: TIER 1 — DOMAIN EXPERTS (Parallel Execution)                  │
└─────────────────────────────────────────────────────────────────────────┘

3. Domain Agents Run in Parallel
   
   SENTINEL (Cold Chain)
   ├─ Queries: cold_chain.get_temperature_readings(store_id, unit_id, hours=24)
   ├─ Analyzes: WHO PQS excursion classification (2°C-8°C standard)
   ├─ Proposes: Quarantine batch if SEVERE (>15°C) or cumulative >2h
   └─ Output: {'action': 'QUARANTINE_BATCH', 'severity': 'CRITICAL', ...}

   PULSE (Demand Intelligence)
   ├─ Queries: external_intel.get_disease_surveillance(zone_id)
   ├─ Analyzes: IDSP signals + seasonal trends + Google search volume
   ├─ Proposes: Emergency reorder if forecast >2.5× baseline
   └─ Output: {'action': 'EMERGENCY_REORDER', 'multiplier': 3.4, ...}

   AEGIS (Staffing)
   ├─ Queries: hrms.get_roster(store_id, date), hrms.get_compliance_status()
   ├─ Analyzes: Schedule H gaps (pharmacist must be present during operations)
   ├─ Proposes: Cross-zone redeployment if gap >30min
   └─ Output: {'action': 'REDEPLOY_STAFF', 'gap_severity': 'HIGH', ...}

   MERIDIAN (Inventory)
   ├─ Queries: erp.get_expiry_risks(store_id), erp.get_stock_velocity()
   ├─ Analyzes: Lifecycle state (days_until_expiry × velocity_score)
   ├─ Proposes: Inter-store transfer if velocity <1.0 and expiry <60 days
   └─ Output: {'action': 'TRANSFER_STOCK', 'risk_score': 0.82, ...}

4. Tier 1 Outputs Consolidated
   └─ All proposals collected into state.tier1_proposals[]

┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: TIER 2 — ADVERSARIAL VALIDATION                               │
└─────────────────────────────────────────────────────────────────────────┘

5. CRITIQUE (Quality Gate)
   ├─ For each Tier 1 proposal:
   │  ├─ Data Quality: Source reliability, sample size, recency
   │  ├─ Assumption Stress: What if trend reverses? What if sensor fails?
   │  ├─ Historical Match: Has this pattern occurred before? Outcome?
   │  ├─ Second-Order Effects: Will this create new problems?
   │  └─ Proportionality: Is the response scaled correctly?
   ├─ Verdict: VALIDATED | CHALLENGED | DOWNGRADED | REJECTED
   └─ Output: state.critique_results = {proposal_id: verdict, reasoning}

6. COMPLIANCE (Regulatory Gate)
   ├─ For each VALIDATED/CHALLENGED proposal:
   │  ├─ Queries: regulatory_kb.check_cold_chain_rules(action)
   │  ├─ Verifies: CDSCO Schedule C (cold chain)
   │  │            DPCO pricing ceiling (if price change)
   │  │            Shops & Establishments Act (staffing hours)
   │  │            GST implications (inter-state transfers)
   │  └─ Checks: License validity, batch certification, pharmacist credentials
   ├─ Verdict: COMPLIANT | CONDITIONALLY_COMPLIANT | NON_COMPLIANT
   └─ Output: state.compliance_results = {proposal_id: verdict, conditions}

┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: TIER 3 — META SYNTHESIS & DECISION                            │
└─────────────────────────────────────────────────────────────────────────┘

7. NEXUS (Conflict Resolution & Authority Check)
   ├─ Receives: All Tier 1 proposals + Tier 2 validation results
   ├─ Resolves Conflicts:
   │  ├─ Priority: Patient Safety > Regulatory > Commercial > Efficiency
   │  ├─ Example: SENTINEL requests fridge shutdown (affects stock)
   │  │           MERIDIAN requests transfer from same fridge
   │  │           → SENTINEL wins, MERIDIAN deferred 4 hours
   │  └─ Cross-domain resource allocation (staff, budget, cold chain capacity)
   ├─ Authority Matrix Check:
   │  ├─ AUTO: Severe excursion + compliant + no conflicts → Execute now
   │  ├─ HUMAN_INFORMED: 2.5-3× reorder → Execute + notify manager
   │  ├─ HUMAN_REQUIRED: >3× reorder OR >₹200k → Queue for approval
   │  └─ HUMAN_ONLY: Store closure, narcotic disposal → Cannot auto-execute
   ├─ Financial Impact Assessment:
   │  └─ Aggregates all costs, checks budget constraints
   └─ Decision: EXECUTE | ESCALATE | DEFER | REJECT

8. Decision Tree (NEXUS output)

   ┌─ COMPLIANT + VALIDATED + AUTO authority?
   │  └─ YES → Route to EXECUTION
   │  └─ NO  → Route to ESCALATION
   │
   ┌─ NON_COMPLIANT?
   │  └─ REJECT (logged in audit trail)
   │
   ┌─ CHALLENGED by CRITIQUE?
   │  └─ If Patient Safety: Override → EXECUTE
   │  └─ Else: ESCALATE with CRITIQUE reasoning
   │
   └─ CONDITIONALLY_COMPLIANT?
      └─ If conditions can be auto-satisfied → EXECUTE with conditions
      └─ Else → ESCALATE

┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: EXECUTION / ESCALATION                                        │
└─────────────────────────────────────────────────────────────────────────┘

9. EXECUTION Path (Authority AUTO or HUMAN_INFORMED)
   
   a) MCP Write Operations Execute
      ├─ cold_chain.quarantine_batch(batch_id, reason)
      ├─ erp.create_purchase_order(supplier_id, items, delivery_date)
      ├─ hrms.reassign_staff(staff_id, new_store_id, shift)
      └─ communication.send_alert(recipient, message, priority)

   b) Database Records Created
      ├─ Decision row: action_type, verdicts, store_id, timestamp
      ├─ AuditLog row: event_type="decision_executed", actor="scheduler"
      └─ AgentEvent row: agent="NEXUS", message="Executed: ...", severity

   c) Notifications Sent (if HUMAN_INFORMED)
      └─ Manager receives: "AUTO-EXECUTED: Emergency reorder ₹2.1L"

10. ESCALATION Path (Authority HUMAN_REQUIRED)
   
    a) Escalation Record Created
       ├─ action_type: "Emergency Reorder — Paracetamol 650mg"
       ├─ reason_for_escalation: "3.4× baseline exceeds TIER_2 authority"
       ├─ nexus_recommendation: "Approve with 2-tranche schedule"
       ├─ financial_impact: ₹320,000
       ├─ expires_at: now + 90 minutes
       └─ status: PENDING_HUMAN_APPROVAL

    b) Manager Notification
       ├─ Push notification: "ACTION REQUIRED: ₹3.2L approval expires in 90m"
       ├─ Email with full context + NEXUS recommendation
       └─ Dashboard escalations page updates in real-time

    c) Manager Decision
       ├─ Approves → Execute MCP ops + record in audit log
       ├─ Rejects → Record rejection reason + notify scheduler
       └─ Expires → Auto-reject + CHRONICLE records pattern

┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 6: LEARNING & MEMORY UPDATE                                      │
└─────────────────────────────────────────────────────────────────────────┘

11. CHRONICLE EXIT (Outcome Recording)
    ├─ Records: Decision outcome, execution latency, validation verdicts
    ├─ Updates Pattern Library:
    │  ├─ "Dengue surge forecasts in Q1 are 23% over-estimated historically"
    │  ├─ "Sensor false-positive rate 23% for fridges >4 years old"
    │  └─ "Cross-zone staff redeployment has 94% acceptance rate"
    ├─ Agent Calibration:
    │  ├─ PULSE forecast accuracy: MAPE reduced from 17% to 12%
    │  └─ SENTINEL excursion classification: 99.2% precision
    └─ Memory Embedding: Store for future CHRONICLE ENTRY injections
```

### Concrete Example — Dengue Surge Response

**Scenario:** IDSP reports dengue cluster in East Delhi (40 confirmed cases, rising trend)

```
09:47 AM  Signal arrives via external_intel MCP
09:47 AM  Ingestion: Classified as "epidemic_signal", significance = HIGH
09:47 AM  CHRONICLE ENTRY: Injects → "Q1 dengue forecasts over-estimate by 23%"

09:48 AM  PULSE analyzes
          ├─ IDSP: 40 cases, weekly growth 180%
          ├─ Google Trends: "dengue symptoms" +210% in East Delhi
          ├─ IMD: Heavy rainfall last week (dengue breeding conditions)
          └─ Proposes: 3.4× baseline reorder for Paracetamol + ORS + NS1 kits
          
09:48 AM  SENTINEL checks cold chain capacity for vaccine surge
          └─ 18% capacity available across 6 East Delhi stores

09:49 AM  CRITIQUE evaluates PULSE proposal
          ├─ Data Quality: ✓ IDSP confirmed, not just Google Trends
          ├─ Assumption Stress: ⚠ What if outbreak plateau in 3 days?
          ├─ Historical Match: Similar Q1 2025 dengue surge, actual demand was 2.1×
          ├─ Second-Order Effects: ✓ No conflicts
          └─ Verdict: CHALLENGED → Recommend 2.1× instead of 3.4×

09:49 AM  COMPLIANCE checks
          ├─ DPCO ceiling: ✓ Paracetamol within price control
          ├─ GST: ✓ Intra-state transfer (Delhi → Delhi)
          └─ Verdict: COMPLIANT

09:50 AM  NEXUS synthesis
          ├─ Accepts CRITIQUE adjustment: 2.1× reorder (not 3.4×)
          ├─ Financial impact: ₹1.8L (down from ₹3.2L)
          ├─ Authority check: 2.1× = AUTO threshold (≤2.5×)
          └─ Decision: EXECUTE immediately + NOTIFY manager

09:51 AM  EXECUTION
          ├─ erp.create_purchase_order(supplier="MedPlus", total=₹180000)
          ├─ communication.send_alert(managers, "Dengue surge order executed")
          └─ Database: Decision + AuditLog rows written

09:52 AM  CHRONICLE EXIT
          ├─ Records: CRITIQUE intervention prevented ₹1.4L over-order
          ├─ Updates: "PULSE dengue forecasts → apply 0.62 correction factor in Q1"
          └─ Agent calibration: CRITIQUE challenge rate 11% → pattern is healthy

OUTCOME:  Stores restocked within 18 hours, no stockouts during surge peak.
          Actual demand matched CRITIQUE's 2.1× prediction (MAPE 4.2%).
```

### Timing Benchmarks

| Phase | Typical Duration | Notes |
|-------|------------------|-------|
| Signal ingestion + routing | 50-200ms | Depends on MCP network latency |
| CHRONICLE ENTRY | 800ms-1.2s | Embedding search + context assembly |
| Tier 1 agents (parallel) | 2-5s | 4 agents run simultaneously |
| CRITIQUE | 1.5-3s | 5-dimension analysis per proposal |
| COMPLIANCE | 600ms-1.5s | Regulatory KB lookups |
| NEXUS synthesis | 2-4s | Complex reasoning with Gemini Pro |
| Execution (MCP writes) | 500ms-2s | Depends on external API latency |
| **Total cycle time** | **8-18s** | 95th percentile: <15s |

### Key Workflow Principles

1. **Parallel where possible** — Tier 1 agents run concurrently, results aggregated before Tier 2
2. **Fail-fast on compliance** — NON_COMPLIANT immediately reject, no NEXUS needed
3. **Patient safety bypass** — SEVERE cold chain excursions skip CRITIQUE delays
4. **Audit everything** — Every agent call, decision, and outcome logged immutably
5. **Human-in-loop is explicit** — Authority matrix prevents silent escalation failures
6. **Learning is continuous** — CHRONICLE closes every cycle, success or failure

---

## �🚀 Quick Start

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
