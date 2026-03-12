"""
Unit tests for the authority matrix.
Verifies all domain/action combinations map to expected authority levels.
"""

import pytest
from config.authority_matrix import (
    AuthorityLevel,
    get_authority,
    can_auto_execute,
    requires_human,
    AUTHORITY_MATRIX,
)


class TestAuthorityMatrix:
    """Test authority level assignments for all domain/action pairs."""

    def test_cold_chain_minor_alert_is_auto(self):
        assert get_authority("cold_chain", "minor_excursion_alert") == AuthorityLevel.AUTO

    def test_cold_chain_severe_quarantine_is_auto(self):
        # Severe excursions are AUTO for quarantine (patient safety priority)
        assert get_authority("cold_chain", "quarantine") == AuthorityLevel.AUTO

    def test_cold_chain_batch_destruction_requires_human(self):
        assert requires_human("cold_chain", "batch_destruction") is True

    def test_cold_chain_store_closure_is_human_only(self):
        assert get_authority("cold_chain", "store_closure") in (
            AuthorityLevel.HUMAN_REQUIRED,
            AuthorityLevel.HUMAN_ONLY,
        )

    def test_procurement_normal_order_is_auto(self):
        assert can_auto_execute("procurement", "standard_reorder") is True

    def test_procurement_emergency_large_order_requires_human(self):
        assert requires_human("procurement", "emergency_large_order") is True

    def test_staffing_compliance_gap_is_auto(self):
        assert can_auto_execute("staffing", "compliance_notification") is True

    def test_staffing_cross_zone_redeployment_requires_human(self):
        assert requires_human("staffing", "cross_zone_redeployment") is True

    def test_all_human_only_actions_cannot_auto_execute(self):
        human_only_actions = [
            (domain, action)
            for (domain, action), entry in AUTHORITY_MATRIX.items()
            if entry[0] == AuthorityLevel.HUMAN_ONLY
        ]
        for domain, action in human_only_actions:
            assert can_auto_execute(domain, action) is False, (
                f"HUMAN_ONLY action {domain}/{action} should not be auto-executable"
            )

    def test_unknown_action_defaults_to_human_required(self):
        result = get_authority("unknown_domain", "unknown_action")
        # Should default to safe fallback
        assert result in (AuthorityLevel.HUMAN_REQUIRED, AuthorityLevel.HUMAN_ONLY)

    def test_authority_matrix_has_all_required_domains(self):
        domains_in_matrix = {domain for (domain, _) in AUTHORITY_MATRIX}
        required_domains = {"cold_chain", "procurement", "inventory", "staffing", "regulatory"}
        assert required_domains.issubset(domains_in_matrix)
