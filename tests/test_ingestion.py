"""
Unit tests for the signal ingestion and routing layer.
"""

import pytest
from graph.ingestion import (
    SignalType,
    CycleType,
    classify_signal,
    determine_cycle_type,
    compute_signal_significance,
    passes_significance_gate,
    build_initial_state,
    CYCLE_AGENT_MAP,
)


class TestSignalClassification:
    """Test incoming signal taxonomy classification."""

    def test_cold_chain_event_classified_correctly(self):
        event = {"event_type": "cold_chain_temperature_breach", "source": "iot", "data": {}}
        assert classify_signal(event) == SignalType.COLD_CHAIN_ALERT

    def test_epidemic_event_classified_correctly(self):
        event = {"event_type": "epidemic_signal", "source": "idsp", "data": {}}
        assert classify_signal(event) == SignalType.EPIDEMIC_SIGNAL

    def test_recall_notice_classified_correctly(self):
        event = {"event_type": "drug_recall", "source": "cdsco", "data": {}}
        assert classify_signal(event) == SignalType.RECALL_NOTICE

    def test_scheduled_event_classified_correctly(self):
        event = {"event_type": "scheduled_cycle", "source": "scheduler", "data": {}}
        assert classify_signal(event) == SignalType.SCHEDULED_FORECAST

    def test_staffing_event_classified_correctly(self):
        event = {"event_type": "pharmacist_sick_call", "source": "hrms", "data": {}}
        assert classify_signal(event) == SignalType.STAFFING_EVENT


class TestCycleTypeMapping:
    """Test scheduled cycle type determination by hour."""

    def test_hour_5_maps_to_morning_forecast(self):
        event = {"event_type": "scheduled", "source": "scheduler", "data": {}}
        result = determine_cycle_type(SignalType.SCHEDULED_FORECAST, event, current_hour=5)
        assert result == CycleType.MORNING_FORECAST

    def test_hour_13_maps_to_midday_reforecast(self):
        event = {"event_type": "scheduled", "source": "scheduler", "data": {}}
        result = determine_cycle_type(SignalType.SCHEDULED_FORECAST, event, current_hour=13)
        assert result == CycleType.MIDDAY_REFORECAST

    def test_cold_chain_signal_maps_to_reactive(self):
        event = {"event_type": "temperature_alert", "source": "iot", "data": {}}
        result = determine_cycle_type(SignalType.COLD_CHAIN_ALERT, event)
        assert result == CycleType.REACTIVE_COLD_CHAIN

    def test_recall_signal_maps_to_reactive_recall(self):
        event = {"event_type": "recall_notice", "source": "cdsco", "data": {}}
        result = determine_cycle_type(SignalType.RECALL_NOTICE, event)
        assert result == CycleType.REACTIVE_RECALL


class TestSignificanceGate:
    """Test significance scoring and gating."""

    def test_severe_temperature_breach_is_significant(self):
        event = {"event_type": "cold_chain", "source": "iot", "data": {"current_temp": 25.0}}
        sig = compute_signal_significance(SignalType.COLD_CHAIN_ALERT, event)
        assert sig > 0.5

    def test_normal_temperature_is_below_gate(self):
        event = {"event_type": "cold_chain", "source": "iot", "data": {"current_temp": 5.0}}
        sig = compute_signal_significance(SignalType.COLD_CHAIN_ALERT, event)
        # 5°C is within normal range — low significance
        assert sig < 0.5

    def test_all_recalls_pass_gate(self):
        """All recall notices should always pass the significance gate."""
        assert passes_significance_gate(SignalType.RECALL_NOTICE, 0.0) is True

    def test_all_staffing_events_pass_gate(self):
        """All staffing compliance events should always pass."""
        assert passes_significance_gate(SignalType.STAFFING_EVENT, 0.0) is True

    def test_low_confidence_epidemic_dropped(self):
        """Epidemic signal below 25% confidence should be dropped."""
        assert passes_significance_gate(SignalType.EPIDEMIC_SIGNAL, 0.10) is False

    def test_high_confidence_epidemic_passes(self):
        """Epidemic signal above 25% confidence should pass."""
        assert passes_significance_gate(SignalType.EPIDEMIC_SIGNAL, 0.60) is True


class TestCycleAgentMap:
    """Verify that the cycle agent map includes required agents for each cycle type."""

    def test_morning_forecast_includes_all_tier1_agents(self):
        agents = CYCLE_AGENT_MAP[CycleType.MORNING_FORECAST]
        for agent in ["SENTINEL", "PULSE", "AEGIS", "MERIDIAN"]:
            assert agent in agents, f"{agent} missing from MORNING_FORECAST cycle"

    def test_compliance_sweep_includes_aegis_and_sentinel(self):
        agents = CYCLE_AGENT_MAP[CycleType.COMPLIANCE_SWEEP]
        assert "AEGIS" in agents
        assert "SENTINEL" in agents

    def test_expiry_review_includes_meridian(self):
        agents = CYCLE_AGENT_MAP[CycleType.EXPIRY_REVIEW]
        assert "MERIDIAN" in agents

    def test_all_cycles_include_chronicle_entry(self):
        for cycle_type, agents in CYCLE_AGENT_MAP.items():
            assert "CHRONICLE_ENTRY" in agents, (
                f"{cycle_type} cycle missing CHRONICLE_ENTRY"
            )


class TestBuildInitialState:
    """Test initial state construction from raw events."""

    def test_initial_state_has_all_required_fields(self):
        state = build_initial_state(
            raw_event={"event_type": "test", "source": "test"},
            store_id="STORE_001",
            zone_id="DELHI_NCR",
            signal_type=SignalType.COLD_CHAIN_ALERT,
            cycle_type=CycleType.REACTIVE_COLD_CHAIN,
        )
        required_fields = [
            "store_id", "zone_id", "cycle_type", "signal_type",
            "route_to_critique", "route_to_compliance", "route_to_nexus",
            "cold_chain_alerts", "compliance_gaps", "critique_verdicts",
        ]
        for field in required_fields:
            assert field in state, f"Initial state missing field: {field}"

    def test_initial_routing_flags_all_false(self):
        state = build_initial_state(
            raw_event={},
            store_id="STORE_001",
            zone_id="DELHI_NCR",
            signal_type=SignalType.SCHEDULED_FORECAST,
            cycle_type=CycleType.MORNING_FORECAST,
        )
        assert state["route_to_critique"] is False
        assert state["route_to_compliance"] is False
        assert state["route_to_nexus"] is False
        assert state["route_to_execution"] is False
        assert state["cycle_complete"] is False
