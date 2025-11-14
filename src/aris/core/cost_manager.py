"""Cost tracking and budget management for ARIS research sessions.

This module provides:
- Real-time cost accumulation during research
- Budget threshold warnings (75%, 90%, 100%)
- Cost breakdown by service (Tavily, LLM tokens)
- Monthly/weekly cost reports
- Budget enforcement before operations
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

from aris.storage.session_manager import SessionManager
from aris.storage.models import ResearchSession, ResearchHop


class BudgetThreshold(float, Enum):
    """Budget threshold levels for warnings."""

    CRITICAL = 1.0  # 100% - Hard limit
    WARNING_HIGH = 0.90  # 90% warning
    WARNING_MEDIUM = 0.75  # 75% warning


class CostBreakdownType(str, Enum):
    """Types of costs tracked."""

    TAVILY_SEARCH = "tavily_search"
    LLM_TOKENS = "llm_tokens"
    TOTAL = "total"


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a session or hop."""

    tavily_cost: float = 0.0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    total_cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    budget_limit: Optional[float] = None

    def __post_init__(self):
        """Ensure total is accurate."""
        self.total_cost = self.tavily_cost + self.llm_cost

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "tavily_cost": round(self.tavily_cost, 4),
            "llm_tokens": self.llm_tokens,
            "llm_cost": round(self.llm_cost, 4),
            "total_cost": round(self.total_cost, 4),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BudgetAlert:
    """Budget threshold alert."""

    threshold: BudgetThreshold
    current_cost: float
    budget_limit: float
    percentage_used: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "threshold": self.threshold.name,
            "current_cost": round(self.current_cost, 4),
            "budget_limit": round(self.budget_limit, 4),
            "percentage_used": round(self.percentage_used * 100, 2),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class CostManager:
    """Manages cost tracking and budget enforcement for research operations.

    Provides:
    - Real-time cost tracking per hop and session
    - Budget threshold warnings and enforcement
    - Cost breakdown by service type
    - Cost analytics and reporting
    - Budget history and trends

    Example:
        cost_mgr = CostManager(session_manager)
        await cost_mgr.track_hop_cost(session_id, hop_number, tavily_cost=0.01, llm_cost=0.015)
        warnings = cost_mgr.check_budget_threshold(session_id, budget_limit=0.50)
    """

    # Default pricing for services (per operation/1K tokens)
    TAVILY_COST_PER_SEARCH = 0.01
    LLM_COST_PER_1K_TOKENS = 0.01  # Average across models

    def __init__(self, session_manager: SessionManager, cost_history_dir: Optional[Path] = None):
        """Initialize cost manager.

        Args:
            session_manager: SessionManager instance for database access
            cost_history_dir: Directory to store cost history files (optional)
        """
        self.session_manager = session_manager
        self.cost_history_dir = cost_history_dir or Path(".aris/cost-history")
        self.cost_history_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for current session costs
        self._session_costs: Dict[str, CostBreakdown] = {}
        self._alerts: Dict[str, List[BudgetAlert]] = {}

    def set_pricing(
        self,
        tavily_per_search: float = 0.01,
        llm_per_1k_tokens: float = 0.01,
    ) -> None:
        """Update pricing for cost calculations.

        Args:
            tavily_per_search: Cost per Tavily search operation
            llm_per_1k_tokens: Cost per 1000 LLM tokens
        """
        CostManager.TAVILY_COST_PER_SEARCH = tavily_per_search
        CostManager.LLM_COST_PER_1K_TOKENS = llm_per_1k_tokens

    async def track_hop_cost(
        self,
        session_id: str,
        hop_number: int,
        tavily_searches: int = 0,
        llm_tokens: int = 0,
        tavily_cost_override: Optional[float] = None,
        llm_cost_override: Optional[float] = None,
    ) -> Tuple[CostBreakdown, Optional[BudgetAlert]]:
        """Track cost for a research hop.

        Args:
            session_id: Research session ID
            hop_number: Hop number within session
            tavily_searches: Number of Tavily searches performed
            llm_tokens: Total LLM tokens used
            tavily_cost_override: Override calculated Tavily cost
            llm_cost_override: Override calculated LLM cost

        Returns:
            Tuple of (CostBreakdown, BudgetAlert or None)
        """
        # Calculate costs
        tavily_cost = tavily_cost_override or (tavily_searches * self.TAVILY_COST_PER_SEARCH)
        llm_cost = llm_cost_override or ((llm_tokens / 1000) * self.LLM_COST_PER_1K_TOKENS)

        breakdown = CostBreakdown(
            tavily_cost=tavily_cost,
            llm_tokens=llm_tokens,
            llm_cost=llm_cost,
        )

        # Update database
        hop = await self.session_manager.get_hop(session_id, hop_number)
        if hop:
            hop.cost = breakdown.total_cost
            hop.llm_calls = tavily_searches
            hop.total_tokens = llm_tokens
            await self.session_manager.update_hop(hop)

        # Update session total
        session = await self.session_manager.get_session(session_id)
        if session:
            # Recalculate total from all hops
            total_cost = sum(h.cost for h in session.hops if h.cost) + breakdown.total_cost
            session.total_cost = total_cost
            await self.session_manager.update_session(session)

        # Cache for quick access
        self._session_costs[session_id] = breakdown

        # Check budget threshold
        alert = None
        if session and session.budget_target:
            alert = await self.check_budget_threshold(session_id, session.budget_target)

        return breakdown, alert

    async def check_budget_threshold(
        self, session_id: str, budget_limit: float
    ) -> Optional[BudgetAlert]:
        """Check if session exceeded budget threshold.

        Args:
            session_id: Research session ID
            budget_limit: Budget limit in dollars

        Returns:
            BudgetAlert if threshold exceeded, None otherwise
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            return None

        current_cost = session.total_cost
        percentage_used = current_cost / budget_limit if budget_limit > 0 else 0

        # Determine which threshold was hit
        alert = None
        if percentage_used >= BudgetThreshold.CRITICAL:
            alert = BudgetAlert(
                threshold=BudgetThreshold.CRITICAL,
                current_cost=current_cost,
                budget_limit=budget_limit,
                percentage_used=percentage_used,
                message=f"Budget exhausted: ${current_cost:.4f} / ${budget_limit:.4f}",
            )
        elif percentage_used >= BudgetThreshold.WARNING_HIGH:
            alert = BudgetAlert(
                threshold=BudgetThreshold.WARNING_HIGH,
                current_cost=current_cost,
                budget_limit=budget_limit,
                percentage_used=percentage_used,
                message=f"Budget warning (90%): ${current_cost:.4f} / ${budget_limit:.4f}",
            )
        elif percentage_used >= BudgetThreshold.WARNING_MEDIUM:
            alert = BudgetAlert(
                threshold=BudgetThreshold.WARNING_MEDIUM,
                current_cost=current_cost,
                budget_limit=budget_limit,
                percentage_used=percentage_used,
                message=f"Budget caution (75%): ${current_cost:.4f} / ${budget_limit:.4f}",
            )

        # Store alert
        if alert:
            if session_id not in self._alerts:
                self._alerts[session_id] = []
            self._alerts[session_id].append(alert)
            session.budget_warnings_issued.append(alert.message)
            await self.session_manager.update_session(session)

        return alert

    async def can_perform_operation(
        self,
        session_id: str,
        operation_cost: float,
        budget_limit: Optional[float],
    ) -> bool:
        """Check if operation can be performed within budget.

        Args:
            session_id: Research session ID
            operation_cost: Estimated cost of operation
            budget_limit: Budget limit in dollars (None = no limit)

        Returns:
            True if operation fits within budget, False otherwise
        """
        # No budget limit set - allow operation
        if budget_limit is None:
            return True

        session = await self.session_manager.get_session(session_id)
        if not session:
            return True  # No session, allow operation

        projected_cost = session.total_cost + operation_cost
        return projected_cost <= budget_limit

    def get_session_cost_breakdown(self, session_id: str) -> Optional[Dict]:
        """Get cost breakdown for a session.

        Args:
            session_id: Research session ID

        Returns:
            Dictionary with cost breakdown or None
        """
        if session_id in self._session_costs:
            return self._session_costs[session_id].to_dict()
        return None

    async def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get cost summary for a session.

        Args:
            session_id: Research session ID

        Returns:
            Dictionary with session cost summary or None
        """
        session = await self.session_manager.get_session(session_id)
        if not session:
            return None

        tavily_total = sum(h.llm_calls * self.TAVILY_COST_PER_SEARCH for h in session.hops)
        llm_total = sum(h.total_tokens for h in session.hops)
        llm_cost_total = (llm_total / 1000) * self.LLM_COST_PER_1K_TOKENS

        return {
            "session_id": session_id,
            "status": session.status,
            "hops_completed": len([h for h in session.hops if h.completed_at]),
            "total_hops": session.max_hops,
            "tavily_cost": round(tavily_total, 4),
            "llm_tokens": llm_total,
            "llm_cost": round(llm_cost_total, 4),
            "total_cost": round(session.total_cost, 4),
            "budget_target": session.budget_target,
            "budget_used_percentage": round((session.total_cost / session.budget_target * 100) if session.budget_target else 0, 2),
            "within_budget": session.total_cost <= session.budget_target,
            "warnings_issued": len(session.budget_warnings_issued),
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }

    async def get_all_sessions_cost_summary(self) -> List[Dict]:
        """Get cost summary for all sessions.

        Returns:
            List of session cost summaries
        """
        sessions = await self.session_manager.list_sessions()
        summaries = []

        for session in sessions:
            summary = await self.get_session_summary(session.id)
            if summary:
                summaries.append(summary)

        return summaries

    async def get_cost_history(
        self,
        days: int = 30,
        topic_id: Optional[str] = None,
    ) -> Dict:
        """Get cost history for a time period.

        Args:
            days: Number of days to look back
            topic_id: Optional filter by topic ID

        Returns:
            Dictionary with cost history metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        sessions = await self.session_manager.list_sessions()

        # Filter by date and topic
        relevant_sessions = [
            s for s in sessions
            if s.started_at >= cutoff_date and (not topic_id or s.topic_id == topic_id)
        ]

        total_cost = sum(s.total_cost for s in relevant_sessions)
        total_sessions = len(relevant_sessions)
        avg_cost = total_cost / total_sessions if total_sessions > 0 else 0

        # Group by day
        daily_costs = {}
        for session in relevant_sessions:
            day = session.started_at.date()
            day_key = str(day)
            if day_key not in daily_costs:
                daily_costs[day_key] = {
                    "sessions": 0,
                    "total_cost": 0.0,
                    "hops": 0,
                }
            daily_costs[day_key]["sessions"] += 1
            daily_costs[day_key]["total_cost"] += session.total_cost
            daily_costs[day_key]["hops"] += len(session.hops)

        return {
            "period_days": days,
            "period_start": cutoff_date.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "total_sessions": total_sessions,
            "total_cost": round(total_cost, 4),
            "average_cost_per_session": round(avg_cost, 4),
            "daily_costs": {k: {"sessions": v["sessions"], "total_cost": round(v["total_cost"], 4), "hops": v["hops"]} for k, v in daily_costs.items()},
        }

    async def save_cost_report(self, session_id: str) -> Path:
        """Save detailed cost report to file.

        Args:
            session_id: Research session ID

        Returns:
            Path to saved report file
        """
        summary = await self.get_session_summary(session_id)
        if not summary:
            raise ValueError(f"Session {session_id} not found")

        report_file = self.cost_history_dir / f"cost-report-{session_id}.json"
        report_file.write_text(json.dumps(summary, indent=2))

        return report_file

    async def export_cost_history(self, format: str = "json") -> Path:
        """Export complete cost history.

        Args:
            format: Export format (json or csv)

        Returns:
            Path to exported file
        """
        summaries = await self.get_all_sessions_cost_summary()

        if format == "json":
            export_file = self.cost_history_dir / f"cost-history-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
            export_file.write_text(json.dumps(summaries, indent=2))
        elif format == "csv":
            import csv

            export_file = self.cost_history_dir / f"cost-history-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
            with open(export_file, "w", newline="") as f:
                if summaries:
                    writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
                    writer.writeheader()
                    writer.writerows(summaries)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return export_file

    def clear_session_cache(self, session_id: str) -> None:
        """Clear in-memory cache for a session.

        Args:
            session_id: Research session ID
        """
        self._session_costs.pop(session_id, None)
        self._alerts.pop(session_id, None)
