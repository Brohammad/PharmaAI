# PharmaIQ — Autonomous Health Retail Intelligence System

> **Industry-grade multi-agent AI for MedChain India**  
> 320 pharmacies · 4.2M patients/year · ₹480Cr annual revenue  
> LangGraph + Gemini 1.5 Pro · 8 agents · 7 MCP servers · 5 scheduled cycles

---

## Architecture Overview

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
│  │  │ Chain    │  │ Epidemic │  │ Compliance│  │ Inventory    │   │       │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   │ route_to_critique?                      │
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

## Agent Reference

### Tier 1 — Operational (Domain Experts)

| Agent | Responsibility | Temporal Mode | Key Tools |
|-------|---------------|---------------|-----------|
| **SENTINEL** | Cold chain guardian — WHO PQS-aligned excursion classification | Real-time reactive | ColdChainMCP, ERPMCP |
| **PULSE** | Demand & epidemic intelligence — scenario-weighted forecasts | Predictive (hours to weeks) | ExternalIntelMCP, ERPMCP |
| **AEGIS** | Staffing & Schedule H compliance | Real-time reactive + planning | HRMSMCP |
| **MERIDIAN** | Expiry risk scoring via Lifecycle State Machine | Continuous monitoring | ERPMCP, DistributorMCP |

### Tier 2 — Validation (Adversarial)

| Agent | Method | Verdicts |
|-------|--------|---------|
| **CRITIQUE** | 5-dimension adversarial: Data Quality → Assumption Stress → Historical Match → Second-Order Effects → Proportionality | VALIDATED / CHALLENGED / DOWNGRADED / REJECTED |
| **COMPLIANCE** | Regulatory verification: CDSCO · DPCO · Shops Act · GST | COMPLIANT / CONDITIONALLY_COMPLIANT / NON_COMPLIANT |

### Tier 3 — Meta (Synthesis & Learning)

| Agent | Function |
|-------|---------|
| **NEXUS** | Cross-domain conflict resolution · Authority matrix enforcement · Network-level resource allocation |
| **CHRONICLE** | Decision outcome tracking · Pattern library · Agent calibration · Contextual memory injection |

---

## MCP Server Reference

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

## Authority Matrix

| Authority Level | Condition | Example |
|----------------|-----------|---------|
| **AUTO** | Within thresholds, fully validated | Severe excursion quarantine, ≤2.5× reorder |
| **HUMAN_INFORMED** | Executes + notifies human simultaneously | 2.5–3× reorder, cross-store transfer |
| **HUMAN_REQUIRED** | Queued until human approves | >3× reorder, >₹2L cost, batch destruction |
| **HUMAN_ONLY** | No automated path | Store closure, narcotic disposal, CDSCO formal notification |

---

## Scheduled Cycles (IST)

| Time | Cycle | Agents Activated |
|------|-------|-----------------|
| 05:00 daily | Morning Forecast | All (CHRONICLE → SENTINEL → PULSE → AEGIS → MERIDIAN) |
| Every 2h | Compliance Sweep | CHRONICLE → AEGIS → SENTINEL |
| 13:00 daily | Midday Reforecast | CHRONICLE → PULSE → MERIDIAN |
| 22:00 daily | Expiry Review | CHRONICLE → MERIDIAN → PULSE |
| Monday 07:00 | Weekly Brief | All (full network-wide review) |

---

## Setup

### Prerequisites
- Python 3.11+
- Google Gemini API key (`gemini-1.5-pro` access)

### Installation

```bash
# Clone and enter project
cd /path/to/PharmaAI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Running

```bash
# Development server (auto-reload)
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Or via gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Testing

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_authority_matrix.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

---

## API Reference

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/health` | GET | System health check |
| `/signals/ingest` | POST | Ingest external signal (IoT, IDSP, HR event) |
| `/cycles/trigger` | POST | Manually trigger a decision cycle |
| `/cycles/status` | GET | APScheduler job status and next run times |
| `/graph/topology` | GET | Agent graph topology reference |
| `/docs` | GET | FastAPI interactive docs (Swagger UI) |

### Signal Ingestion Example

```bash
curl -X POST http://localhost:8000/signals/ingest \
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

## Project Structure

```
PharmaAI/
├── main.py                    # FastAPI app + APScheduler
├── pyproject.toml
├── requirements.txt
├── .env.example
│
├── config/
│   ├── settings.py            # Pydantic Settings (all env vars)
│   ├── authority_matrix.py    # AUTO/HUMAN_INFORMED/REQUIRED/ONLY rules
│   └── drug_stability.py      # WHO PQS stability profiles + excursion classifier
│
├── agents/
│   ├── sentinel.py            # SENTINEL — cold chain guardian
│   ├── pulse.py               # PULSE — demand & epidemic intelligence
│   ├── aegis.py               # AEGIS — staffing & compliance
│   ├── meridian.py            # MERIDIAN — expiry & inventory lifecycle
│   ├── critique.py            # CRITIQUE — 5-dimension adversarial validation
│   ├── compliance.py          # COMPLIANCE — regulatory verification
│   ├── nexus.py               # NEXUS — cross-domain synthesis
│   └── chronicle.py           # CHRONICLE — institutional memory
│
├── graph/
│   ├── state.py               # PharmaIQState Pydantic model
│   ├── ingestion.py           # Signal classification, routing, significance gate
│   ├── workflow.py            # LangGraph StateGraph compilation
│   ├── execution.py           # MCP write-operation execution engine
│   └── audit.py               # Audit trail integration
│
├── tools/mcp/
│   ├── cold_chain.py          # ColdChainMCPServer
│   ├── erp.py                 # ERPMCPServer (SAP B1)
│   ├── hrms.py                # HRMSMCPServer (Zoho People)
│   ├── distributor.py         # DistributorMCPServer
│   ├── external_intel.py      # ExternalIntelMCPServer (IDSP, IMD, WHO)
│   ├── regulatory_kb.py       # RegulatoryKBMCPServer (CDSCO, DPCO)
│   └── communication.py       # CommunicationMCPServer (multi-channel)
│
├── utils/
│   └── logger.py              # structlog + immutable JSONL audit trail
│
├── logs/
│   └── audit.jsonl            # Append-only audit log
│
└── tests/
    ├── test_authority_matrix.py
    ├── test_drug_stability.py
    ├── test_ingestion.py
    └── test_integration.py
```

---

## Design Principles

1. **Tier 1 agents only propose** — they never call MCP write operations directly
2. **CRITIQUE before COMPLIANCE** — quality gate before regulatory gate
3. **NEXUS sees all** — only agent with full network-wide view
4. **Fail closed** — COMPLIANCE returns NON_COMPLIANT when regulatory KB is unavailable
5. **Patient safety is absolute** — SEVERE/FREEZE quarantines bypass CRITIQUE delays
6. **Every decision is audited** — immutable JSONL trail with outcome updates from CHRONICLE
7. **Scenario forecasts, not point estimates** — PULSE always provides confidence intervals

---

## KPI Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold chain compliance | ≥99.8% | Hours in range / total hours |
| Expiry write-off rate | <0.8% | Write-off value / total inventory value |
| Stockout rate | <0.2% | SKU-hours out of stock / total SKU-hours |
| Schedule H compliance | 100% | Stores with pharmacist present / total operating hours |
| Demand forecast MAPE | <12% | Measured weekly by CHRONICLE |
