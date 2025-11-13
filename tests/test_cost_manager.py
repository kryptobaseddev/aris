"""Tests for cost tracking and budget management system.

Tests cover:
- Cost accumulation per hop and session
- Budget threshold warnings and enforcement
- Cost breakdown calculations
- Cost history and reporting
- Export functionality
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import tempfile

from aris.core.cost_manager import (
    CostManager,
    CostBreakdown,
    BudgetAlert,
    BudgetThreshold,
)
from aris.storage.session_manager import SessionManager
from aris.storage.models import ResearchSession, ResearchHop
from aris.models.research import ResearchQuery, ResearchDepth


class TestCostBreakdown:
    """Tests for CostBreakdown data class."""

    def test_cost_breakdown_creation(self):
        """Test creating cost breakdown."""
        breakdown = CostBreakdown(
            tavily_cost=0.05,
            llm_tokens=1000,
            llm_cost=0.01,
        )

        assert breakdown.tavily_cost == 0.05
        assert breakdown.llm_tokens == 1000
        assert breakdown.llm_cost == 0.01
        assert breakdown.total_cost == 0.06

    def test_cost_breakdown_to_dict(self):
        """Test converting cost breakdown to dictionary."""
        breakdown = CostBreakdown(
            tavily_cost=0.05,
            llm_tokens=1000,
            llm_cost=0.01,
        )

        result = breakdown.to_dict()
        assert result["tavily_cost"] == 0.05
        assert result["llm_tokens"] == 1000
        assert result["llm_cost"] == 0.01
        assert result["total_cost"] == 0.06
        assert "timestamp" in result


class TestBudgetAlert:
    """Tests for BudgetAlert data class."""

    def test_budget_alert_creation(self):
        """Test creating budget alert."""
        alert = BudgetAlert(
            threshold=BudgetThreshold.WARNING_HIGH,
            current_cost=0.45,
            budget_limit=0.50,
            percentage_used=0.9,
            message="Budget warning (90%): $0.4500 / $0.5000",
        )

        assert alert.threshold == BudgetThreshold.WARNING_HIGH
        assert alert.current_cost == 0.45
        assert alert.budget_limit == 0.50
        assert alert.percentage_used == 0.9

    def test_budget_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = BudgetAlert(
            threshold=BudgetThreshold.CRITICAL,
            current_cost=0.50,
            budget_limit=0.50,
            percentage_used=1.0,
            message="Budget exhausted: $0.5000 / $0.5000",
        )

        result = alert.to_dict()
        assert result["threshold"] == "CRITICAL"
        assert result["current_cost"] == 0.50
        assert result["budget_limit"] == 0.50
        assert result["percentage_used"] == 100.0


class TestCostManager:
    """Tests for CostManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for cost history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cost_manager(self, temp_dir):
        """Create cost manager instance."""
        session_manager = SessionManager(":memory:")
        cost_manager = CostManager(session_manager, cost_history_dir=temp_dir)
        return cost_manager

    def test_cost_manager_initialization(self, cost_manager):
        """Test cost manager initialization."""
        assert cost_manager.TAVILY_COST_PER_SEARCH == 0.01
        assert cost_manager.LLM_COST_PER_1K_TOKENS == 0.01
        assert cost_manager.cost_history_dir.exists()

    def test_set_pricing(self, cost_manager):
        """Test updating pricing configuration."""
        cost_manager.set_pricing(
            tavily_per_search=0.02,
            llm_per_1k_tokens=0.015,
        )

        assert CostManager.TAVILY_COST_PER_SEARCH == 0.02
        assert CostManager.LLM_COST_PER_1K_TOKENS == 0.015

    @pytest.mark.asyncio
    async def test_track_hop_cost_with_calculations(self, cost_manager):
        """Test tracking hop cost with automatic calculations."""
        # Reset pricing first
        cost_manager.set_pricing()

        # Create session
        session = ResearchSession(
            id="test-session-1",
            query_text="test query",
            budget_target=0.50,
        )
        cost_manager.session_manager.session = session

        # Track hop cost
        breakdown, alert = await cost_manager.track_hop_cost(
            session_id="test-session-1",
            hop_number=1,
            tavily_searches=2,
            llm_tokens=1500,
        )

        # Should calculate: 2*0.01 + (1500/1000)*0.01 = 0.035
        assert breakdown.tavily_cost == 0.02
        assert breakdown.llm_tokens == 1500
        assert abs(breakdown.llm_cost - 0.015) < 0.001
        assert abs(breakdown.total_cost - 0.035) < 0.001

    @pytest.mark.asyncio
    async def test_track_hop_cost_with_overrides(self, cost_manager):
        """Test tracking hop cost with override values."""
        session = ResearchSession(
            id="test-session-2",
            query_text="test query",
            budget_target=0.50,
        )
        cost_manager.session_manager.session = session

        breakdown, _ = await cost_manager.track_hop_cost(
            session_id="test-session-2",
            hop_number=1,
            tavily_cost_override=0.025,
            llm_cost_override=0.03,
        )

        assert breakdown.tavily_cost == 0.025
        assert breakdown.llm_cost == 0.03
        assert breakdown.total_cost == 0.055

    @pytest.mark.asyncio
    async def test_budget_threshold_75_percent(self, cost_manager):
        """Test budget warning at 75% threshold."""
        cost_manager.set_pricing()

        session = ResearchSession(
            id="test-session-3",
            query_text="test query",
            budget_target=0.50,
            total_cost=0.375,  # 75% of budget
        )
        cost_manager.session_manager.session = session

        alert = await cost_manager.check_budget_threshold(
            session_id="test-session-3",
            budget_limit=0.50,
        )

        assert alert is not None
        assert alert.threshold == BudgetThreshold.WARNING_MEDIUM
        assert abs(alert.percentage_used - 0.75) < 0.001

    @pytest.mark.asyncio
    async def test_budget_threshold_90_percent(self, cost_manager):
        """Test budget warning at 90% threshold."""
        cost_manager.set_pricing()

        session = ResearchSession(
            id="test-session-4",
            query_text="test query",
            budget_target=0.50,
            total_cost=0.45,  # 90% of budget
        )
        cost_manager.session_manager.session = session

        alert = await cost_manager.check_budget_threshold(
            session_id="test-session-4",
            budget_limit=0.50,
        )

        assert alert is not None
        assert alert.threshold == BudgetThreshold.WARNING_HIGH

    @pytest.mark.asyncio
    async def test_budget_threshold_critical(self, cost_manager):
        """Test budget alert at critical (100%+) threshold."""
        cost_manager.set_pricing()

        session = ResearchSession(
            id="test-session-5",
            query_text="test query",
            budget_target=0.50,
            total_cost=0.50,  # 100% of budget
        )
        cost_manager.session_manager.session = session

        alert = await cost_manager.check_budget_threshold(
            session_id="test-session-5",
            budget_limit=0.50,
        )

        assert alert is not None
        assert alert.threshold == BudgetThreshold.CRITICAL

    @pytest.mark.asyncio
    async def test_can_perform_operation_within_budget(self, cost_manager):
        """Test checking if operation fits within budget."""
        session = ResearchSession(
            id="test-session-6",
            query_text="test query",
            budget_target=0.50,
            total_cost=0.30,
        )
        cost_manager.session_manager.session = session

        can_perform = await cost_manager.can_perform_operation(
            session_id="test-session-6",
            operation_cost=0.15,
            budget_limit=0.50,
        )

        assert can_perform is True

    @pytest.mark.asyncio
    async def test_can_perform_operation_exceeds_budget(self, cost_manager):
        """Test checking if operation exceeds budget."""
        session = ResearchSession(
            id="test-session-7",
            query_text="test query",
            budget_target=0.50,
            total_cost=0.40,
        )
        cost_manager.session_manager.session = session

        can_perform = await cost_manager.can_perform_operation(
            session_id="test-session-7",
            operation_cost=0.15,
            budget_limit=0.50,
        )

        assert can_perform is False

    def test_clear_session_cache(self, cost_manager):
        """Test clearing session cache."""
        breakdown = CostBreakdown(tavily_cost=0.05, llm_cost=0.01)
        cost_manager._session_costs["test-session"] = breakdown

        cost_manager.clear_session_cache("test-session")

        assert "test-session" not in cost_manager._session_costs


class TestCostIntegration:
    """Integration tests for cost tracking system."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cost_manager(self, temp_dir):
        """Create cost manager with session manager."""
        session_manager = SessionManager(":memory:")
        cost_manager = CostManager(session_manager, cost_history_dir=temp_dir)
        return cost_manager

    @pytest.mark.asyncio
    async def test_multiple_hops_cost_accumulation(self, cost_manager):
        """Test cost accumulation across multiple hops."""
        cost_manager.set_pricing()

        session = ResearchSession(
            id="multi-hop-session",
            query_text="test query",
            budget_target=1.00,
            total_cost=0.0,
        )
        cost_manager.session_manager.session = session

        # Simulate multiple hops
        hops_costs = [
            (1, 2, 1000),  # hop, searches, tokens
            (2, 3, 1200),
            (3, 2, 800),
        ]

        total_expected = 0.0
        for hop_num, searches, tokens in hops_costs:
            breakdown, _ = await cost_manager.track_hop_cost(
                session_id="multi-hop-session",
                hop_number=hop_num,
                tavily_searches=searches,
                llm_tokens=tokens,
            )
            total_expected += breakdown.total_cost

        # Verify total cost accumulation
        cache_breakdown = cost_manager.get_session_cost_breakdown("multi-hop-session")
        assert cache_breakdown is not None
        assert abs(cache_breakdown["total_cost"] - total_expected) < 0.001

    def test_cost_history_directory_creation(self, cost_manager):
        """Test that cost history directory is created."""
        assert cost_manager.cost_history_dir.exists()
        assert cost_manager.cost_history_dir.is_dir()

    @pytest.mark.asyncio
    async def test_export_cost_history_json(self, cost_manager):
        """Test exporting cost history as JSON."""
        session = ResearchSession(
            id="export-test",
            query_text="test query",
            budget_target=0.50,
            total_cost=0.10,
        )
        cost_manager.session_manager.session = session

        export_file = await cost_manager.export_cost_history(format="json")

        assert export_file.exists()
        assert export_file.suffix == ".json"

        # Verify file contains valid JSON
        import json
        with open(export_file) as f:
            data = json.load(f)
            assert isinstance(data, list)
