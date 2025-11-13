"""Unit tests for SessionManager."""

import pytest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from aris.storage.models import Topic, ResearchSession, ResearchHop
from aris.storage.database import DatabaseManager
from aris.storage.session_manager import SessionManager


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseManager:
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)
    manager.create_all_tables()
    return manager


@pytest.fixture
def session_manager(temp_db: DatabaseManager) -> SessionManager:
    """Create SessionManager with test database."""
    db_session = temp_db.get_session()
    return SessionManager(db_session)


@pytest.fixture
def test_topic(session_manager: SessionManager) -> Topic:
    """Create a test topic."""
    topic = Topic(id=str(uuid4()), name="Test Topic", description="A test topic")
    session_manager.session.add(topic)
    session_manager.session.commit()
    return topic


class TestSessionCreation:
    """Test session creation functionality."""

    def test_create_session_success(self, session_manager: SessionManager, test_topic: Topic):
        """Test successful session creation."""
        query_text = "What is quantum computing?"
        query_depth = "standard"

        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text=query_text,
            query_depth=query_depth
        )

        assert session is not None
        assert session.query_text == query_text
        assert session.query_depth == query_depth
        assert session.status == "planning"
        assert session.total_cost == 0.0
        assert session.current_hop == 1

    def test_create_session_with_custom_budget(self, session_manager: SessionManager, test_topic: Topic):
        """Test session creation with custom budget."""
        budget_target = 2.50

        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query",
            budget_target=budget_target
        )

        assert session.budget_target == budget_target

    def test_create_session_invalid_topic(self, session_manager: SessionManager):
        """Test session creation with invalid topic raises error."""
        with pytest.raises(ValueError, match="Topic .* not found"):
            session_manager.create_session(
                topic_id="invalid-topic-id",
                query_text="Test query"
            )

    def test_create_session_custom_max_hops(self, session_manager: SessionManager, test_topic: Topic):
        """Test session creation with custom max hops."""
        max_hops = 10

        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query",
            max_hops=max_hops
        )

        assert session.max_hops == max_hops


class TestSessionRetrieval:
    """Test session retrieval functionality."""

    def test_get_session_by_id(self, session_manager: SessionManager, test_topic: Topic):
        """Test retrieving session by ID."""
        created_session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        retrieved_session = session_manager.get_session(created_session.id)

        assert retrieved_session is not None
        assert retrieved_session.id == created_session.id
        assert retrieved_session.query_text == created_session.query_text

    def test_get_session_not_found(self, session_manager: SessionManager):
        """Test retrieving non-existent session returns None."""
        session = session_manager.get_session("non-existent-id")
        assert session is None

    def test_get_session_with_hops(self, session_manager: SessionManager, test_topic: Topic):
        """Test retrieving session with hops eagerly loaded."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        # Add some hops
        session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search 1",
            sources_found_count=5
        )

        retrieved = session_manager.get_session_with_hops(session.id)

        assert retrieved is not None
        assert len(retrieved.hops) == 1
        assert retrieved.hops[0].hop_number == 1

    def test_list_sessions_empty(self, session_manager: SessionManager):
        """Test listing sessions when none exist."""
        sessions = session_manager.list_sessions()
        assert sessions == []

    def test_list_sessions_multiple(self, session_manager: SessionManager, test_topic: Topic):
        """Test listing multiple sessions."""
        # Create multiple sessions
        for i in range(3):
            session_manager.create_session(
                topic_id=test_topic.id,
                query_text=f"Query {i}"
            )

        sessions = session_manager.list_sessions()

        assert len(sessions) == 3

    def test_list_sessions_with_status_filter(self, session_manager: SessionManager, test_topic: Topic):
        """Test listing sessions filtered by status."""
        session1 = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Query 1"
        )
        session2 = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Query 2"
        )

        # Complete one session
        session_manager.update_session_status(session1.id, "complete")

        # List only complete sessions
        sessions = session_manager.list_sessions(status="complete")

        assert len(sessions) == 1
        assert sessions[0].id == session1.id

    def test_list_sessions_with_limit(self, session_manager: SessionManager, test_topic: Topic):
        """Test listing sessions with limit."""
        # Create 10 sessions
        for i in range(10):
            session_manager.create_session(
                topic_id=test_topic.id,
                query_text=f"Query {i}"
            )

        sessions = session_manager.list_sessions(limit=5)

        assert len(sessions) == 5


class TestSessionStatus:
    """Test session status management."""

    def test_update_status_planning_to_searching(self, session_manager: SessionManager, test_topic: Topic):
        """Test updating session status."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        updated = session_manager.update_session_status(session.id, "searching")

        assert updated is not None
        assert updated.status == "searching"

    def test_update_status_to_complete(self, session_manager: SessionManager, test_topic: Topic):
        """Test updating status to complete sets completion time."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        before_update = datetime.utcnow()
        updated = session_manager.update_session_status(session.id, "complete")
        after_update = datetime.utcnow()

        assert updated is not None
        assert updated.status == "complete"
        assert updated.completed_at is not None
        assert before_update <= updated.completed_at <= after_update

    def test_update_status_non_existent(self, session_manager: SessionManager):
        """Test updating non-existent session returns None."""
        result = session_manager.update_session_status("non-existent-id", "complete")
        assert result is None


class TestHopManagement:
    """Test research hop management."""

    def test_add_hop(self, session_manager: SessionManager, test_topic: Topic):
        """Test adding a hop to a session."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        hop = session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search term 1",
            sources_found_count=10,
            sources_added_count=5,
            confidence_before=0.3,
            confidence_after=0.6,
            cost=0.15,
            llm_calls=2,
            total_tokens=1000
        )

        assert hop is not None
        assert hop.hop_number == 1
        assert hop.sources_found_count == 10
        assert hop.cost == 0.15

        # Verify session was updated
        updated_session = session_manager.get_session(session.id)
        assert updated_session.total_cost == 0.15
        assert updated_session.current_hop == 2
        assert updated_session.final_confidence == 0.6

    def test_add_multiple_hops(self, session_manager: SessionManager, test_topic: Topic):
        """Test adding multiple hops to a session."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        # Add first hop
        session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search 1",
            confidence_before=0.3,
            confidence_after=0.5,
            cost=0.10
        )

        # Add second hop
        session_manager.add_hop(
            session_id=session.id,
            hop_number=2,
            search_query="Search 2",
            confidence_before=0.5,
            confidence_after=0.8,
            cost=0.20
        )

        # Verify totals
        updated_session = session_manager.get_session(session.id)
        assert updated_session.total_cost == 0.30
        assert updated_session.current_hop == 3
        assert updated_session.final_confidence == 0.8

    def test_add_hop_invalid_session(self, session_manager: SessionManager):
        """Test adding hop to non-existent session raises error."""
        with pytest.raises(ValueError, match="Session .* not found"):
            session_manager.add_hop(
                session_id="invalid-session-id",
                hop_number=1,
                search_query="Test"
            )

    def test_get_hop(self, session_manager: SessionManager, test_topic: Topic):
        """Test retrieving specific hop."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        added_hop = session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search term"
        )

        retrieved = session_manager.get_hop(session.id, 1)

        assert retrieved is not None
        assert retrieved.id == added_hop.id
        assert retrieved.search_query == "Search term"

    def test_get_session_hops(self, session_manager: SessionManager, test_topic: Topic):
        """Test retrieving all hops for a session."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        # Add multiple hops
        for i in range(3):
            session_manager.add_hop(
                session_id=session.id,
                hop_number=i + 1,
                search_query=f"Search {i + 1}"
            )

        hops = session_manager.get_session_hops(session.id)

        assert len(hops) == 3
        assert hops[0].hop_number == 1
        assert hops[2].hop_number == 3


class TestSessionStatistics:
    """Test session statistics functionality."""

    def test_get_session_statistics(self, session_manager: SessionManager, test_topic: Topic):
        """Test getting comprehensive session statistics."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query",
            query_depth="standard"
        )

        # Add hop
        session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search 1",
            sources_found_count=10,
            sources_added_count=5,
            confidence_before=0.3,
            confidence_after=0.6,
            cost=0.15,
            llm_calls=2,
            total_tokens=1500
        )

        stats = session_manager.get_session_statistics(session.id)

        assert stats is not None
        assert stats["session"]["query"] == "Test query"
        assert stats["cost"]["total"] == 0.15
        assert stats["confidence"]["final"] == 0.6
        assert stats["sources"]["total_found"] == 10
        assert len(stats["hops"]) == 1

    def test_session_statistics_not_found(self, session_manager: SessionManager):
        """Test getting statistics for non-existent session."""
        stats = session_manager.get_session_statistics("non-existent-id")
        assert stats is None

    def test_all_statistics(self, session_manager: SessionManager, test_topic: Topic):
        """Test getting aggregate statistics."""
        # Create multiple sessions with different statuses
        session1 = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Query 1"
        )
        session_manager.add_hop(
            session_id=session1.id,
            hop_number=1,
            search_query="Search 1",
            cost=0.10
        )
        session_manager.update_session_status(session1.id, "complete")

        session2 = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Query 2"
        )
        session_manager.add_hop(
            session_id=session2.id,
            hop_number=1,
            search_query="Search 2",
            cost=0.20
        )

        stats = session_manager.get_all_statistics()

        assert stats["total_sessions"] == 2
        assert stats["completed_sessions"] == 1
        assert stats["aggregate_cost"] == 0.30
        assert "by_status" in stats
        assert "by_depth" in stats


class TestSessionDeletion:
    """Test session deletion functionality."""

    def test_delete_session(self, session_manager: SessionManager, test_topic: Topic):
        """Test deleting a session."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        deleted = session_manager.delete_session(session.id)

        assert deleted is True

        # Verify session is deleted
        retrieved = session_manager.get_session(session.id)
        assert retrieved is None

    def test_delete_session_not_found(self, session_manager: SessionManager):
        """Test deleting non-existent session."""
        deleted = session_manager.delete_session("non-existent-id")
        assert deleted is False

    def test_delete_session_with_hops(self, session_manager: SessionManager, test_topic: Topic):
        """Test deleting session also deletes hops (cascading)."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        hop = session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search 1"
        )

        # Delete session
        session_manager.delete_session(session.id)

        # Verify hop is also deleted
        retrieved_hop = session_manager.get_hop(session.id, 1)
        assert retrieved_hop is None


class TestSessionExport:
    """Test session export functionality."""

    def test_export_session_json(self, session_manager: SessionManager, test_topic: Topic):
        """Test exporting session as JSON."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        session_manager.add_hop(
            session_id=session.id,
            hop_number=1,
            search_query="Search 1",
            cost=0.15
        )

        exported = session_manager.export_session(session.id, format="json")

        assert exported is not None
        assert "session" in exported
        assert "hops" in exported
        assert '"query": "Test query"' in exported

    def test_export_session_not_found(self, session_manager: SessionManager):
        """Test exporting non-existent session."""
        exported = session_manager.export_session("non-existent-id", format="json")
        assert exported is None

    def test_export_session_invalid_format(self, session_manager: SessionManager, test_topic: Topic):
        """Test exporting with invalid format raises error."""
        session = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Test query"
        )

        with pytest.raises(ValueError, match="Export format .* not yet supported"):
            session_manager.export_session(session.id, format="csv")


class TestSessionQueries:
    """Test session query functionality."""

    def test_get_resumable_sessions(self, session_manager: SessionManager, test_topic: Topic):
        """Test getting resumable sessions (not complete or error)."""
        session1 = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Query 1"
        )

        session2 = session_manager.create_session(
            topic_id=test_topic.id,
            query_text="Query 2"
        )
        session_manager.update_session_status(session2.id, "complete")

        resumable = session_manager.get_resumable_sessions()

        assert len(resumable) == 1
        assert resumable[0].id == session1.id

    def test_get_resumable_sessions_by_topic(self, session_manager: SessionManager):
        """Test getting resumable sessions filtered by topic."""
        topic1 = Topic(id=str(uuid4()), name="Topic 1")
        topic2 = Topic(id=str(uuid4()), name="Topic 2")
        session_manager.session.add(topic1)
        session_manager.session.add(topic2)
        session_manager.session.commit()

        session1 = session_manager.create_session(
            topic_id=topic1.id,
            query_text="Query 1"
        )

        session2 = session_manager.create_session(
            topic_id=topic2.id,
            query_text="Query 2"
        )

        resumable = session_manager.get_resumable_sessions(topic_id=topic1.id)

        assert len(resumable) == 1
        assert resumable[0].id == session1.id
