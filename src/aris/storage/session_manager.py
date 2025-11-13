"""Session management for research operations with database persistence."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_

from aris.storage.models import ResearchSession, ResearchHop, Topic

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages research session persistence and lifecycle.

    Handles:
    - Session creation and initialization
    - Session state tracking and updates
    - Hop management and checkpointing
    - Session statistics and analytics
    - Session recovery and resumption

    Example:
        from aris.storage.database import DatabaseManager
        from aris.storage.session_manager import SessionManager

        db_manager = DatabaseManager(Path("data/aris.db"))
        db_manager.initialize_database()

        with db_manager.session_scope() as db_session:
            manager = SessionManager(db_session)

            # Create session
            research_session = manager.create_session(
                topic_id="topic-123",
                query_text="Latest AI developments",
                query_depth="standard"
            )

            # Update as research progresses
            manager.update_session_status(research_session.id, "searching")

            # Add hop results
            hop = manager.add_hop(
                session_id=research_session.id,
                hop_number=1,
                search_query="AI models 2024",
                sources_found=15,
                confidence_before=0.3,
                confidence_after=0.6,
                cost=0.15
            )

            # Get statistics
            stats = manager.get_session_statistics(research_session.id)
    """

    def __init__(self, db_session: Session):
        """Initialize session manager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.session = db_session
        logger.info("SessionManager initialized")

    def create_session(
        self,
        topic_id: str,
        query_text: str,
        query_depth: str = "standard",
        budget_target: float = 0.50,
        max_hops: int = 5
    ) -> ResearchSession:
        """Create a new research session.

        Args:
            topic_id: Associated topic UUID
            query_text: Research query text
            query_depth: Depth level (quick|standard|deep|exhaustive)
            budget_target: Target cost budget in dollars
            max_hops: Maximum research hops allowed

        Returns:
            Created ResearchSession instance

        Raises:
            ValueError: If topic doesn't exist
        """
        # Verify topic exists
        topic = self.session.get(Topic, topic_id)
        if not topic:
            raise ValueError(f"Topic '{topic_id}' not found")

        research_session = ResearchSession(
            topic_id=topic_id,
            query_text=query_text,
            query_depth=query_depth,
            budget_target=budget_target,
            max_hops=max_hops,
            status="planning",
            current_hop=1,
            total_cost=0.0,
            final_confidence=0.0
        )

        self.session.add(research_session)
        self.session.flush()

        logger.info(
            f"Created research session {research_session.id} "
            f"for query: {query_text[:50]}"
        )

        return research_session

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Get research session by ID.

        Args:
            session_id: Session UUID string

        Returns:
            ResearchSession instance or None if not found
        """
        return self.session.get(ResearchSession, session_id)

    def get_session_with_hops(self, session_id: str) -> Optional[ResearchSession]:
        """Get research session with all hops eagerly loaded.

        Useful for resuming sessions to avoid lazy-loading issues.

        Args:
            session_id: Session UUID string

        Returns:
            ResearchSession instance with hops or None if not found
        """
        result = self.session.execute(
            select(ResearchSession)
            .where(ResearchSession.id == session_id)
        ).scalar_one_or_none()

        if result:
            # Ensure hops are loaded
            _ = len(result.hops)

        return result

    def list_sessions(
        self,
        topic_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ResearchSession]:
        """List research sessions with optional filtering.

        Args:
            topic_id: Optional topic filter
            status: Optional status filter (planning|searching|analyzing|validating|complete|error)
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of ResearchSession instances
        """
        query = select(ResearchSession)

        conditions = []
        if topic_id:
            conditions.append(ResearchSession.topic_id == topic_id)
        if status:
            conditions.append(ResearchSession.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(ResearchSession.started_at)).limit(limit).offset(offset)

        return list(self.session.execute(query).scalars())

    def update_session_status(
        self,
        session_id: str,
        status: str
    ) -> Optional[ResearchSession]:
        """Update research session status.

        Args:
            session_id: Session UUID string
            status: New status (planning|searching|analyzing|validating|complete|error)

        Returns:
            Updated ResearchSession or None if not found
        """
        research_session = self.get_session(session_id)
        if not research_session:
            return None

        research_session.status = status

        # Mark as complete if applicable
        if status in ("complete", "error"):
            research_session.completed_at = datetime.utcnow()

        self.session.flush()

        logger.info(f"Updated session {session_id} status to '{status}'")

        return research_session

    def add_hop(
        self,
        session_id: str,
        hop_number: int,
        search_query: str,
        sources_found_count: int = 0,
        sources_added_count: int = 0,
        confidence_before: float = 0.0,
        confidence_after: float = 0.0,
        cost: float = 0.0,
        llm_calls: int = 0,
        total_tokens: int = 0
    ) -> ResearchHop:
        """Add a research hop to a session.

        Args:
            session_id: Session UUID string
            hop_number: Hop number (sequential)
            search_query: Search query used
            sources_found_count: Number of sources found
            sources_added_count: Number of sources added to database
            confidence_before: Confidence before hop
            confidence_after: Confidence after hop
            cost: Cost of this hop in dollars
            llm_calls: Number of LLM calls
            total_tokens: Total tokens used

        Returns:
            Created ResearchHop instance

        Raises:
            ValueError: If session not found
        """
        research_session = self.get_session(session_id)
        if not research_session:
            raise ValueError(f"Session '{session_id}' not found")

        hop = ResearchHop(
            session_id=session_id,
            hop_number=hop_number,
            search_query=search_query,
            sources_found_count=sources_found_count,
            sources_added_count=sources_added_count,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            cost=cost,
            llm_calls=llm_calls,
            total_tokens=total_tokens
        )

        self.session.add(hop)

        # Update session totals
        research_session.total_cost += cost
        research_session.current_hop = hop_number + 1
        research_session.final_confidence = confidence_after

        self.session.flush()

        logger.info(
            f"Added hop {hop_number} to session {session_id}: "
            f"{sources_found_count} sources, cost=${cost:.2f}"
        )

        return hop

    def get_hop(self, session_id: str, hop_number: int) -> Optional[ResearchHop]:
        """Get specific hop from session.

        Args:
            session_id: Session UUID string
            hop_number: Hop number

        Returns:
            ResearchHop instance or None if not found
        """
        return self.session.execute(
            select(ResearchHop)
            .where(and_(
                ResearchHop.session_id == session_id,
                ResearchHop.hop_number == hop_number
            ))
        ).scalar_one_or_none()

    def get_session_hops(self, session_id: str) -> List[ResearchHop]:
        """Get all hops for a session in order.

        Args:
            session_id: Session UUID string

        Returns:
            List of ResearchHop instances ordered by hop_number
        """
        return list(
            self.session.execute(
                select(ResearchHop)
                .where(ResearchHop.session_id == session_id)
                .order_by(ResearchHop.hop_number)
            ).scalars()
        )

    def delete_session(self, session_id: str) -> bool:
        """Delete research session and all associated hops.

        Args:
            session_id: Session UUID string

        Returns:
            True if deleted, False if not found
        """
        research_session = self.get_session(session_id)
        if not research_session:
            return False

        self.session.delete(research_session)
        self.session.flush()

        logger.info(f"Deleted session {session_id}")

        return True

    def get_session_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive statistics for a research session.

        Args:
            session_id: Session UUID string

        Returns:
            Dictionary with session statistics or None if not found

        Statistics include:
            - Session metadata (id, query, status, created/completed times)
            - Duration and timing information
            - Cost metrics (total, average per hop, budget compliance)
            - Confidence metrics (initial, final, gain, per hop)
            - Source metrics (total found, added per hop)
            - Hop information (count, details per hop)
        """
        research_session = self.get_session_with_hops(session_id)
        if not research_session:
            return None

        # Calculate duration
        duration_seconds = None
        if research_session.completed_at:
            duration_seconds = (
                research_session.completed_at - research_session.started_at
            ).total_seconds()

        # Aggregate hop statistics
        hops = research_session.hops or []
        total_sources = sum(h.sources_found_count for h in hops)
        total_sources_added = sum(h.sources_added_count for h in hops)
        total_llm_calls = sum(h.llm_calls for h in hops)
        total_tokens = sum(h.total_tokens for h in hops)
        average_confidence_gain = (
            sum(h.confidence_after - h.confidence_before for h in hops) / len(hops)
            if hops else 0.0
        )

        stats = {
            "session": {
                "id": str(research_session.id),
                "topic_id": str(research_session.topic_id),
                "query": research_session.query_text,
                "query_depth": research_session.query_depth,
                "status": research_session.status,
                "created_at": research_session.started_at.isoformat(),
                "completed_at": (
                    research_session.completed_at.isoformat()
                    if research_session.completed_at else None
                ),
            },
            "timing": {
                "duration_seconds": duration_seconds,
                "hops_executed": len(hops),
                "max_hops_allowed": research_session.max_hops,
            },
            "cost": {
                "total": round(research_session.total_cost, 4),
                "budget_target": research_session.budget_target,
                "within_budget": research_session.total_cost <= research_session.budget_target,
                "budget_remaining": round(
                    research_session.budget_target - research_session.total_cost, 4
                ),
                "average_per_hop": (
                    round(research_session.total_cost / len(hops), 4)
                    if hops else 0.0
                ),
            },
            "confidence": {
                "initial": hops[0].confidence_before if hops else 0.0,
                "final": research_session.final_confidence,
                "total_gain": research_session.final_confidence - (hops[0].confidence_before if hops else 0.0),
                "average_gain_per_hop": round(average_confidence_gain, 4),
            },
            "sources": {
                "total_found": total_sources,
                "total_added": total_sources_added,
                "average_per_hop": round(total_sources / len(hops), 2) if hops else 0.0,
            },
            "llm": {
                "total_calls": total_llm_calls,
                "total_tokens": total_tokens,
                "average_tokens_per_call": (
                    round(total_tokens / total_llm_calls, 2)
                    if total_llm_calls > 0 else 0.0
                ),
            },
            "hops": [
                {
                    "hop_number": h.hop_number,
                    "query": h.search_query,
                    "sources_found": h.sources_found_count,
                    "sources_added": h.sources_added_count,
                    "confidence_gain": round(h.confidence_after - h.confidence_before, 4),
                    "cost": round(h.cost, 4),
                    "duration_seconds": (
                        (h.completed_at - h.started_at).total_seconds()
                        if h.completed_at else None
                    ),
                }
                for h in hops
            ],
        }

        return stats

    def get_all_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics across all sessions.

        Returns:
            Dictionary with aggregate statistics
        """
        all_sessions = list(
            self.session.execute(select(ResearchSession)).scalars()
        )

        if not all_sessions:
            return {
                "total_sessions": 0,
                "by_status": {},
                "by_depth": {},
                "aggregate_cost": 0.0,
                "aggregate_confidence": 0.0,
            }

        # Group by status and depth
        by_status = {}
        by_depth = {}
        total_cost = 0.0
        total_hops = 0
        completed_sessions = 0

        for sess in all_sessions:
            # By status
            status = sess.status
            if status not in by_status:
                by_status[status] = {"count": 0, "total_cost": 0.0}
            by_status[status]["count"] += 1
            by_status[status]["total_cost"] += sess.total_cost

            # By depth
            depth = sess.query_depth
            if depth not in by_depth:
                by_depth[depth] = {"count": 0, "total_cost": 0.0}
            by_depth[depth]["count"] += 1
            by_depth[depth]["total_cost"] += sess.total_cost

            # Aggregates
            total_cost += sess.total_cost
            total_hops += sess.current_hop - 1  # Subtract the initial counter
            if sess.status == "complete":
                completed_sessions += 1

        return {
            "total_sessions": len(all_sessions),
            "completed_sessions": completed_sessions,
            "by_status": by_status,
            "by_depth": by_depth,
            "aggregate_cost": round(total_cost, 4),
            "average_cost_per_session": round(total_cost / len(all_sessions), 4),
            "total_hops_executed": total_hops,
            "average_hops_per_session": round(total_hops / len(all_sessions), 2),
        }

    def export_session(
        self,
        session_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """Export session data in specified format.

        Args:
            session_id: Session UUID string
            format: Export format (json|csv) - currently supports json

        Returns:
            Exported data as string or None if not found
        """
        stats = self.get_session_statistics(session_id)
        if not stats:
            return None

        if format == "json":
            return json.dumps(stats, indent=2)

        # Add CSV support later if needed
        raise ValueError(f"Export format '{format}' not yet supported")

    def get_active_sessions(self) -> List[ResearchSession]:
        """Get all active (incomplete) research sessions.

        Returns:
            List of active ResearchSession instances
        """
        return self.list_sessions(
            status=None  # We'll filter in Python since we need OR logic
        )  # TODO: Improve with SQLAlchemy or_ when needed

    def get_resumable_sessions(self, topic_id: Optional[str] = None) -> List[ResearchSession]:
        """Get sessions that can be resumed (not completed or errored).

        Args:
            topic_id: Optional topic filter

        Returns:
            List of ResearchSession instances that can be resumed
        """
        resumable_statuses = ["planning", "searching", "analyzing", "validating"]

        query = select(ResearchSession).where(
            ResearchSession.status.in_(resumable_statuses)
        )

        if topic_id:
            query = query.where(ResearchSession.topic_id == topic_id)

        query = query.order_by(desc(ResearchSession.started_at))

        return list(self.session.execute(query).scalars())
