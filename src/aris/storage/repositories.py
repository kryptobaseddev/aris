"""Repository pattern for database operations."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session, joinedload

from aris.storage.models import (
    Topic,
    Document,
    Source,
    Relationship,
    ResearchSession,
    ResearchHop,
    Conflict,
)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, session: Session):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session instance
        """
        self.session = session


class TopicRepository(BaseRepository):
    """Repository for Topic operations."""

    def create(self, name: str, description: Optional[str] = None) -> Topic:
        """Create a new topic.

        Args:
            name: Topic name (must be unique)
            description: Optional topic description

        Returns:
            Created Topic instance
        """
        topic = Topic(name=name, description=description)
        self.session.add(topic)
        self.session.flush()
        return topic

    def get_by_id(self, topic_id: str) -> Optional[Topic]:
        """Get topic by ID.

        Args:
            topic_id: Topic UUID string

        Returns:
            Topic instance or None if not found
        """
        return self.session.get(Topic, topic_id)

    def get_by_name(self, name: str) -> Optional[Topic]:
        """Get topic by name.

        Args:
            name: Topic name

        Returns:
            Topic instance or None if not found
        """
        return self.session.execute(
            select(Topic).where(Topic.name == name)
        ).scalar_one_or_none()

    def get_or_create(self, name: str, description: Optional[str] = None) -> Topic:
        """Get existing topic or create new one.

        Args:
            name: Topic name
            description: Optional topic description

        Returns:
            Topic instance (existing or newly created)
        """
        topic = self.get_by_name(name)
        if topic:
            return topic
        return self.create(name, description)

    def get_all(self, status: Optional[str] = None) -> List[Topic]:
        """Get all topics, optionally filtered by status.

        Args:
            status: Optional status filter (active | archived | completed)

        Returns:
            List of Topic instances
        """
        query = select(Topic)
        if status:
            query = query.where(Topic.status == status)
        query = query.order_by(Topic.name)
        return list(self.session.execute(query).scalars())

    def update_status(self, topic_id: str, status: str) -> Optional[Topic]:
        """Update topic status.

        Args:
            topic_id: Topic UUID string
            status: New status (active | archived | completed)

        Returns:
            Updated Topic instance or None if not found
        """
        topic = self.get_by_id(topic_id)
        if topic:
            topic.status = status
            topic.updated_at = datetime.utcnow()
            self.session.flush()
        return topic

    def delete(self, topic_id: str) -> bool:
        """Delete topic and all related documents.

        Args:
            topic_id: Topic UUID string

        Returns:
            True if deleted, False if not found
        """
        topic = self.get_by_id(topic_id)
        if topic:
            self.session.delete(topic)
            self.session.flush()
            return True
        return False


class DocumentRepository(BaseRepository):
    """Repository for Document operations."""

    def create(
        self,
        topic_id: str,
        title: str,
        file_path: str,
        word_count: int = 0,
        confidence: float = 0.0,
        embedding_id: Optional[str] = None
    ) -> Document:
        """Create a new document.

        Args:
            topic_id: Parent topic UUID
            title: Document title
            file_path: Path to document file
            word_count: Number of words in document
            confidence: Research confidence score (0.0-1.0)
            embedding_id: Optional vector embedding reference

        Returns:
            Created Document instance
        """
        doc = Document(
            topic_id=topic_id,
            title=title,
            file_path=file_path,
            word_count=word_count,
            confidence=confidence,
            embedding_id=embedding_id
        )
        self.session.add(doc)
        self.session.flush()
        return doc

    def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID with related data.

        Args:
            doc_id: Document UUID string

        Returns:
            Document instance with loaded relationships or None
        """
        return self.session.execute(
            select(Document)
            .options(joinedload(Document.topic))
            .options(joinedload(Document.sources))
            .where(Document.id == doc_id)
        ).scalar_one_or_none()

    def get_by_file_path(self, file_path: str) -> Optional[Document]:
        """Get document by file path.

        Args:
            file_path: Document file path

        Returns:
            Document instance or None if not found
        """
        return self.session.execute(
            select(Document).where(Document.file_path == file_path)
        ).scalar_one_or_none()

    def find_by_topic(
        self,
        topic_id: str,
        status: Optional[str] = None
    ) -> List[Document]:
        """Find documents by topic.

        Args:
            topic_id: Topic UUID string
            status: Optional status filter (draft | review | published | archived)

        Returns:
            List of Document instances
        """
        query = select(Document).where(Document.topic_id == topic_id)
        if status:
            query = query.where(Document.status == status)
        query = query.order_by(Document.updated_at.desc())
        return list(self.session.execute(query).scalars())

    def search_by_title(self, search_term: str) -> List[Document]:
        """Search documents by title (case-insensitive).

        Args:
            search_term: Search string

        Returns:
            List of matching Document instances
        """
        return list(
            self.session.execute(
                select(Document)
                .where(Document.title.ilike(f"%{search_term}%"))
                .order_by(Document.updated_at.desc())
            ).scalars()
        )

    def update_metadata(
        self,
        doc_id: str,
        title: Optional[str] = None,
        word_count: Optional[int] = None,
        status: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> Optional[Document]:
        """Update document metadata.

        Args:
            doc_id: Document UUID string
            title: New title (optional)
            word_count: New word count (optional)
            status: New status (optional)
            confidence: New confidence score (optional)

        Returns:
            Updated Document instance or None if not found
        """
        doc = self.get_by_id(doc_id)
        if doc:
            if title is not None:
                doc.title = title
            if word_count is not None:
                doc.word_count = word_count
            if status is not None:
                doc.status = status
            if confidence is not None:
                doc.confidence = confidence
            doc.updated_at = datetime.utcnow()
            self.session.flush()
        return doc

    def mark_researched(self, doc_id: str) -> Optional[Document]:
        """Mark document as recently researched.

        Args:
            doc_id: Document UUID string

        Returns:
            Updated Document instance or None if not found
        """
        doc = self.get_by_id(doc_id)
        if doc:
            doc.last_research_at = datetime.utcnow()
            self.session.flush()
        return doc

    def delete(self, doc_id: str) -> bool:
        """Delete document and all related data.

        Args:
            doc_id: Document UUID string

        Returns:
            True if deleted, False if not found
        """
        doc = self.get_by_id(doc_id)
        if doc:
            self.session.delete(doc)
            self.session.flush()
            return True
        return False


class SourceRepository(BaseRepository):
    """Repository for Source operations."""

    def create(
        self,
        url: str,
        title: str,
        source_type: str = "other",
        tier: int = 3,
        credibility_score: float = 0.6,
        summary: Optional[str] = None
    ) -> Source:
        """Create a new source.

        Args:
            url: Source URL (must be unique)
            title: Source title
            source_type: Type of source (academic | news | blog | documentation | other)
            tier: Credibility tier (1-4, 1 highest)
            credibility_score: Credibility score (0.0-1.0)
            summary: Optional content summary

        Returns:
            Created Source instance
        """
        source = Source(
            url=url,
            title=title,
            source_type=source_type,
            tier=tier,
            credibility_score=credibility_score,
            summary=summary
        )
        self.session.add(source)
        self.session.flush()
        return source

    def get_by_id(self, source_id: str) -> Optional[Source]:
        """Get source by ID.

        Args:
            source_id: Source UUID string

        Returns:
            Source instance or None if not found
        """
        return self.session.get(Source, source_id)

    def get_by_url(self, url: str) -> Optional[Source]:
        """Get source by URL.

        Args:
            url: Source URL

        Returns:
            Source instance or None if not found
        """
        return self.session.execute(
            select(Source).where(Source.url == url)
        ).scalar_one_or_none()

    def get_or_create(
        self,
        url: str,
        title: str,
        source_type: str = "other",
        tier: int = 3,
        credibility_score: float = 0.6,
        summary: Optional[str] = None
    ) -> Source:
        """Get existing source or create new one.

        Args:
            url: Source URL
            title: Source title
            source_type: Type of source
            tier: Credibility tier (1-4)
            credibility_score: Credibility score (0.0-1.0)
            summary: Optional content summary

        Returns:
            Source instance (existing or newly created)
        """
        source = self.get_by_url(url)
        if source:
            return source
        return self.create(url, title, source_type, tier, credibility_score, summary)

    def find_by_tier(self, min_tier: int = 1, max_tier: int = 4) -> List[Source]:
        """Find sources by credibility tier range.

        Args:
            min_tier: Minimum tier (inclusive, 1 = highest)
            max_tier: Maximum tier (inclusive, 4 = lowest)

        Returns:
            List of Source instances
        """
        return list(
            self.session.execute(
                select(Source)
                .where(and_(Source.tier >= min_tier, Source.tier <= max_tier))
                .order_by(Source.tier, Source.credibility_score.desc())
            ).scalars()
        )

    def update_credibility(
        self,
        source_id: str,
        credibility_score: float,
        verification_status: Optional[str] = None
    ) -> Optional[Source]:
        """Update source credibility metrics.

        Args:
            source_id: Source UUID string
            credibility_score: New credibility score (0.0-1.0)
            verification_status: New verification status (optional)

        Returns:
            Updated Source instance or None if not found
        """
        source = self.get_by_id(source_id)
        if source:
            source.credibility_score = credibility_score
            if verification_status:
                source.verification_status = verification_status
            source.updated_at = datetime.utcnow()
            self.session.flush()
        return source


class RelationshipRepository(BaseRepository):
    """Repository for Document Relationship operations."""

    def create(
        self,
        source_doc_id: str,
        target_doc_id: str,
        relationship_type: str,
        strength: float = 0.5,
        evidence: Optional[str] = None
    ) -> Relationship:
        """Create a document relationship.

        Args:
            source_doc_id: Source document UUID
            target_doc_id: Target document UUID
            relationship_type: Type (contradicts | supports | extends | cites | related)
            strength: Relationship strength (0.0-1.0)
            evidence: Optional supporting evidence

        Returns:
            Created Relationship instance
        """
        rel = Relationship(
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            relationship_type=relationship_type,
            strength=strength,
            evidence=evidence
        )
        self.session.add(rel)
        self.session.flush()
        return rel

    def get_by_id(self, relationship_id: str) -> Optional[Relationship]:
        """Get relationship by ID.

        Args:
            relationship_id: Relationship UUID string

        Returns:
            Relationship instance or None if not found
        """
        return self.session.get(Relationship, relationship_id)

    def find_by_document(
        self,
        doc_id: str,
        direction: str = "both"
    ) -> List[Relationship]:
        """Find relationships involving a document.

        Args:
            doc_id: Document UUID string
            direction: Filter by direction (outgoing | incoming | both)

        Returns:
            List of Relationship instances
        """
        if direction == "outgoing":
            query = select(Relationship).where(Relationship.source_doc_id == doc_id)
        elif direction == "incoming":
            query = select(Relationship).where(Relationship.target_doc_id == doc_id)
        else:  # both
            query = select(Relationship).where(
                or_(
                    Relationship.source_doc_id == doc_id,
                    Relationship.target_doc_id == doc_id
                )
            )
        return list(self.session.execute(query).scalars())

    def find_by_type(
        self,
        relationship_type: str,
        min_strength: float = 0.0
    ) -> List[Relationship]:
        """Find relationships by type and minimum strength.

        Args:
            relationship_type: Relationship type to filter
            min_strength: Minimum relationship strength

        Returns:
            List of Relationship instances
        """
        return list(
            self.session.execute(
                select(Relationship)
                .where(
                    and_(
                        Relationship.relationship_type == relationship_type,
                        Relationship.strength >= min_strength
                    )
                )
                .order_by(Relationship.strength.desc())
            ).scalars()
        )


class ResearchSessionRepository(BaseRepository):
    """Repository for ResearchSession operations."""

    def create(
        self,
        topic_id: str,
        query_text: str,
        query_depth: str = "standard",
        max_hops: int = 5,
        budget_target: float = 0.50
    ) -> ResearchSession:
        """Create a new research session.

        Args:
            topic_id: Topic UUID
            query_text: Research query
            query_depth: Depth level (quick | standard | deep | exhaustive)
            max_hops: Maximum search iterations
            budget_target: Budget limit in dollars

        Returns:
            Created ResearchSession instance
        """
        session = ResearchSession(
            topic_id=topic_id,
            query_text=query_text,
            query_depth=query_depth,
            max_hops=max_hops,
            budget_target=budget_target
        )
        self.session.add(session)
        self.session.flush()
        return session

    def get_by_id(self, session_id: str) -> Optional[ResearchSession]:
        """Get research session by ID with related hops.

        Args:
            session_id: Session UUID string

        Returns:
            ResearchSession instance with loaded hops or None
        """
        return self.session.execute(
            select(ResearchSession)
            .options(joinedload(ResearchSession.hops))
            .where(ResearchSession.id == session_id)
        ).scalar_one_or_none()

    def find_by_topic(
        self,
        topic_id: str,
        status: Optional[str] = None
    ) -> List[ResearchSession]:
        """Find research sessions by topic.

        Args:
            topic_id: Topic UUID string
            status: Optional status filter

        Returns:
            List of ResearchSession instances
        """
        query = select(ResearchSession).where(ResearchSession.topic_id == topic_id)
        if status:
            query = query.where(ResearchSession.status == status)
        query = query.order_by(ResearchSession.started_at.desc())
        return list(self.session.execute(query).scalars())

    def update_status(
        self,
        session_id: str,
        status: str,
        completed: bool = False
    ) -> Optional[ResearchSession]:
        """Update research session status.

        Args:
            session_id: Session UUID string
            status: New status
            completed: Whether session is completed

        Returns:
            Updated ResearchSession instance or None if not found
        """
        session = self.get_by_id(session_id)
        if session:
            session.status = status
            if completed and not session.completed_at:
                session.completed_at = datetime.utcnow()
            self.session.flush()
        return session

    def add_cost(self, session_id: str, cost: float) -> Optional[ResearchSession]:
        """Add cost to research session total.

        Args:
            session_id: Session UUID string
            cost: Cost to add

        Returns:
            Updated ResearchSession instance or None if not found
        """
        session = self.get_by_id(session_id)
        if session:
            session.total_cost += cost
            self.session.flush()
        return session


class ResearchHopRepository(BaseRepository):
    """Repository for ResearchHop operations."""

    def create(
        self,
        session_id: str,
        hop_number: int,
        search_query: str,
        search_strategy: Optional[str] = None
    ) -> ResearchHop:
        """Create a new research hop.

        Args:
            session_id: Parent session UUID
            hop_number: Hop sequence number
            search_query: Search query text
            search_strategy: Strategy used (broad | targeted | verification)

        Returns:
            Created ResearchHop instance
        """
        hop = ResearchHop(
            session_id=session_id,
            hop_number=hop_number,
            search_query=search_query,
            search_strategy=search_strategy
        )
        self.session.add(hop)
        self.session.flush()
        return hop

    def get_by_id(self, hop_id: str) -> Optional[ResearchHop]:
        """Get research hop by ID.

        Args:
            hop_id: Hop UUID string

        Returns:
            ResearchHop instance or None if not found
        """
        return self.session.get(ResearchHop, hop_id)

    def find_by_session(self, session_id: str) -> List[ResearchHop]:
        """Find all hops for a research session.

        Args:
            session_id: Session UUID string

        Returns:
            List of ResearchHop instances ordered by hop number
        """
        return list(
            self.session.execute(
                select(ResearchHop)
                .where(ResearchHop.session_id == session_id)
                .order_by(ResearchHop.hop_number)
            ).scalars()
        )

    def update_results(
        self,
        hop_id: str,
        sources_found_count: int,
        sources_added_count: int,
        confidence_after: float,
        llm_calls: int = 0,
        total_tokens: int = 0,
        cost: float = 0.0
    ) -> Optional[ResearchHop]:
        """Update hop results and metrics.

        Args:
            hop_id: Hop UUID string
            sources_found_count: Number of sources found
            sources_added_count: Number of sources added
            confidence_after: Confidence score after hop
            llm_calls: Number of LLM API calls
            total_tokens: Total tokens used
            cost: Cost of hop

        Returns:
            Updated ResearchHop instance or None if not found
        """
        hop = self.get_by_id(hop_id)
        if hop:
            hop.sources_found_count = sources_found_count
            hop.sources_added_count = sources_added_count
            hop.confidence_after = confidence_after
            hop.llm_calls = llm_calls
            hop.total_tokens = total_tokens
            hop.cost = cost
            hop.completed_at = datetime.utcnow()
            self.session.flush()
        return hop


class ConflictRepository(BaseRepository):
    """Repository for Conflict operations."""

    def create(
        self,
        document_id: str,
        conflict_type: str,
        description: str,
        severity: str = "low",
        source_ids: Optional[str] = None
    ) -> Conflict:
        """Create a new conflict.

        Args:
            document_id: Document UUID
            conflict_type: Type (contradiction | ambiguity | outdated)
            description: Conflict description
            severity: Severity level (low | medium | high | critical)
            source_ids: JSON array of involved source IDs

        Returns:
            Created Conflict instance
        """
        conflict = Conflict(
            document_id=document_id,
            conflict_type=conflict_type,
            description=description,
            severity=severity,
            source_ids=source_ids
        )
        self.session.add(conflict)
        self.session.flush()
        return conflict

    def get_by_id(self, conflict_id: str) -> Optional[Conflict]:
        """Get conflict by ID.

        Args:
            conflict_id: Conflict UUID string

        Returns:
            Conflict instance or None if not found
        """
        return self.session.get(Conflict, conflict_id)

    def find_by_document(
        self,
        document_id: str,
        status: Optional[str] = None
    ) -> List[Conflict]:
        """Find conflicts for a document.

        Args:
            document_id: Document UUID string
            status: Optional status filter (open | investigating | resolved | ignored)

        Returns:
            List of Conflict instances
        """
        query = select(Conflict).where(Conflict.document_id == document_id)
        if status:
            query = query.where(Conflict.status == status)
        query = query.order_by(Conflict.detected_at.desc())
        return list(self.session.execute(query).scalars())

    def find_by_severity(
        self,
        min_severity: str = "low",
        status: Optional[str] = None
    ) -> List[Conflict]:
        """Find conflicts by minimum severity.

        Args:
            min_severity: Minimum severity level (low | medium | high | critical)
            status: Optional status filter

        Returns:
            List of Conflict instances
        """
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_order.get(min_severity, 1)

        query = select(Conflict).where(
            Conflict.severity.in_([s for s, l in severity_order.items() if l >= min_level])
        )
        if status:
            query = query.where(Conflict.status == status)
        query = query.order_by(Conflict.detected_at.desc())
        return list(self.session.execute(query).scalars())

    def resolve(
        self,
        conflict_id: str,
        resolution: str
    ) -> Optional[Conflict]:
        """Resolve a conflict.

        Args:
            conflict_id: Conflict UUID string
            resolution: Resolution description

        Returns:
            Updated Conflict instance or None if not found
        """
        conflict = self.get_by_id(conflict_id)
        if conflict:
            conflict.status = "resolved"
            conflict.resolution = resolution
            conflict.resolved_at = datetime.utcnow()
            conflict.updated_at = datetime.utcnow()
            self.session.flush()
        return conflict
