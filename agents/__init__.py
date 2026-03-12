"""
Agents package — PharmaIQ multi-agent system.

Eight agents in three tiers:

Tier 1 — Operational (domain experts, propose only):
  SENTINEL  — Cold chain guardian
  PULSE     — Demand and epidemic intelligence
  AEGIS     — Staffing and compliance shield
  MERIDIAN  — Expiry and inventory lifecycle

Tier 2 — Validation (adversarial, block/allow):
  CRITIQUE  — Adversarial quality validation (5 dimensions)
  COMPLIANCE — Regulatory verification

Tier 3 — Meta (synthesis and learning):
  NEXUS     — Cross-domain synthesis + authority matrix enforcer
  CHRONICLE — Institutional memory + learning
"""

from agents.sentinel import sentinel_node, SentinelAgent
from agents.pulse import pulse_node, PulseAgent
from agents.aegis import aegis_node, AegisAgent
from agents.meridian import meridian_node, MeridianAgent
from agents.critique import critique_node, CritiqueAgent
from agents.compliance import compliance_node, ComplianceAgent
from agents.nexus import nexus_node, NexusAgent
from agents.chronicle import chronicle_entry_node, chronicle_exit_node, ChronicleAgent

__all__ = [
    # LangGraph node functions
    "sentinel_node",
    "pulse_node",
    "aegis_node",
    "meridian_node",
    "critique_node",
    "compliance_node",
    "nexus_node",
    "chronicle_entry_node",
    "chronicle_exit_node",
    # Agent classes (for testing and direct instantiation)
    "SentinelAgent",
    "PulseAgent",
    "AegisAgent",
    "MeridianAgent",
    "CritiqueAgent",
    "ComplianceAgent",
    "NexusAgent",
    "ChronicleAgent",
]
