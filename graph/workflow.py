"""
PharmaIQ LangGraph Workflow — Full StateGraph Wiring.

Topology:
  chronicle_entry → [sentinel | pulse | aegis | meridian] (parallel)
      ↓
  critique → compliance → nexus
      ↓                     ↓
  execution             chronicle_exit
      ↓
  chronicle_exit

The graph handles all 5 scheduled cycle types and all 4 reactive trigger types.
CHRONICLE runs at entry (inject context) and at exit (record outcomes).
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from graph.state import PharmaIQState
from graph.ingestion import (
    post_tier1_router,
    post_critique_router,
    post_compliance_router,
    post_nexus_router,
    post_execution_router,
)
from agents.sentinel import sentinel_node
from agents.pulse import pulse_node
from agents.aegis import aegis_node
from agents.meridian import meridian_node
from agents.critique import critique_node
from agents.compliance import compliance_node
from agents.nexus import nexus_node
from agents.chronicle import chronicle_entry_node, chronicle_exit_node
from graph.execution import execution_node
from utils.logger import get_logger

logger = get_logger("graph.workflow")


def build_pharmaiq_graph() -> StateGraph:
    """
    Construct and compile the full PharmaIQ multi-agent graph.

    Node execution order per cycle:
      1. chronicle_entry   (memory injection)
      2. sentinel          (cold chain monitoring)
      3. pulse             (demand/epidemic)
      4. aegis             (staffing/compliance)
      5. meridian          (expiry/inventory)
      6. critique          (adversarial validation)
      7. compliance        (regulatory verification)
      8. nexus             (cross-domain synthesis + authority enforcement)
      9. execution         (write actions to MCP servers)
      10. chronicle_exit   (outcome recording)

    Tier 1 agents (sentinel, pulse, aegis, meridian) run SEQUENTIALLY so that
    each agent can see proposals from preceding agents (e.g., AEGIS sees SENTINEL
    alerts before deciding on pharmacist deployment for patient counselling).
    """
    builder = StateGraph(PharmaIQState)

    # ── Register all nodes ─────────────────────────────────────────────────────
    builder.add_node("chronicle_entry", chronicle_entry_node)
    builder.add_node("sentinel", sentinel_node)
    builder.add_node("pulse", pulse_node)
    builder.add_node("aegis", aegis_node)
    builder.add_node("meridian", meridian_node)
    builder.add_node("critique", critique_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("nexus", nexus_node)
    builder.add_node("execution", execution_node)
    builder.add_node("chronicle_exit", chronicle_exit_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    builder.set_entry_point("chronicle_entry")

    # ── Tier 3 entry → Tier 1 sequential chain ─────────────────────────────────
    # Sequential execution allows each Tier 1 agent to see prior agents' proposals.
    # This is intentional: AEGIS must know about SENTINEL quarantines when planning
    # pharmacist deployment for patient counselling.
    builder.add_edge("chronicle_entry", "sentinel")
    builder.add_edge("sentinel", "pulse")
    builder.add_edge("pulse", "aegis")
    builder.add_edge("aegis", "meridian")

    # ── Tier 1 → Tier 2: route to CRITIQUE if any agent flagged proposals ─────
    builder.add_conditional_edges(
        "meridian",
        post_tier1_router,
        {
            "critique": "critique",
            "compliance": "compliance",
            "nexus": "nexus",
        },
    )

    # ── Tier 2 chain: CRITIQUE → COMPLIANCE (always sequential) ───────────────
    builder.add_conditional_edges(
        "critique",
        post_critique_router,
        {"compliance": "compliance"},
    )

    builder.add_conditional_edges(
        "compliance",
        post_compliance_router,
        {"nexus": "nexus"},
    )

    # ── Tier 3 synthesis → execution or chronicle ─────────────────────────────
    builder.add_conditional_edges(
        "nexus",
        post_nexus_router,
        {
            "execution": "execution",
            "chronicle_exit": "chronicle_exit",
        },
    )

    # ── Post-execution: always go to CHRONICLE ─────────────────────────────────
    builder.add_conditional_edges(
        "execution",
        post_execution_router,
        {"chronicle_exit": "chronicle_exit"},
    )

    # ── CHRONICLE exit → END ───────────────────────────────────────────────────
    builder.add_edge("chronicle_exit", END)

    logger.info("pharmaiq_graph_compiled", nodes=10)
    return builder


def get_compiled_graph():
    """
    Returns the compiled LangGraph runnable.
    Cache this at application startup — do not rebuild per request.

    When LANGCHAIN_TRACING_V2=true is set in the environment (populated by
    gemini_client module on import), LangGraph automatically submits full
    graph traces — node execution, state transitions, and timing — to LangSmith.
    """
    builder = build_pharmaiq_graph()
    return builder.compile(name="PharmaIQ")


# ── Module-level compiled graph ────────────────────────────────────────────────
# Imported by main.py and tests
graph = get_compiled_graph()
