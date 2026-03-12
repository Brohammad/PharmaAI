"""
PharmaIQ – Structured Logger & Audit Trail
All agent decisions, MCP calls, and system events are logged here.
The audit log (JSONL) is immutable — entries are only ever appended.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog


# ── Bootstrap structlog ────────────────────────────────────────────────────────
def configure_logging(log_level: str = "INFO", audit_log_path: str = "logs/audit.jsonl") -> None:
    """
    Call once at application startup.
    Sets up:
      - structlog for all application code (console + JSON)
      - A dedicated audit JSONL file for immutable decision records
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Ensure audit log directory exists
    audit_path = Path(audit_log_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


# ── Immutable Audit Log ────────────────────────────────────────────────────────

class AuditLogger:
    """
    Writes immutable JSONL audit records for every decision.
    Each record is a single JSON object per line.

    Regulatory requirement: audit trail must include:
      - Decision ID (UUID)
      - Timestamp (UTC ISO8601)
      - Agent that made the decision
      - Data sources consulted (with freshness timestamps)
      - Confidence level
      - CRITIQUE verdict (if applicable)
      - COMPLIANCE verdict (if applicable)
      - Authority level applied
      - Action taken or escalated
      - Outcome (filled in later by CHRONICLE)
    """

    def __init__(self, audit_log_path: str = "logs/audit.jsonl") -> None:
        self._path = Path(audit_log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger("audit")

    def record(
        self,
        *,
        agent: str,
        event_type: str,
        store_id: str | None = None,
        zone_id: str | None = None,
        domain: str,
        action: str,
        authority_level: str,
        reasoning_summary: str,
        data_sources: list[dict[str, Any]] | None = None,
        confidence: float | None = None,
        critique_verdict: str | None = None,
        compliance_verdict: str | None = None,
        estimated_cost_lakh: float | None = None,
        outcome: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """
        Append one audit record to the JSONL file.
        Returns the generated decision_id.
        """
        decision_id = str(uuid.uuid4())
        record: dict[str, Any] = {
            "decision_id": decision_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "event_type": event_type,
            "store_id": store_id,
            "zone_id": zone_id,
            "domain": domain,
            "action": action,
            "authority_level": authority_level,
            "reasoning_summary": reasoning_summary,
            "data_sources": data_sources or [],
            "confidence": confidence,
            "critique_verdict": critique_verdict,
            "compliance_verdict": compliance_verdict,
            "estimated_cost_lakh": estimated_cost_lakh,
            "outcome": outcome,
            **(extra or {}),
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._logger.info(
            "audit_record_written",
            decision_id=decision_id,
            agent=agent,
            action=action,
            authority=authority_level,
        )
        return decision_id

    def update_outcome(self, decision_id: str, outcome: str, extra: dict[str, Any] | None = None) -> None:
        """
        CHRONICLE calls this to fill in the actual outcome of a decision.
        Appends a separate outcome record linked by decision_id.
        """
        outcome_record: dict[str, Any] = {
            "record_type": "OUTCOME",
            "decision_id": decision_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
            **(extra or {}),
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(outcome_record, ensure_ascii=False) + "\n")


# ── Module-level singletons (initialised after configure_logging is called) ────
_audit_logger: AuditLogger | None = None


def get_audit_logger(audit_log_path: str = "logs/audit.jsonl") -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(audit_log_path)
    return _audit_logger
