"""Research orchestrator coordinating all components for complete research workflows.

Integrates:
- Tavily MCP (search and evidence gathering)
- Sequential MCP (structured reasoning)
- Database (session tracking and cost management)
- Document Store (Git-backed document storage)
- Progress tracking (CLI streaming support)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from aris.core.progress_tracker import ProgressEventType, ProgressTracker
from aris.core.reasoning_engine import ReasoningEngine
from aris.models.config import ArisConfig
from aris.models.document import DocumentMetadata
from aris.models.research import (
    ResearchDepth,
    ResearchHop,
    ResearchQuery,
    ResearchResult,
    ResearchSession,
)
from aris.storage.database import DatabaseManager

if TYPE_CHECKING:
    from aris.storage.document_store import DocumentStore

logger = logging.getLogger(__name__)


class ResearchOrchestratorError(Exception):
    """Research orchestrator operation errors."""

    pass


class ResearchOrchestrator:
    """Orchestrates complete research workflows from query to document.

    Coordinates all ARIS components to execute research:
    1. Create research session in database
    2. Analyze query and create research plan
    3. Execute multi-hop research with Tavily + Sequential
    4. Track costs and enforce budget limits
    5. Store results in documents via Git
    6. Provide real-time progress updates

    Example:
        config = ConfigManager.get_instance().get_config()
        orchestrator = ResearchOrchestrator(config)

        result = await orchestrator.execute_research(
            query="Latest advances in LLM reasoning",
            depth="standard",
            max_cost=0.50
        )

        print(f"Document: {result.document_path}")
        print(f"Confidence: {result.confidence:.2%}")
        print(f"Cost: ${result.total_cost:.2f}")
    """

    def __init__(self, config: ArisConfig) -> None:
        """Initialize research orchestrator.

        Args:
            config: ARIS configuration
        """
        from aris.core.deduplication_gate import DeduplicationGate
        from aris.core.document_finder import DocumentFinder
        from aris.mcp.serena_client import SerenaClient
        from aris.storage import DocumentStore

        self.config = config
        self.db = DatabaseManager(Path(config.database_path))
        self.document_store = DocumentStore(config)
        self.document_finder = DocumentFinder(config)
        self.reasoning_engine = ReasoningEngine(config)
        self.progress_tracker = ProgressTracker()
        self.serena_client = SerenaClient()
        self.deduplication_gate = DeduplicationGate(
            db=self.db,
            research_dir=Path(config.research_dir)
        )

        logger.info("Research orchestrator initialized")

    async def execute_research(
        self,
        query: str,
        depth: str = "standard",
        max_cost: Optional[float] = None,
    ) -> ResearchResult:
        """Execute complete research workflow.

        Args:
            query: User research query
            depth: Research depth (quick, standard, deep)
            max_cost: Maximum cost override (overrides depth default)

        Returns:
            Research result with document path and metrics

        Raises:
            ResearchOrchestratorError: On research execution failure
        """
        self.progress_tracker.start(f"Starting {depth} research")

        try:
            # 1. Create research session
            session = self._create_research_session(query, depth, max_cost)
            logger.info(f"Created research session: {session.id}")

            # 2. Analyze query and create plan
            self.progress_tracker.update(
                "Analyzing query...", ProgressEventType.PLANNING
            )
            plan = await self.reasoning_engine.analyze_query(query)
            logger.info(f"Research plan created with {len(plan.hypotheses)} hypotheses")

            # 3. Check for existing documents (basic check for now)
            self.progress_tracker.update(
                "Checking existing research...", ProgressEventType.INFO
            )
            existing_docs = await self._find_similar_documents(query)
            similar_doc_path = existing_docs[0] if existing_docs else None

            # 4. Execute multi-hop research
            max_hops = self._get_max_hops(depth)
            target_confidence = 0.70

            context = await self._execute_research_hops(
                session=session,
                plan=plan,
                max_hops=max_hops,
                target_confidence=target_confidence,
            )

            # 5. Save research document
            self.progress_tracker.update(
                "Saving research findings...", ProgressEventType.SAVING
            )
            document = await self._save_research_document(
                session=session, context=context, query=query
            )

            # 6. Update session status
            session.status = "complete"
            session.final_confidence = context.overall_confidence
            session.completed_at = datetime.utcnow()

            # Store operation type
            operation = "created" if not existing_docs else "updated"
            if operation == "created":
                session.document_created = str(document.file_path)
            else:
                session.document_updated = str(document.file_path)

            self._update_session(session)

            # 7. Save session context for cross-session persistence
            await self.save_session_context(session)

            # 8. Create result
            result = ResearchResult(
                session_id=session.id,
                query_text=query,
                success=True,
                document_path=str(document.file_path),
                operation=operation,
                confidence=context.overall_confidence,
                sources_analyzed=len(context.all_sources),
                hops_executed=len(session.hops),
                total_cost=session.total_cost,
                within_budget=session.within_budget,
                duration_seconds=session.duration_seconds or 0.0,
            )

            # Add suggestions
            if not session.within_budget:
                result.warnings.append(
                    f"Research exceeded budget: ${session.total_cost:.2f} > ${session.budget_target:.2f}"
                )

            if context.overall_confidence < target_confidence:
                result.suggestions.append(
                    f"Consider deeper research (confidence: {context.overall_confidence:.2%})"
                )

            self.progress_tracker.complete(
                f"Research complete: {result.document_path}"
            )
            logger.info(f"Research completed successfully: {session.id}")

            return result

        except Exception as e:
            self.progress_tracker.error(f"Research failed: {str(e)}", error=e)
            logger.error(f"Research execution failed: {e}", exc_info=True)

            # Update session status if created
            if "session" in locals():
                session.status = "error"
                self._update_session(session)

            raise ResearchOrchestratorError(f"Research execution failed: {e}") from e

    async def _execute_research_hops(
        self,
        session: ResearchSession,
        plan,
        max_hops: int,
        target_confidence: float,
    ):
        """Execute multi-hop research with early stopping.

        Args:
            session: Research session for tracking
            plan: Research plan from ReasoningEngine
            max_hops: Maximum number of hops
            target_confidence: Target confidence for early stopping

        Returns:
            ReasoningContext with all hop results
        """
        from aris.mcp.reasoning_schemas import ReasoningContext

        context = ReasoningContext()

        for hop_num in range(1, max_hops + 1):
            self.progress_tracker.hop_progress(
                hop_num, max_hops, "Gathering evidence and analyzing..."
            )

            hop_started = datetime.utcnow()

            # Execute hop via reasoning engine
            hop_result = await self.reasoning_engine.execute_research_hop(
                plan=plan, hop_number=hop_num
            )

            hop_completed = datetime.utcnow()

            # Create database hop record
            db_hop = ResearchHop(
                hop_number=hop_num,
                started_at=hop_started,
                completed_at=hop_completed,
                search_queries=[],  # Will be populated from hop_result
                sources_found=len(hop_result.evidence),
                confidence_before=context.overall_confidence,
                confidence_after=hop_result.synthesis.confidence,
                confidence_gain=hop_result.synthesis.confidence
                - context.overall_confidence,
            )

            # Add hop to session
            session.add_hop(db_hop)
            self._update_session(session)

            # Update context
            context.add_hop_result(hop_result)

            logger.info(
                f"Hop {hop_num} complete: confidence={context.overall_confidence:.2f}, "
                f"sources={len(hop_result.evidence)}, cost=${db_hop.total_cost:.2f}"
            )

            # Check budget constraints
            if session.total_cost >= session.budget_target * 0.90:
                self.progress_tracker.warning(
                    f"Approaching budget limit: ${session.total_cost:.2f} / ${session.budget_target:.2f}"
                )
                session.budget_warnings_issued.append(
                    f"90% budget reached at hop {hop_num}"
                )

            if session.total_cost >= session.budget_target:
                self.progress_tracker.warning("Budget limit reached, stopping research")
                session.budget_warnings_issued.append(
                    f"Budget limit reached at hop {hop_num}"
                )
                break

            # Early stopping checks
            if context.overall_confidence >= target_confidence:
                self.progress_tracker.update(
                    f"Target confidence reached: {context.overall_confidence:.2%}",
                    ProgressEventType.INFO,
                )
                break

            # Refine plan for next hop based on results
            if hop_num < max_hops:
                plan = await self._refine_research_plan(plan, hop_result)

        # Final synthesis
        self.progress_tracker.update(
            "Synthesizing final findings...", ProgressEventType.SYNTHESIZING
        )

        # Use reasoning engine to synthesize all hypothesis results
        all_hypothesis_results = []
        for hop_result in context.hop_results:
            all_hypothesis_results.extend(hop_result.hypothesis_results)

        if all_hypothesis_results:
            final_synthesis = await self.reasoning_engine.sequential.synthesize_findings(
                all_hypothesis_results
            )
            context.final_synthesis = final_synthesis

        return context

    async def _refine_research_plan(self, plan, hop_result):
        """Refine research plan based on hop results.

        Args:
            plan: Current research plan
            hop_result: Results from completed hop

        Returns:
            Refined research plan for next hop
        """
        # For now, return same plan
        # Future: Use Sequential to generate follow-up questions
        # based on synthesis gaps and contradictions
        return plan

    async def _find_similar_documents(self, query: str) -> list:
        """Find existing documents similar to query.

        Uses semantic similarity search via DocumentFinder to identify
        documents that may be related to the research query.

        Args:
            query: Research query

        Returns:
            List of similar (Document, similarity_score) tuples
        """
        try:
            similar_docs = self.document_finder.find_similar_documents(
                query=query,
                threshold=0.80,
                limit=5,
            )
            logger.info(f"Found {len(similar_docs)} similar documents for query")
            return similar_docs
        except Exception as e:
            logger.warning(f"Document similarity search failed: {e}")
            return []

    async def _save_research_document(self, session: ResearchSession, context, query: str):
        """Save research findings as a document.

        Implements pre-write validation via deduplication gate to decide
        between CREATE (new document) or UPDATE (merge with existing).

        Args:
            session: Research session
            context: ReasoningContext with all results
            query: Original query

        Returns:
            Saved Document instance or updated Document instance
        """
        # Generate title from query
        title = self._generate_title(query)

        # Extract topics from hypotheses and findings
        topics = []
        if context.final_synthesis:
            topics = context.final_synthesis.key_findings[:3]

        # Format content as markdown
        content = self._format_research_findings(context, query, session)

        # Prepare metadata for deduplication gate
        metadata = {
            "title": title,
            "topics": topics,
            "purpose": query,
            "confidence": context.overall_confidence,
        }

        # Run pre-write validation gate to check for duplicates
        dedup_result = await self.deduplication_gate.check_before_write(
            content=content,
            metadata=metadata,
            query=query,
        )

        logger.info(
            f"Deduplication gate decision: {dedup_result.action} "
            f"(confidence: {dedup_result.confidence:.2%})"
        )
        logger.debug(f"Reason: {dedup_result.reason}")

        # Execute decision: CREATE or UPDATE
        if dedup_result.should_create:
            # Create new document
            document = self.document_store.create_document(
                title=title,
                content=content,
                topics=topics,
                confidence=context.overall_confidence,
            )
            logger.info(f"Research document created: {document.file_path}")

        else:
            # Update existing document (MERGE or UPDATE action)
            target_doc = dedup_result.target_document
            logger.info(
                f"Merging research findings with existing document: "
                f"{target_doc.metadata.title}"
            )

            # Prepare new metadata for merge
            new_metadata = DocumentMetadata(
                title=target_doc.metadata.title,
                purpose=target_doc.metadata.purpose,
                topics=topics,
                confidence=context.overall_confidence,
                source_count=len(context.all_sources),
            )

            # Use intelligent merge via document store
            merge_strategy = "integrate"  # Use intelligent integration
            document, merge_report = self.document_store.merge_document(
                file_path=target_doc.file_path,
                new_content=content,
                new_metadata=new_metadata,
                strategy=merge_strategy,
                commit_message=f"Merge: Research findings for '{title}'",
            )

            logger.info(
                f"Research document merged: {document.file_path} "
                f"(strategy={merge_strategy}, "
                f"conflicts={merge_report['conflicts_detected']}, "
                f"similarity={dedup_result.confidence:.2%})"
            )

        return document

    def _format_research_findings(
        self, context, query: str, session: ResearchSession
    ) -> str:
        """Format research findings as markdown.

        Args:
            context: ReasoningContext with results
            query: Original research query
            session: Research session with metrics

        Returns:
            Formatted markdown content
        """
        lines = []

        # Header
        lines.append(f"# Research: {query}")
        lines.append("")
        lines.append(f"**Research Date**: {session.started_at.strftime('%Y-%m-%d')}")
        lines.append(
            f"**Confidence Score**: {context.overall_confidence:.1%}"
        )
        lines.append(f"**Sources Analyzed**: {len(context.all_sources)}")
        lines.append(f"**Research Hops**: {len(session.hops)}")
        lines.append(f"**Cost**: ${session.total_cost:.2f}")
        lines.append("")

        # Summary
        if context.final_synthesis:
            lines.append("## Summary")
            lines.append("")
            for finding in context.final_synthesis.key_findings:
                lines.append(f"- {finding}")
            lines.append("")

        # Detailed findings by hop
        lines.append("## Research Process")
        lines.append("")

        for i, hop_result in enumerate(context.hop_results, 1):
            lines.append(f"### Hop {i}")
            lines.append("")

            # Hypotheses tested
            lines.append("**Hypotheses Tested**:")
            lines.append("")
            for hyp_result in hop_result.hypothesis_results:
                status = "✓" if hyp_result.supported else "✗"
                lines.append(
                    f"- {status} {hyp_result.hypothesis.statement} "
                    f"(confidence: {hyp_result.posterior_confidence:.1%})"
                )
            lines.append("")

            # Evidence
            if hop_result.evidence:
                lines.append("**Evidence**:")
                lines.append("")
                for evidence in hop_result.evidence[:5]:  # Limit to top 5
                    lines.append(f"- {evidence}")
                lines.append("")

            # Synthesis
            if hop_result.synthesis.key_findings:
                lines.append("**Key Findings**:")
                lines.append("")
                for finding in hop_result.synthesis.key_findings:
                    lines.append(f"- {finding}")
                lines.append("")

        # Sources
        if context.all_sources:
            lines.append("## Sources")
            lines.append("")
            for source in context.all_sources:
                lines.append(f"- {source}")
            lines.append("")

        # Gaps and recommendations
        if context.final_synthesis:
            if context.final_synthesis.remaining_gaps:
                lines.append("## Remaining Questions")
                lines.append("")
                for gap in context.final_synthesis.remaining_gaps:
                    lines.append(f"- {gap}")
                lines.append("")

            if context.final_synthesis.recommendations:
                lines.append("## Recommendations")
                lines.append("")
                for rec in context.final_synthesis.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        return "\n".join(lines)

    def _generate_title(self, query: str) -> str:
        """Generate document title from query.

        Args:
            query: Research query

        Returns:
            Document title
        """
        # Simple title generation
        # TODO: Use LLM to generate better titles in future
        title = query.strip()
        if len(title) > 80:
            title = title[:77] + "..."
        return title

    def _create_research_session(
        self, query: str, depth: str, max_cost: Optional[float]
    ) -> ResearchSession:
        """Create new research session in database.

        Args:
            query: Research query
            depth: Research depth level
            max_cost: Optional cost override

        Returns:
            Created ResearchSession
        """
        # Create query object
        depth_enum = ResearchDepth(depth)
        research_query = ResearchQuery(
            query_text=query, depth=depth_enum, max_cost=max_cost
        )

        # Determine budget
        budget_map = {
            ResearchDepth.QUICK: 0.20,
            ResearchDepth.STANDARD: 0.50,
            ResearchDepth.DEEP: 2.00,
        }
        budget = max_cost if max_cost is not None else budget_map[depth_enum]

        # Create session
        session = ResearchSession(
            query=research_query,
            budget_target=budget,
            status="planning",
        )

        # TODO: Store in database
        # For now, session exists in memory only
        # Wave 1 Agent 4 will implement database storage

        return session

    def _update_session(self, session: ResearchSession) -> None:
        """Update research session in database.

        Args:
            session: Research session to update
        """
        # TODO: Implement database update
        # For now, sessions are in-memory only
        pass

    def _get_max_hops(self, depth: str) -> int:
        """Get maximum hops for research depth.

        Args:
            depth: Research depth level

        Returns:
            Maximum number of hops
        """
        hop_map = {
            "quick": 1,
            "standard": 3,
            "deep": 5,
        }
        return hop_map.get(depth, 3)

    async def get_session_status(self, session_id: UUID) -> Optional[ResearchSession]:
        """Get status of a research session.

        Args:
            session_id: Session UUID

        Returns:
            ResearchSession if found, None otherwise
        """
        # TODO: Implement database lookup
        # For now, returns None
        return None

    async def save_session_context(self, session: ResearchSession) -> None:
        """Save research session context for cross-session persistence.

        Args:
            session: Research session to save

        Raises:
            ResearchOrchestratorError: If context save fails
        """
        try:
            from aris.mcp.serena_client import SessionContext

            context = SessionContext(
                session_id=str(session.id),
                query=session.query,
                created_at=session.created_at,
                last_updated=datetime.utcnow(),
                hops_executed=len(session.hops),
                max_hops=session.max_hops,
                documents_found=len(session.documents),
                research_depth=session.research_depth,
                status=session.status,
                findings_summary=session.findings_summary or "",
                execution_time_seconds=session.duration_seconds or 0.0,
                documents=[doc.model_dump() for doc in session.documents],
                sources=[source.model_dump() for source in session.sources],
                metadata={
                    "total_cost": session.total_cost,
                    "budget_target": session.budget_target,
                    "within_budget": session.within_budget,
                    "final_confidence": session.final_confidence,
                },
            )
            self.serena_client.save_session_context(context)
            logger.info(f"Session context saved: {session.id}")
        except Exception as e:
            logger.error(f"Failed to save session context: {e}")
            raise ResearchOrchestratorError(f"Failed to save session context: {e}") from e

    async def load_session_context(self, session_id: str) -> Optional[dict]:
        """Load research session context from memory.

        Args:
            session_id: ID of the session to load

        Returns:
            Session context dict if found, None otherwise
        """
        try:
            context = self.serena_client.load_session_context(session_id)
            if context:
                logger.info(f"Session context loaded: {session_id}")
                return context.model_dump()
            return None
        except Exception as e:
            logger.warning(f"Failed to load session context: {e}")
            return None

    def get_previous_sessions(self) -> list[str]:
        """Get list of previous research sessions.

        Returns:
            List of session IDs
        """
        return self.serena_client.list_sessions()

    async def update_document_index(self, documents: list[dict]) -> None:
        """Update cross-session document index.

        Args:
            documents: List of document metadata dicts
        """
        try:
            self.serena_client.save_document_index(documents)
            logger.info(f"Document index updated with {len(documents)} documents")
        except Exception as e:
            logger.error(f"Failed to update document index: {e}")

    def get_research_patterns(self) -> dict:
        """Get learned research patterns from previous sessions.

        Returns:
            Dictionary of research patterns
        """
        try:
            patterns = self.serena_client.load_research_patterns()
            logger.info(f"Loaded {len(patterns)} research patterns")
            return patterns
        except Exception as e:
            logger.warning(f"Failed to load research patterns: {e}")
            return {}

    def save_research_learnings(self, session_id: str, learnings: dict) -> None:
        """Save learning outcomes from a research session.

        Args:
            session_id: ID of the session
            learnings: Dictionary of learning insights
        """
        try:
            current_patterns = self.serena_client.load_research_patterns()
            current_patterns[session_id] = learnings
            self.serena_client.save_research_patterns(current_patterns)
            logger.info(f"Research learnings saved for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to save research learnings: {e}")

    def get_memory_stats(self) -> dict:
        """Get statistics about session memory.

        Returns:
            Dictionary with memory statistics
        """
        return self.serena_client.get_memory_stats()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.reasoning_engine.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.reasoning_engine.__aexit__(exc_type, exc_val, exc_tb)
