"""
Mock data generators for the PharmaIQ frontend.
In production these come from the live MCP servers and audit log.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago(minutes: int = 0, hours: int = 0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes, hours=hours)
    return dt.isoformat()


# ── KPI summary ───────────────────────────────────────────────────────────────

def get_kpi_summary() -> dict[str, Any]:
    return {
        # Dashboard KPI card keys (must match frontend exactly)
        "stores_online":           318,
        "active_alerts":           random.randint(0, 6),
        "cold_chain_risk_pct":     round(random.uniform(1.5, 8.0), 1),
        "schedule_h_compliance":   round(random.uniform(97.5, 100.0), 1),
        "demand_mape":             round(random.uniform(11.0, 17.5), 1),
        "active_escalations":      random.randint(0, 3),
        "pharmacist_coverage":     round(random.uniform(91.0, 98.0), 1),
        "expiry_risk_units":       random.randint(8, 24),
        "cycles_today":            random.randint(42, 120),
        "decisions_approved":      random.randint(38, 110),
        "decisions_escalated":     random.randint(0, 5),
        "avg_cycle_time_s":        round(random.uniform(4.2, 9.8), 1),
        # Extra context fields
        "total_stores":            320,
        "agents_active":           8,
        "mcp_servers_online":      7,
        "system_health":           "healthy",
        "last_cycle_completed_at": _ago(minutes=random.randint(2, 45)),
        "timestamp":               _now(),
    }


# ── Agent activity feed ───────────────────────────────────────────────────────

_AGENT_EVENTS = [
    ("SENTINEL", "cold_chain", "SEVERE excursion detected at STORE_MUM_042 — FRIDGE_B2 → 19.4°C", "critical"),
    ("SENTINEL", "cold_chain", "Batch quarantine executed: Hepatitis B Vaccine — 240 units", "warning"),
    ("PULSE", "demand", "Dengue demand surge forecast: +340% ORS, +280% Paracetamol — East Delhi zone", "info"),
    ("AEGIS", "staffing", "Schedule H gap closed: Pharmacist Priya Sharma redeployed to STORE_DEL_018", "success"),
    ("MERIDIAN", "inventory", "Expiry risk: Insulin Glargine batch EXP2026-04 — 18 days, 0.9 velocity", "warning"),
    ("CRITIQUE", "validation", "CHALLENGED: MERIDIAN transfer proposal — insufficient demand evidence", "info"),
    ("COMPLIANCE", "regulatory", "COMPLIANT: Cold chain quarantine — CDSCO Schedule C §7.3 satisfied", "success"),
    ("NEXUS", "synthesis", "Cross-domain resolved: fridge conflict → SENTINEL priority, MERIDIAN deferred 4h", "info"),
    ("CHRONICLE", "memory", "Pattern recorded: Sensor false-positive rate 23% at stores >4yr fridge age", "info"),
    ("SENTINEL", "cold_chain", "MINOR excursion resolved: STORE_BLR_011 — temperature normalised 6.2°C", "success"),
    ("PULSE", "demand", "Epidemic confidence raised to 0.87: IDSP confirms dengue cluster — District 7", "warning"),
    ("AEGIS", "staffing", "Compliance sweep: 317/320 stores pharmacist-present ✓", "success"),
    ("NEXUS", "synthesis", "Escalation sent: Emergency reorder >3x requires CFO approval — ₹3.2L", "warning"),
    ("MERIDIAN", "inventory", "Inter-store transfer approved: Metformin 500mg — STORE_DEL_019 → STORE_DEL_004", "success"),
]


def get_live_events(limit: int = 20) -> list[dict[str, Any]]:
    events = []
    for i in range(limit):
        template = _AGENT_EVENTS[i % len(_AGENT_EVENTS)]
        events.append({
            "id": str(uuid.uuid4()),
            "agent": template[0],
            "domain": template[1],
            "message": template[2],
            "severity": template[3],
            "timestamp": _ago(minutes=i * random.randint(1, 8)),
        })
    return events


# ── Cold chain ────────────────────────────────────────────────────────────────

_STORE_IDS = [f"STORE_{city}_{str(n).zfill(3)}" for city in ["DEL", "MUM", "BLR", "HYD", "CHN"] for n in range(1, 17)]

def get_cold_chain_overview() -> dict[str, Any]:
    units = []
    for store_id in random.sample(_STORE_IDS, 40):
        for unit in ["FRIDGE_A1", "FRIDGE_B1", "FRIDGE_C1"]:
            temp = round(random.gauss(5.5, 2.0), 1)
            status = "NORMAL"
            if temp > 15:
                status = "SEVERE"
            elif temp > 8:
                status = "MODERATE"
            elif temp < 0:
                status = "FREEZE"
            elif temp > 6:
                status = "MINOR"
            units.append({
                "store_id": store_id,
                "unit_id": unit,
                "temperature_c": temp,
                "status": status,
                "humidity_pct": round(random.uniform(40, 75), 1),
                "door_open": random.random() < 0.03,
                "sensor_status": "ONLINE" if random.random() > 0.02 else "OFFLINE",
                "last_updated": _ago(minutes=random.randint(0, 3)),
            })
    return {
        "total_units": 960,
        "units_monitored": 947,
        "units_normal": sum(1 for u in units if u["status"] == "NORMAL"),
        "units_alert": sum(1 for u in units if u["status"] != "NORMAL"),
        "units": units[:120],
        "timestamp": _now(),
    }


def get_cold_chain_alerts() -> list[dict[str, Any]]:
    alerts = []
    excursion_types = ["MINOR", "MODERATE", "SEVERE", "FREEZE"]
    drugs = ["Hepatitis B Vaccine", "Insulin Glargine", "Polio IPV", "Rotavirus Vaccine", "Insulin Regular"]
    for i in range(random.randint(2, 8)):
        exc = random.choice(excursion_types[:3])
        alerts.append({
            "alert_id": str(uuid.uuid4()),
            "store_id": random.choice(_STORE_IDS),
            "unit_id": f"FRIDGE_{random.choice(['A1','B1','B2','C1'])}",
            "excursion_type": exc,
            "current_temp": round(random.uniform(9, 22), 1),
            "drug_affected": random.choice(drugs),
            "batches_affected": random.randint(1, 4),
            "cumulative_minutes": random.randint(5, 180),
            "sentinel_recommendation": "Quarantine batch and request maintenance inspection.",
            "critique_verdict": random.choice(["VALIDATED", "VALIDATED", "CHALLENGED"]),
            "status": random.choice(["PENDING", "EXECUTING", "RESOLVED"]),
            "created_at": _ago(minutes=random.randint(5, 240)),
        })
    return alerts


def get_temperature_trend(unit_id: str) -> list[dict[str, Any]]:
    points = []
    base_temp = random.uniform(4.0, 7.0)
    for i in range(48):
        spike = 0.0
        if 20 <= i <= 28:
            spike = random.uniform(0, 6.0)
        temp = round(base_temp + random.gauss(0, 0.3) + spike, 2)
        points.append({
            "time": _ago(minutes=(48 - i) * 30),
            "temperature_c": temp,
            "threshold_max": 8.0,
            "threshold_min": 2.0,
        })
    return points


# ── Demand / Epidemic ─────────────────────────────────────────────────────────

def get_epidemic_signals() -> list[dict[str, Any]]:
    diseases = [
        ("Dengue Fever",     0.87, 2.8, 3, "East Delhi"),
        ("Influenza H3N2",   0.62, 1.9, 5, "Mumbai South"),
        ("Gastroenteritis",  0.44, 1.4, 7, "Bangalore North"),
        ("Chikungunya",      0.31, 1.2, 9, "Chennai Central"),
    ]
    return [
        {
            "signal_id":        str(uuid.uuid4()),
            "disease":          d[0],
            "confidence":       d[1],          # float 0–1, used by frontend for %
            "demand_multiplier": d[2],          # frontend reads demand_multiplier
            "peak_week":        d[3],           # frontend reads peak_week
            "affected_zones":   [d[4]],         # frontend reads affected_zones (list)
            "key_drugs":        _epidemic_drugs(d[0]),
            "affected_stores":  random.randint(4, 22),
            "lead_time_days":   random.randint(3, 8),
            "status":           "ACTIVE",
            "data_sources":     ["IDSP", "Google Trends", "IMD"],
        }
        for d in diseases
    ]


def _epidemic_drugs(disease: str) -> list[str]:
    mapping = {
        "Dengue Fever":    ["Paracetamol", "Dengue NS1 Kit", "ORS Sachets", "Platelet Boosters"],
        "Influenza H3N2":  ["Oseltamivir", "Paracetamol", "Cetirizine", "Vitamin C"],
        "Gastroenteritis": ["ORS Sachets", "Zinc Sulfate", "Domperidone", "Probiotics"],
        "Chikungunya":     ["Paracetamol", "Ibuprofen", "Chloroquine", "Multivitamins"],
    }
    return mapping.get(disease, ["Paracetamol"])


def get_demand_forecast(store_id: str = "STORE_DEL_001") -> list[dict[str, Any]]:
    skus = [
        ("SKU-1001", "Paracetamol 650mg",   "OTC"),
        ("SKU-1002", "ORS Sachets",          "OTC"),
        ("SKU-1003", "Dengue NS1 Test Kit",  "Diagnostics"),
        ("SKU-1004", "Metformin 500mg",      "Schedule H"),
        ("SKU-1005", "Insulin Glargine",     "Schedule H"),
        ("SKU-1006", "Amoxicillin 500mg",    "Schedule H"),
    ]
    result = []
    for sku_id, name, category in skus:
        baseline = random.randint(20, 200)
        epidemic_mult = round(random.uniform(1.0, 3.5), 2)
        adjusted = round(baseline * epidemic_mult)
        conf = round(random.uniform(0.60, 0.95), 2)
        action = "REORDER" if epidemic_mult > 2.0 else "MONITOR" if epidemic_mult > 1.3 else "OK"
        result.append({
            "sku_id":              sku_id,
            "drug_name":           name,          # frontend reads drug_name
            "category":            category,
            "baseline_demand":     baseline,       # frontend reads baseline_demand
            "epidemic_adjustment": epidemic_mult,  # frontend reads epidemic_adjustment
            "adjusted_forecast":   adjusted,       # frontend reads adjusted_forecast
            "confidence":          conf,           # float 0–1
            "horizon_days":        7,
            "recommended_action":  action,         # frontend reads recommended_action
            "reorder_triggered":   epidemic_mult > 1.5,
        })
    return result


def get_forecast_chart_data() -> list[dict[str, Any]]:
    """28-day daily forecast with scenario bands for the main chart."""
    data = []
    base = 150
    for day in range(28):
        epidemic_factor = 1 + (day * 0.04)
        point = {
            "date":              (datetime.now(timezone.utc) + timedelta(days=day)).strftime("%d %b"),
            "baseline":          round(base + random.gauss(0, 10)),
            "epidemic_high":     round(base * epidemic_factor * 1.3 + random.gauss(0, 8)),
            "epidemic_weighted": round(base * epidemic_factor + random.gauss(0, 8)),
            "historic_avg":      round(base * 0.85 + random.gauss(0, 5)),
        }
        data.append(point)
    return data


# ── Staffing ──────────────────────────────────────────────────────────────────

def get_staffing_overview() -> dict[str, Any]:
    has_gap = random.random() > 0.4
    gaps = [
        {
            "store_id": "STORE_DEL_018",
            "shift": "Morning",
            "severity": "HIGH",
            "gap_hours": round(random.uniform(1.0, 4.5), 1),
            "suggested_action": "Deploy Priya Sharma (D.Pharm) from STORE_DEL_021 — ETA 18 min",
        },
        {
            "store_id": "STORE_MUM_042",
            "shift": "Night",
            "severity": "MEDIUM",
            "gap_hours": round(random.uniform(0.5, 2.0), 1),
            "suggested_action": "Activate on-call pharmacist — Rajan Iyer",
        },
    ] if has_gap else []

    return {
        "pharmacist_coverage_pct":    round(random.uniform(91.0, 98.0), 1),
        "schedule_h_compliance_pct":  round(random.uniform(97.5, 100.0), 1),
        "active_shifts":              random.randint(280, 318),
        "night_shift_gaps":           len([g for g in gaps if g["shift"] == "Night"]),
        "active_gaps":                gaps,
        "zone_utilisation": [
            {"zone": "Delhi NCR",   "utilisation_pct": round(random.uniform(70, 96), 1)},
            {"zone": "Mumbai",      "utilisation_pct": round(random.uniform(65, 90), 1)},
            {"zone": "Bengaluru",   "utilisation_pct": round(random.uniform(68, 88), 1)},
            {"zone": "Chennai",     "utilisation_pct": round(random.uniform(72, 92), 1)},
            {"zone": "Hyderabad",   "utilisation_pct": round(random.uniform(60, 85), 1)},
        ],
        "total_stores": 320,
        "pharmacist_present": 317,
    }


# ── Inventory / Expiry ─────────────────────────────────────────────────────────

def get_expiry_risks() -> list[dict[str, Any]]:
    skus = [
        ("Insulin Glargine 100U/mL", "INS-GLAR-001", 18, 0.92, "TRANSFER"),
        ("Hepatitis A Vaccine",      "HAV-001",       24, 0.85, "TRANSFER"),
        ("Rotavirus Vaccine",        "ROT-001",       31, 0.78, "MARKDOWN"),
        ("Metformin SR 500mg",       "MET-SR-001",    45, 0.65, "MARKDOWN"),
        ("Amlodipine 5mg",           "AML-001",       52, 0.55, "MONITOR"),
        ("Cetirizine 10mg",          "CET-001",       58, 0.48, "MONITOR"),
        ("Azithromycin 500mg",       "AZI-001",       62, 0.42, "MONITOR"),
    ]
    result = []
    for sku in skus:
        qty = random.randint(40, 400)
        result.append({
            "drug_name":                sku[0],
            "sku_id":                   sku[1],
            "batch_id":                 f"BATCH-{uuid.uuid4().hex[:8].upper()}",
            "store_id":                 random.choice(_STORE_IDS),
            "days_until_expiry":        sku[2],      # key the Inventory page uses
            "risk_score":               sku[3],
            "quantity":                 qty,
            "estimated_loss_value":     round(qty * random.uniform(8, 120), 0),
            "recommended_intervention": sku[4],
            "critique_verdict":         random.choice(["VALIDATED", "VALIDATED", "CHALLENGED"]),
        })
    return result


# ── NEXUS Decisions ───────────────────────────────────────────────────────────

def get_recent_decisions(limit: int = 15) -> list[dict[str, Any]]:
    templates = [
        ("Batch Quarantine",              "SENTINEL",    "TIER_1",          "APPROVED",               "VALIDATED",  "COMPLIANT"),
        ("Emergency Reorder 2.1x",        "PULSE",       "TIER_2",          "APPROVED",               "VALIDATED",  "COMPLIANT"),
        ("Pharmacist Redeployment",       "AEGIS",       "TIER_2",          "APPROVED_WITH_CONDITIONS","VALIDATED",  "COMPLIANT"),
        ("Inter-store Transfer",          "MERIDIAN",    "TIER_1",          "APPROVED",               "CHALLENGED", "COMPLIANT"),
        ("Emergency Reorder 3.4x",        "PULSE",       "HUMAN_REQUIRED",  "ESCALATED",              "VALIDATED",  "COMPLIANT"),
        ("Maintenance Request",           "SENTINEL",    "TIER_1",          "APPROVED",               "VALIDATED",  "COMPLIANT"),
        ("CDSCO Regulatory Notification", "COMPLIANCE",  "HUMAN_REQUIRED",  "ESCALATED",              "VALIDATED",  "COMPLIANT"),
        ("Demand Reforecast",             "PULSE",       "TIER_1",          "APPROVED",               "VALIDATED",  "COMPLIANT"),
        ("Expiry Write-off Prevention",   "MERIDIAN",    "TIER_2",          "APPROVED",               "VALIDATED",  "COMPLIANT"),
        ("Schedule H Gap Closure",        "AEGIS",       "TIER_1",          "APPROVED",               "VALIDATED",  "COMPLIANT"),
    ]
    decisions = []
    for i in range(limit):
        t = templates[i % len(templates)]
        decisions.append({
            "decision_id":        str(uuid.uuid4()),
            "action_type":        t[0],
            "source_agent":       t[1],
            "authority_level":    t[2],
            "nexus_verdict":      t[3],
            "critique_verdict":   t[4],
            "compliance_verdict": t[5],
            "store_id":           random.choice(_STORE_IDS),
            "timestamp":          _ago(hours=i // 3, minutes=(i * 17) % 60),
        })
    return decisions


def get_escalation_queue() -> list[dict[str, Any]]:
    return [
        {
            "escalation_id":          str(uuid.uuid4()),
            "action_type":            "Emergency Reorder — Paracetamol 650mg",
            "reason_for_escalation":  "PULSE forecasts 340% demand surge due to dengue cluster. Order 3.4× baseline. Exceeds TIER_2 authority.",
            "nexus_recommendation":   "Approve with condition: split into two orders, second tranche contingent on day-3 actual demand.",
            "store_id":               "STORE_DEL_007",
            "financial_impact":       320000,
            "expires_in":             "45m",
            "status":                 "PENDING_HUMAN_APPROVAL",
            "source_agent":           "NEXUS",
            "created_at":             _ago(minutes=12),
        },
        {
            "escalation_id":          str(uuid.uuid4()),
            "action_type":            "Cross-Zone Pharmacist Redeployment",
            "reason_for_escalation":  "AEGIS: Schedule H gap at STORE_DEL_018. Nearest qualified pharmacist is in adjacent zone — cross-zone redeployment requires HR approval.",
            "nexus_recommendation":   "Approve redeployment. Estimated cost ₹1,200 travel allowance. Gap risk outweighs cost.",
            "store_id":               "STORE_DEL_018",
            "financial_impact":       1200,
            "expires_in":             "30m",
            "status":                 "PENDING_HUMAN_APPROVAL",
            "source_agent":           "NEXUS",
            "created_at":             _ago(minutes=28),
        },
    ]
