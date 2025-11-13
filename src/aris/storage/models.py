"""SQLAlchemy database models for ARIS metadata storage."""

from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Table,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# Use String for UUID to support SQLite and PostgreSQL
Base = declarative_base()


def generate_uuid() -> str:
    """Generate UUID string for primary keys."""
    return str(uuid4())


# Association table for many-to-many document-source relationship
document_sources = Table(
    "document_sources",
    Base.metadata,
    Column("document_id", String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("source_id", String(36), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
    Column("citation_count", Integer, default=0),
    Column("relevance_score", Float, default=0.0),
    Column("added_at", DateTime, default=datetime.utcnow),
)


class Topic(Base):
    """Research topic tracking."""

    __tablename__ = "topics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active | archived | completed
    confidence = Column(Float, default=0.0)  # Overall confidence in topic understanding
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="topic", cascade="all, delete-orphan")
    research_sessions = relationship("ResearchSession", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name={self.name}, status={self.status})>"


class Document(Base):
    """Research document metadata."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Document identity
    title = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False, unique=True)

    # Content metadata
    word_count = Column(Integer, default=0)
    status = Column(String(50), default="draft")  # draft | review | published | archived
    confidence = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_research_at = Column(DateTime, nullable=True)

    # Vector embedding reference (stored in separate vector DB)
    embedding_id = Column(String(100), nullable=True)

    # Relationships
    topic = relationship("Topic", back_populates="documents")
    sources = relationship("Source", secondary=document_sources, back_populates="documents")
    outgoing_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_doc_id",
        back_populates="source_document",
        cascade="all, delete-orphan"
    )
    incoming_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.target_doc_id",
        back_populates="target_document",
        cascade="all, delete-orphan"
    )
    conflicts = relationship("Conflict", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_document_topic_status", "topic_id", "status"),
        Index("idx_document_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, status={self.status})>"


class Source(Base):
    """Research source with credibility tracking."""

    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Source identity
    url = Column(String(2000), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    source_type = Column(String(50), default="other")  # academic | news | blog | documentation | other

    # Credibility
    tier = Column(Integer, default=3)  # 1 (highest) to 4 (lowest)
    credibility_score = Column(Float, default=0.6)
    verification_status = Column(String(50), default="unverified")  # unverified | verified | disputed

    # Content
    summary = Column(Text, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Usage tracking
    total_citations = Column(Integer, default=0)
    average_relevance = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", secondary=document_sources, back_populates="sources")
    # Note: research_hops relationship removed - ResearchHop.sources_found should use specific queries

    __table_args__ = (
        Index("idx_source_tier_credibility", "tier", "credibility_score"),
    )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, title={self.title}, tier={self.tier})>"


class Relationship(Base):
    """Document-to-document relationships."""

    __tablename__ = "relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Relationship endpoints
    source_doc_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    target_doc_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Relationship metadata
    relationship_type = Column(String(50), nullable=False)  # contradicts | supports | extends | cites | related
    strength = Column(Float, default=0.5)  # 0.0 to 1.0
    evidence = Column(Text, nullable=True)  # Supporting evidence or context

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    source_document = relationship("Document", foreign_keys=[source_doc_id], back_populates="outgoing_relationships")
    target_document = relationship("Document", foreign_keys=[target_doc_id], back_populates="incoming_relationships")

    __table_args__ = (
        UniqueConstraint("source_doc_id", "target_doc_id", "relationship_type", name="uq_relationship"),
        Index("idx_relationship_type", "relationship_type"),
        Index("idx_relationship_strength", "strength"),
    )

    def __repr__(self) -> str:
        return f"<Relationship(source={self.source_doc_id}, target={self.target_doc_id}, type={self.relationship_type})>"


class ResearchSession(Base):
    """Research session tracking with cost metrics."""

    __tablename__ = "research_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Query information
    query_text = Column(Text, nullable=False)
    query_depth = Column(String(50), default="standard")  # quick | standard | deep | exhaustive

    # Execution state
    status = Column(String(50), default="planning")  # planning | searching | analyzing | validating | complete | error
    current_hop = Column(Integer, default=1)
    max_hops = Column(Integer, default=5)

    # Results
    documents_found = Column(Text, nullable=True)  # JSON array of document IDs
    document_created_id = Column(String(36), nullable=True)
    document_updated_id = Column(String(36), nullable=True)
    final_confidence = Column(Float, default=0.0)

    # Cost tracking
    total_cost = Column(Float, default=0.0)
    budget_target = Column(Float, default=0.50)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    topic = relationship("Topic", back_populates="research_sessions")
    hops = relationship("ResearchHop", back_populates="session", cascade="all, delete-orphan", order_by="ResearchHop.hop_number")

    __table_args__ = (
        Index("idx_session_status", "status"),
        Index("idx_session_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<ResearchSession(id={self.id}, query={self.query_text[:50]}, status={self.status})>"


class ResearchHop(Base):
    """Individual search iteration within a research session."""

    __tablename__ = "research_hops"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Hop metadata
    hop_number = Column(Integer, nullable=False)
    search_query = Column(Text, nullable=False)
    search_strategy = Column(String(100), nullable=True)  # broad | targeted | verification

    # Results
    sources_found_count = Column(Integer, default=0)
    sources_added_count = Column(Integer, default=0)
    confidence_before = Column(Float, default=0.0)
    confidence_after = Column(Float, default=0.0)

    # Cost tracking
    llm_calls = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("ResearchSession", back_populates="hops")
    # Note: Sources for this hop are tracked by sources_found_count field, not a relationship

    __table_args__ = (
        UniqueConstraint("session_id", "hop_number", name="uq_session_hop"),
        Index("idx_hop_session", "session_id", "hop_number"),
    )

    def __repr__(self) -> str:
        return f"<ResearchHop(session={self.session_id}, hop={self.hop_number}, query={self.search_query[:50]})>"


class Conflict(Base):
    """Semantic conflict tracking between sources or within documents."""

    __tablename__ = "conflicts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Conflict details
    conflict_type = Column(String(50), nullable=False)  # contradiction | ambiguity | outdated
    severity = Column(String(50), default="low")  # low | medium | high | critical
    description = Column(Text, nullable=False)

    # Involved sources
    source_ids = Column(Text, nullable=True)  # JSON array of source IDs

    # Resolution
    status = Column(String(50), default="open")  # open | investigating | resolved | ignored
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="conflicts")

    __table_args__ = (
        Index("idx_conflict_status", "status"),
        Index("idx_conflict_severity", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Conflict(id={self.id}, type={self.conflict_type}, severity={self.severity}, status={self.status})>"
