"""
PharmaIQ – Prometheus Metrics

Exposes /metrics endpoint compatible with Grafana + Prometheus scraping.

Counters / Gauges:
  pharmaiq_cycle_duration_seconds   — histogram of graph run durations
  pharmaiq_agent_calls_total        — counter per agent name
  pharmaiq_decisions_total          — counter by verdict + agent
  pharmaiq_escalations_total        — counter by action (created/approved/rejected)
  pharmaiq_ws_connections           — gauge of current WebSocket clients
  pharmaiq_signal_significance      — histogram of ingested signal significance scores
  pharmaiq_cold_chain_excursions_total — counter by excursion type
"""
from __future__ import annotations

from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    REGISTRY,
)
from fastapi import Response

# ── Metrics ────────────────────────────────────────────────────────────────────
CYCLE_DURATION = Histogram(
    "pharmaiq_cycle_duration_seconds",
    "Time to complete a full 10-node LangGraph cycle",
    buckets=[1, 2, 5, 10, 20, 30, 60],
)

AGENT_CALLS = Counter(
    "pharmaiq_agent_calls_total",
    "Total agent node invocations",
    labelnames=["agent"],
)

DECISIONS = Counter(
    "pharmaiq_decisions_total",
    "Total decisions produced by NEXUS",
    labelnames=["verdict", "agent"],
)

ESCALATIONS = Counter(
    "pharmaiq_escalations_total",
    "Total escalation lifecycle events",
    labelnames=["action"],  # created | approved | rejected | expired
)

WS_CONNECTIONS = Gauge(
    "pharmaiq_ws_connections",
    "Current number of active WebSocket connections",
)

SIGNAL_SIGNIFICANCE = Histogram(
    "pharmaiq_signal_significance",
    "Significance score of ingested signals",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

COLD_CHAIN_EXCURSIONS = Counter(
    "pharmaiq_cold_chain_excursions_total",
    "Total cold chain excursion events recorded",
    labelnames=["excursion_type"],  # MINOR | MODERATE | SEVERE | FREEZE
)

HTTP_REQUESTS = Counter(
    "pharmaiq_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)


# ── FastAPI route handler ──────────────────────────────────────────────────────
async def metrics_endpoint() -> Response:
    """Prometheus scrape endpoint — returns text/plain metrics."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


# ── Convenience helpers ────────────────────────────────────────────────────────
def record_agent_call(agent_name: str) -> None:
    AGENT_CALLS.labels(agent=agent_name).inc()


def record_decision(verdict: str, agent: str) -> None:
    DECISIONS.labels(verdict=verdict, agent=agent).inc()


def record_escalation(action: str) -> None:
    ESCALATIONS.labels(action=action).inc()


def record_cold_chain_excursion(excursion_type: str) -> None:
    COLD_CHAIN_EXCURSIONS.labels(excursion_type=excursion_type).inc()
