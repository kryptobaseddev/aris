# ARIS MVP Testing and Validation Strategy

**Version**: 1.0.0
**Generated**: 2025-11-12
**Purpose**: Comprehensive testing strategy to prove ARIS solves document proliferation problem

---

## Executive Summary

This document defines the complete testing and validation strategy for the ARIS MVP. The goal is to prove with measurable data that ARIS solves the document proliferation problem while meeting quality, cost, and user satisfaction targets.

**Key Validation Questions**:
1. Does ARIS find and update existing documents instead of creating duplicates?
2. Do users trust the research results?
3. Is the cost per query sustainable?
4. Do users actually use the system repeatedly?

**MVP Success Metrics (3-month checkpoint)**:
- 10+ active users conducting research
- <10% duplicate document creation rate (down from ~60-70%)
- Average cost <$0.50 per query
- 30-day retention rate >60%
- User confidence in results >70%

---

## 1. Testing Pyramid Strategy

### 1.1 Test Distribution

```
                    E2E Tests (5%)
                  ┌──────────────┐
                  │ User Journey │
                  │ Real APIs    │
                  └──────────────┘
                       ▲
                       │
            Integration Tests (25%)
          ┌────────────────────────┐
          │ Multi-Agent Workflows  │
          │ Database + MCP         │
          └────────────────────────┘
                     ▲
                     │
              Unit Tests (70%)
        ┌──────────────────────────────┐
        │ Individual Components        │
        │ Pure Functions, Mocked Deps  │
        └──────────────────────────────┘
```

**Distribution Rationale**:
- **70% Unit Tests**: Fast feedback, comprehensive coverage
- **25% Integration Tests**: Verify component interactions
- **5% E2E Tests**: Validate user scenarios, expensive but critical

---

## 2. Unit Testing Strategy

### 2.1 Coverage Targets

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| `core/*` | 90%+ | Critical |
| `agents/*` | 85%+ | High |
| `integrations/*` | 70%+ | Medium |
| `knowledge/*` | 85%+ | High |
| `output/*` | 80%+ | Medium |
| `utils/*` | 95%+ | High |

### 2.2 Critical Unit Tests

#### **Semantic Deduplication (core/coordinator.py)**

**Test: Identical queries return same topic**
```python
@pytest.mark.asyncio
async def test_semantic_dedup_identical_query():
    """Identical queries should return existing topic"""
    coordinator = CoordinatorAgent(state_manager)

    # Create topic
    topic_id = await coordinator.execute_research(
        "How do booking systems handle offline mode?"
    )

    # Query again with identical text
    result = await coordinator.execute_research(
        "How do booking systems handle offline mode?"
    )

    assert result.mode == ResearchMode.UPDATE
    assert result.topic_id == topic_id
    assert result.duplicate_created == False
```

**Test: Semantically similar queries return same topic**
```python
@pytest.mark.asyncio
async def test_semantic_dedup_similar_query():
    """Semantically similar queries should match existing topic"""
    coordinator = CoordinatorAgent(state_manager)

    # Create topic
    topic_id = await coordinator.execute_research(
        "How do booking systems work offline?"
    )

    # Query with different words, same meaning
    result = await coordinator.execute_research(
        "How do reservation systems handle no internet connection?"
    )

    # Should match (cosine similarity > 0.85)
    assert result.mode == ResearchMode.UPDATE
    assert result.topic_id == topic_id
    assert result.duplicate_created == False
```

**Test: Different topics create separate documents**
```python
@pytest.mark.asyncio
async def test_semantic_dedup_different_topic():
    """Different topics should create new documents"""
    coordinator = CoordinatorAgent(state_manager)

    # Create topic
    topic_id_1 = await coordinator.execute_research(
        "How do booking systems work offline?"
    )

    # Completely different topic
    result = await coordinator.execute_research(
        "What is quantum computing?"
    )

    assert result.mode == ResearchMode.CREATE
    assert result.topic_id != topic_id_1
    assert result.duplicate_created == False
```

#### **Consensus Validation (core/consensus.py)**

**Test: All models agree (high confidence)**
```python
@pytest.mark.asyncio
async def test_consensus_unanimous_agreement():
    """All models agree should result in high confidence"""
    validator = ConsensusValidator()

    claim = "Python was created by Guido van Rossum"
    sources = [mock_wikipedia_source(), mock_python_org_source()]

    result = await validator.validate_claim(claim, sources)

    assert result.approved == True
    assert result.consensus_score >= 0.9
    assert len(result.model_results) == 3
    assert all(r.agrees for r in result.model_results)
```

**Test: Disagreement below threshold (reject)**
```python
@pytest.mark.asyncio
async def test_consensus_disagreement_reject():
    """Disagreement below threshold should reject claim"""
    validator = ConsensusValidator()

    claim = "The sky is green"  # Obviously false
    sources = [mock_dubious_source()]

    result = await validator.validate_claim(claim, sources)

    assert result.approved == False
    assert result.consensus_score < 0.5
    assert result.requires_human_review == True
```

**Test: Partial consensus (flag for review)**
```python
@pytest.mark.asyncio
async def test_consensus_partial_agreement():
    """Partial consensus should flag for review"""
    validator = ConsensusValidator()

    claim = "AI will replace all jobs by 2030"  # Controversial
    sources = [mock_source_a(), mock_source_b()]

    result = await validator.validate_claim(claim, sources)

    assert result.approved == False
    assert 0.5 <= result.consensus_score < 0.7
    assert result.requires_human_review == True
    assert result.confidence_level == ConfidenceLevel.LOW
```

#### **Document Update (agents/synthesizer.py)**

**Test: Update preserves existing content**
```python
@pytest.mark.asyncio
async def test_document_update_preserves_content():
    """Document updates should preserve unchanged sections"""
    synthesizer = SynthesizerAgent(state_manager)

    # Create initial document
    existing_content = """
    # Booking Systems Offline Architecture

    ## Introduction
    This is a user-written introduction that should be preserved.

    ## Offline Capabilities
    Systems support offline mode using local storage.
    """

    topic = await state_manager.create_topic(
        title="Booking Systems",
        document_path="research/booking.md"
    )
    await write_file(topic.document_path, existing_content)

    # Add new claim
    new_claim = Claim(
        content="PowerSync enables real-time sync when reconnecting",
        section_anchor="offline-capabilities"
    )

    # Update document
    result = await synthesizer.update_document(topic, [new_claim])

    updated_content = await read_file(topic.document_path)

    # Should preserve user introduction
    assert "This is a user-written introduction" in updated_content

    # Should add new claim
    assert "PowerSync enables real-time sync" in updated_content

    # Should not delete existing content
    assert "Systems support offline mode" in updated_content
```

#### **Cost Tracking (utils/token_tracker.py)**

**Test: Token usage tracking**
```python
@pytest.mark.asyncio
async def test_token_usage_tracking():
    """Track token usage per query for cost control"""
    tracker = TokenTracker()

    # Simulate research workflow
    tracker.log_usage(
        provider="anthropic",
        model="claude-sonnet-4-5",
        prompt_tokens=1500,
        completion_tokens=800,
        cost_usd=0.02
    )

    tracker.log_usage(
        provider="openai",
        model="gpt-4-turbo",
        prompt_tokens=1500,
        completion_tokens=800,
        cost_usd=0.03
    )

    summary = tracker.get_summary()

    assert summary.total_cost < 0.50  # MVP target
    assert summary.total_tokens < 10000
    assert len(summary.provider_breakdown) == 2
```

### 2.3 Property-Based Testing

**Test: Semantic similarity is commutative**
```python
from hypothesis import given, strategies as st

@given(
    query_a=st.text(min_size=10, max_size=200),
    query_b=st.text(min_size=10, max_size=200)
)
def test_semantic_similarity_commutative(query_a, query_b):
    """similarity(A, B) == similarity(B, A)"""
    sim_ab = calculate_similarity(query_a, query_b)
    sim_ba = calculate_similarity(query_b, query_a)

    assert abs(sim_ab - sim_ba) < 0.001
```

**Test: Consensus score always between 0 and 1**
```python
from hypothesis import given, strategies as st

@given(
    model_votes=st.lists(
        st.booleans(),
        min_size=3,
        max_size=5
    )
)
def test_consensus_score_bounded(model_votes):
    """Consensus score must be between 0.0 and 1.0"""
    score = calculate_consensus_score(model_votes)

    assert 0.0 <= score <= 1.0
```

---

## 3. Integration Testing Strategy

### 3.1 End-to-End Workflows (Mocked APIs)

#### **Test: Complete Research Workflow**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_research_workflow():
    """Test complete research workflow with mocked external APIs"""

    # Mock external dependencies
    with mock_tavily_search(), mock_anthropic(), mock_openai():
        orchestrator = Orchestrator(state_manager)

        # Execute research
        result = await orchestrator.execute_research(
            query="How do booking systems handle offline mode?",
            mode=ResearchMode.AUTO
        )

        # Verify workflow completed
        assert result.status == "completed"
        assert result.confidence >= 0.7

        # Verify document created
        assert Path(result.document_path).exists()

        # Verify claims validated
        claims = await state_manager.get_claims(result.topic_id)
        assert len(claims) > 0
        assert all(c.validated_at is not None for c in claims)

        # Verify sources stored
        sources = await state_manager.get_sources_for_topic(result.topic_id)
        assert len(sources) >= 3

        # Verify task execution
        tasks = await state_manager.get_tasks(result.topic_id)
        assert all(t.status == "completed" for t in tasks)
```

#### **Test: Update Existing Document Workflow**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_existing_document_workflow():
    """Test updating existing document instead of creating duplicate"""

    with mock_tavily_search(), mock_anthropic(), mock_openai():
        orchestrator = Orchestrator(state_manager)

        # First research query
        result_1 = await orchestrator.execute_research(
            query="What is PowerSync offline-first architecture?"
        )

        topic_id_1 = result_1.topic_id
        doc_path_1 = result_1.document_path
        version_1 = result_1.version

        # Second query with similar semantic meaning
        result_2 = await orchestrator.execute_research(
            query="How does PowerSync handle offline data synchronization?"
        )

        # Should update same document
        assert result_2.mode == ResearchMode.UPDATE
        assert result_2.topic_id == topic_id_1
        assert result_2.document_path == doc_path_1
        assert result_2.version == version_1 + 1

        # Verify no duplicate created
        topics = await state_manager.get_all_topics()
        powersync_topics = [
            t for t in topics
            if "powersync" in t.title.lower()
        ]
        assert len(powersync_topics) == 1  # Only one topic
```

#### **Test: Parallel Task Execution**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_task_execution():
    """Test DAG executes independent tasks in parallel"""

    orchestrator = Orchestrator(state_manager)

    # Create task DAG with parallelizable tasks
    task_1 = Task(agent_type="researcher", task_spec={"query": "A"})
    task_2 = Task(agent_type="researcher", task_spec={"query": "B"})
    task_3 = Task(agent_type="researcher", task_spec={"query": "C"})
    task_4 = Task(
        agent_type="validator",
        task_spec={"validate": "all"},
        depends_on=[task_1.id, task_2.id, task_3.id]
    )

    start_time = time.time()

    # Execute DAG
    results = await orchestrator.task_queue.execute_dag(task_1.id)

    duration = time.time() - start_time

    # Tasks 1-3 should run in parallel, not sequentially
    # If sequential: ~3 seconds, if parallel: ~1 second
    assert duration < 2.0  # Parallelism working

    # All tasks completed
    assert all(r.status == "completed" for r in results.values())
```

#### **Test: Conflict Detection and Resolution**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_conflict_detection_workflow():
    """Test contradiction detection between claims"""

    with mock_anthropic(), mock_openai():
        orchestrator = Orchestrator(state_manager)

        # Create topic with initial claim
        result_1 = await orchestrator.execute_research(
            query="What is the speed of light?"
        )

        # Inject contradictory claim (for testing)
        contradictory_claim = Claim(
            topic_id=result_1.topic_id,
            content="The speed of light is 150,000 km/s",  # Wrong
            confidence=0.3
        )

        await state_manager.add_claim(contradictory_claim)

        # Trigger conflict detection
        validator = ValidatorAgent(state_manager)
        conflicts = await validator.detect_contradictions(result_1.topic_id)

        # Should detect conflict
        assert len(conflicts) > 0

        conflict = conflicts[0]
        assert conflict.conflict_type == "contradiction"
        assert conflict.severity in ["medium", "high"]
        assert conflict.resolved == False
```

### 3.2 Database Transaction Testing

**Test: Transaction rollback on validation failure**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_rollback_on_failure():
    """Failed validation should rollback all changes"""

    async with state_manager.transaction() as tx:
        # Create topic
        topic = await tx.create_topic(
            title="Test Topic",
            document_path="test.md"
        )

        # Add claims
        claims = [
            Claim(topic_id=topic.id, content="Claim 1"),
            Claim(topic_id=topic.id, content="Claim 2")
        ]
        await tx.add_claims(claims)

        # Simulate validation failure
        raise ValidationError("Consensus threshold not met")

    # Transaction should have rolled back
    topics = await state_manager.get_all_topics()
    assert len(topics) == 0  # No topic created

    claims = await state_manager.get_all_claims()
    assert len(claims) == 0  # No claims stored
```

### 3.3 MCP Integration Testing

**Test: Tavily fallback to native search**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_fallback_tavily_down():
    """Test graceful degradation when Tavily unavailable"""

    # Simulate Tavily server down
    with mock_tavily_unavailable():
        researcher = ResearcherAgent(state_manager)

        # Should fallback to native search
        results = await researcher.research("test query")

        # Should still get results (from fallback)
        assert len(results) > 0
        assert results[0].source_type == "native_search"
```

---

## 4. Performance Testing Strategy

### 4.1 Cost Benchmarks

**Test: Research query cost under $0.50**
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_research_cost_under_target():
    """Each research query should cost < $0.50"""

    tracker = TokenTracker()

    with track_costs(tracker):
        result = await orchestrator.execute_research(
            query="Sample research query"
        )

    cost = tracker.get_total_cost()

    # MVP target: < $0.50 per query
    assert cost < 0.50, f"Cost ${cost:.2f} exceeds $0.50 target"
```

**Test: Caching reduces costs**
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_caching_reduces_costs():
    """Repeated queries should use cache to reduce costs"""

    tracker = TokenTracker()

    # First query (full cost)
    with track_costs(tracker):
        result_1 = await orchestrator.execute_research("test query")
    cost_1 = tracker.get_total_cost()

    tracker.reset()

    # Second identical query (should use cache)
    with track_costs(tracker):
        result_2 = await orchestrator.execute_research("test query")
    cost_2 = tracker.get_total_cost()

    # Second query should be cheaper (cache hits)
    assert cost_2 < cost_1 * 0.5  # At least 50% cheaper
```

### 4.2 Latency Benchmarks

**Test: Research completes within acceptable time**
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_research_latency_acceptable():
    """Research should complete within reasonable time"""

    start_time = time.time()

    result = await orchestrator.execute_research(
        query="Sample query"
    )

    duration = time.time() - start_time

    # Should complete within 5 minutes
    assert duration < 300, f"Research took {duration}s, exceeds 300s limit"
```

**Test: Parallel execution improves throughput**
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_parallel_execution_throughput():
    """Parallel tasks should complete faster than sequential"""

    # Sequential execution baseline
    start = time.time()
    for i in range(5):
        await researcher.research(f"query {i}")
    sequential_time = time.time() - start

    # Parallel execution
    start = time.time()
    tasks = [researcher.research(f"query {i}") for i in range(5)]
    await asyncio.gather(*tasks)
    parallel_time = time.time() - start

    # Parallel should be significantly faster
    speedup = sequential_time / parallel_time
    assert speedup > 2.0, f"Speedup only {speedup}x, expected >2x"
```

### 4.3 Load Testing

**Test: Handle 10 concurrent users**
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_users_load():
    """System should handle 10 concurrent research queries"""

    async def user_research(user_id):
        return await orchestrator.execute_research(
            query=f"Research question from user {user_id}"
        )

    # Simulate 10 concurrent users
    tasks = [user_research(i) for i in range(10)]

    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start

    # All should complete
    assert all(not isinstance(r, Exception) for r in results)

    # Should complete in reasonable time (not 10x single query)
    assert duration < 600  # 10 minutes for 10 concurrent users
```

---

## 5. User Acceptance Testing (UAT)

### 5.1 Test User Recruitment

**Target**: 10+ active test users for 3-month MVP validation

**Recruitment Criteria**:
- Mix of technical and non-technical users
- Regular research needs (weekly or more)
- Willing to provide detailed feedback
- Comfortable with CLI tools (or willing to learn)

**Recruitment Sources**:
- Internal team members
- Technical communities (Reddit, Discord)
- Early adopter programs
- Academic researchers

### 5.2 UAT Scenarios

#### **Scenario 1: First-Time Research**

**User Story**: "As a new user, I want to conduct my first research query and understand the results"

**Test Steps**:
1. Install ARIS
2. Initialize project
3. Execute research query
4. Review generated document
5. Understand confidence scores and sources

**Success Criteria**:
- User completes workflow without assistance
- User expresses confidence in results (>70%)
- User understands what ARIS did
- Document is readable and useful

**Metrics**:
- Time to first successful query
- Confidence rating (1-5 scale)
- Usability rating (System Usability Scale)

#### **Scenario 2: Research Update (Not Duplicate)**

**User Story**: "As a user, I want to add more information to an existing research topic without creating duplicates"

**Test Steps**:
1. Conduct initial research on topic X
2. Wait 1 week
3. Conduct follow-up research on related aspect of topic X
4. Verify ARIS updated existing document (not created new)
5. Review diff showing what changed

**Success Criteria**:
- ARIS correctly identified existing topic
- Document updated (not duplicated)
- User sees clear diff of changes
- User confirms this behavior is desired

**Metrics**:
- Duplicate document creation rate
- User satisfaction with update behavior
- Accuracy of semantic matching

#### **Scenario 3: Conflict Review**

**User Story**: "As a user, I want to review contradictions detected by ARIS and make informed decisions"

**Test Steps**:
1. Conduct research on controversial topic
2. System flags contradictions
3. User reviews conflicting claims side-by-side
4. User sees source evidence for each claim
5. User makes resolution decision

**Success Criteria**:
- Conflicts presented clearly
- User understands the contradiction
- User feels empowered to make decision
- Resolution stored correctly

**Metrics**:
- Time to understand conflict
- Resolution accuracy (compared to expert review)
- User confidence in resolution

#### **Scenario 4: Cost Awareness**

**User Story**: "As a user, I want to understand the cost of my research queries"

**Test Steps**:
1. Conduct multiple research queries
2. View cost summary
3. Understand cost breakdown by provider
4. Adjust usage based on budget

**Success Criteria**:
- Cost information clear and accessible
- User understands cost drivers
- User can make informed decisions
- Average cost stays under $0.50/query

**Metrics**:
- Actual cost per query
- User satisfaction with cost transparency
- Budget adherence rate

### 5.3 User Feedback Collection

**Instruments**:
1. **Post-Query Survey** (after each research query):
   - Confidence in results (1-5 scale)
   - Relevance of findings (1-5 scale)
   - Document quality (1-5 scale)
   - Cost acceptability (Yes/No)

2. **Weekly Survey**:
   - Frequency of use (times per week)
   - Most valuable feature
   - Biggest pain point
   - Feature requests

3. **Monthly Interview** (30 minutes):
   - Deep dive on usage patterns
   - Comparison to previous research methods
   - Trust and confidence in system
   - Willingness to recommend

4. **System Usability Scale (SUS)** (monthly):
   - Standard 10-question usability assessment
   - Target score: 70+ (above average)

**Feedback Channels**:
- In-CLI feedback command: `aris feedback <rating> <comment>`
- Email feedback: feedback@aris-tool.com
- GitHub issues for bug reports
- Scheduled user interviews

---

## 6. Metrics Dashboard Design

### 6.1 Key Metrics to Track

#### **Document Proliferation Metrics** (Primary Goal)

```yaml
duplicate_rate:
  definition: "% of research queries that create new documents when existing topic exists"
  calculation: "(new_topics / total_queries) where semantic_similarity > 0.85"
  target: "< 10%"
  baseline: "60-70% (without ARIS)"
  measurement: "Automated tracking in database"

semantic_match_accuracy:
  definition: "% of queries correctly matched to existing topics"
  calculation: "correct_matches / (correct_matches + false_matches)"
  target: "> 90%"
  measurement: "User validation + manual review"

update_vs_create_ratio:
  definition: "Ratio of document updates to new document creations"
  target: "> 3:1 after 1 month"
  measurement: "Database tracking (ResearchMode.UPDATE vs CREATE)"
```

#### **Research Quality Metrics**

```yaml
consensus_score:
  definition: "Average consensus across all validated claims"
  target: "> 0.85"
  measurement: "Validation logs in database"

user_confidence:
  definition: "User-reported confidence in research results"
  target: "> 70% rating confident/very confident"
  measurement: "Post-query survey"

source_authority:
  definition: "Average authority score of sources"
  target: "> 0.75"
  measurement: "Source metadata in database"

conflict_detection_rate:
  definition: "% of real contradictions successfully detected"
  target: "> 80%"
  measurement: "Expert validation of flagged conflicts"
```

#### **Cost Metrics**

```yaml
cost_per_query:
  definition: "Average total cost per research query"
  target: "< $0.50"
  measurement: "Token usage tracking"

cost_breakdown:
  components:
    - "Search API costs (Tavily)"
    - "LLM inference costs (Anthropic, OpenAI, Google)"
    - "MCP server costs (Context7, etc.)"
  measurement: "Per-provider cost tracking"

budget_adherence:
  definition: "% of queries staying within cost target"
  target: "> 90%"
  measurement: "Automated cost tracking"
```

#### **User Engagement Metrics**

```yaml
active_users:
  definition: "Users conducting 1+ research query per week"
  target: "> 10 users by month 3"
  measurement: "User activity logs"

retention_rate:
  definition: "% of users active after 30 days"
  target: "> 60%"
  measurement: "Cohort analysis"

queries_per_user:
  definition: "Average queries per active user per week"
  target: "> 3"
  measurement: "Usage analytics"

repeat_usage_rate:
  definition: "% of users conducting 2+ queries"
  target: "> 80%"
  measurement: "User activity tracking"
```

#### **System Performance Metrics**

```yaml
research_completion_time:
  definition: "Time from query submission to document completion"
  target: "< 5 minutes p95"
  measurement: "Task execution logs"

error_rate:
  definition: "% of research queries that fail"
  target: "< 2%"
  measurement: "Task status logs"

api_success_rate:
  definition: "% of external API calls that succeed (with fallbacks)"
  target: "> 99%"
  measurement: "Integration layer logs"
```

### 6.2 Dashboard Implementation

#### **Real-Time Metrics Dashboard**

**Location**: `/data/metrics/dashboard.json` (updated every 5 minutes)

**CLI Command**: `aris metrics show`

**Dashboard Sections**:

```
=== ARIS Metrics Dashboard ===
Generated: 2025-11-12 14:30:00

[Document Proliferation]
Duplicate Rate:        8.3%  ✅ (Target: < 10%)
Semantic Match:       92.1%  ✅ (Target: > 90%)
Update/Create Ratio:   4.2:1 ✅ (Target: > 3:1)

[Research Quality]
Consensus Score:      0.87   ✅ (Target: > 0.85)
User Confidence:      74%    ✅ (Target: > 70%)
Source Authority:     0.79   ✅ (Target: > 0.75)
Conflict Detection:   83%    ✅ (Target: > 80%)

[Cost Management]
Avg Cost/Query:       $0.42  ✅ (Target: < $0.50)
Budget Adherence:     94%    ✅ (Target: > 90%)
Total Queries Today:  47
Total Cost Today:     $19.74

[User Engagement]
Active Users (30d):   12     ✅ (Target: > 10)
Retention (30d):      67%    ✅ (Target: > 60%)
Queries/User/Week:    3.8    ✅ (Target: > 3)
Repeat Users:         87%    ✅ (Target: > 80%)

[System Performance]
Completion Time (p95): 4.2m  ✅ (Target: < 5m)
Error Rate:           1.3%   ✅ (Target: < 2%)
API Success:          99.7%  ✅ (Target: > 99%)

[30-Day Trend]
▲ Duplicate Rate:     -15.2% (improving)
▲ User Confidence:    +8%    (improving)
▲ Cost/Query:         -$0.08 (improving)
▲ Active Users:       +5     (growing)
```

#### **Metrics Storage Schema**

```sql
CREATE TABLE metrics_snapshots (
    id UUID PRIMARY KEY,
    captured_at TIMESTAMP NOT NULL,

    -- Document Proliferation
    duplicate_rate FLOAT,
    semantic_match_accuracy FLOAT,
    update_create_ratio FLOAT,

    -- Research Quality
    avg_consensus_score FLOAT,
    user_confidence_pct FLOAT,
    avg_source_authority FLOAT,
    conflict_detection_rate FLOAT,

    -- Cost
    avg_cost_per_query FLOAT,
    total_cost_today FLOAT,
    budget_adherence_pct FLOAT,

    -- Engagement
    active_users_30d INT,
    retention_rate_30d FLOAT,
    avg_queries_per_user_week FLOAT,
    repeat_usage_rate FLOAT,

    -- Performance
    p95_completion_time_seconds INT,
    error_rate_pct FLOAT,
    api_success_rate_pct FLOAT,

    -- Raw counts
    total_queries_today INT,
    total_users INT,

    metadata JSONB
);

-- Index for time-series queries
CREATE INDEX idx_metrics_captured ON metrics_snapshots(captured_at DESC);
```

#### **Automated Metric Collection**

```python
# scripts/collect_metrics.py (runs every 5 minutes via cron)

async def collect_metrics():
    """Collect and store current metrics snapshot"""

    snapshot = MetricsSnapshot(
        captured_at=datetime.utcnow(),

        # Calculate document proliferation metrics
        duplicate_rate=await calculate_duplicate_rate(),
        semantic_match_accuracy=await calculate_match_accuracy(),
        update_create_ratio=await calculate_update_create_ratio(),

        # Calculate quality metrics
        avg_consensus_score=await calculate_avg_consensus(),
        user_confidence_pct=await calculate_user_confidence(),
        avg_source_authority=await calculate_source_authority(),
        conflict_detection_rate=await calculate_conflict_detection(),

        # Calculate cost metrics
        avg_cost_per_query=await calculate_avg_cost(),
        total_cost_today=await calculate_total_cost_today(),
        budget_adherence_pct=await calculate_budget_adherence(),

        # Calculate engagement metrics
        active_users_30d=await count_active_users(days=30),
        retention_rate_30d=await calculate_retention(days=30),
        avg_queries_per_user_week=await calculate_queries_per_user(),
        repeat_usage_rate=await calculate_repeat_usage(),

        # Calculate performance metrics
        p95_completion_time_seconds=await calculate_p95_latency(),
        error_rate_pct=await calculate_error_rate(),
        api_success_rate_pct=await calculate_api_success(),

        # Raw counts
        total_queries_today=await count_queries_today(),
        total_users=await count_total_users()
    )

    await state_manager.store_metrics_snapshot(snapshot)
```

---

## 7. Validation Criteria for MVP Success

### 7.1 3-Month Checkpoint Criteria

**MUST ACHIEVE (Hard Requirements)**:
- ✅ Duplicate rate < 10% (down from 60-70% baseline)
- ✅ Average cost < $0.50 per query
- ✅ 10+ active users conducting research
- ✅ Error rate < 5%

**SHOULD ACHIEVE (Target Requirements)**:
- ✅ User confidence > 70%
- ✅ 30-day retention > 60%
- ✅ Consensus score > 0.85
- ✅ Source authority > 0.75

**NICE TO HAVE (Stretch Goals)**:
- Semantic match accuracy > 95%
- API success rate > 99%
- P95 completion time < 3 minutes
- Queries per user per week > 5

### 7.2 Go/No-Go Decision Framework

**Decision Point**: End of Month 3

**GO Criteria** (Proceed to Phase 2):
- All MUST ACHIEVE criteria met
- At least 3 out of 4 SHOULD ACHIEVE criteria met
- No critical bugs or security issues
- Positive user feedback (NPS > 0)
- Clear path to scale (technical and economic)

**NO-GO Criteria** (Pivot or Cancel):
- Duplicate rate > 20% (not solving core problem)
- Average cost > $0.75 per query (not economically viable)
- < 5 active users (no product-market fit)
- Error rate > 10% (too unreliable)
- Negative user feedback (NPS < -20)

**CONDITIONAL GO** (Extend MVP, fix issues):
- Duplicate rate 10-20% (partial success)
- Cost $0.50-$0.75 (needs optimization)
- 5-10 active users (weak traction)
- Some SHOULD ACHIEVE criteria missed
- Mixed user feedback (NPS 0-20)

---

## 8. Testing Automation

### 8.1 Continuous Integration

**CI Pipeline** (GitHub Actions):

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: poetry install
      - name: Run unit tests
        run: poetry run pytest tests/unit --cov=aris --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
      neo4j:
        image: neo4j:5
      chroma:
        image: chromadb/chroma:latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: poetry install
      - name: Run integration tests
        run: poetry run pytest tests/integration

  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: poetry install
      - name: Run performance benchmarks
        run: poetry run python scripts/benchmark.py
      - name: Compare to baseline
        run: poetry run python scripts/compare_performance.py
```

### 8.2 Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.290
    hooks:
      - id: ruff

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: poetry run pytest tests/unit -x
        language: system
        pass_filenames: false
        always_run: true
```

### 8.3 Nightly Test Suite

**Schedule**: Every night at 2 AM UTC

**Tests**:
- Full unit test suite (70%)
- Full integration test suite (25%)
- E2E tests with real APIs (5%)
- Performance benchmarks
- Security scans (Bandit, Safety)
- Dependency vulnerability checks

**Notifications**:
- Email report to team
- Slack notification on failures
- GitHub issue creation for regressions

---

## 9. Failure Scenarios and Rollback Plan

### 9.1 Failure Scenarios

#### **Scenario 1: Semantic Matching Too Aggressive**

**Symptom**: Different topics incorrectly merged

**Detection**:
- User reports unexpected document updates
- Semantic match accuracy < 70%
- Increase in "this should be separate" feedback

**Response**:
1. Increase similarity threshold (0.85 → 0.90)
2. Add manual review for borderline matches
3. Implement user override: `aris research --force-new`

**Rollback**: Decrease threshold, split incorrectly merged topics

#### **Scenario 2: Cost Exceeds Budget**

**Symptom**: Average cost > $0.75 per query

**Detection**:
- Automated cost alerts
- Budget adherence < 50%
- User complaints about pricing

**Response**:
1. Reduce consensus validation to 2 models (cheaper)
2. Increase caching aggressiveness
3. Use cheaper models for preliminary validation
4. Implement query complexity assessment

**Rollback**: Revert to full 3-model validation for critical queries

#### **Scenario 3: Low User Adoption**

**Symptom**: < 5 active users after 3 months

**Detection**:
- User activity logs
- Low retention rate
- Minimal repeat usage

**Response**:
1. Conduct user interviews to understand barriers
2. Simplify onboarding process
3. Add guided tutorials
4. Improve documentation
5. Consider web UI instead of CLI

**Rollback**: N/A (product issue, not technical)

#### **Scenario 4: High Error Rate**

**Symptom**: Error rate > 10%

**Detection**:
- Automated error monitoring
- User bug reports
- Task failure logs

**Response**:
1. Identify most common error patterns
2. Improve error handling and recovery
3. Add more fallback strategies
4. Increase MCP client timeout tolerance
5. Implement graceful degradation

**Rollback**: Disable problematic features, manual intervention

### 9.2 Rollback Procedures

**Database Rollback**:
```bash
# Revert to previous migration
poetry run alembic downgrade -1

# Restore from backup
pg_restore -d aris data/backups/aris_backup_YYYYMMDD.dump
```

**Feature Flags**:
```python
# config.yaml
features:
  semantic_deduplication: true  # Toggle on/off
  multi_model_consensus: true
  knowledge_graph: false  # Disable problematic features
```

**Emergency Procedures**:
1. Disable automated processing
2. Switch to manual review mode
3. Notify active users of issues
4. Restore from last known good state
5. Root cause analysis
6. Fix and gradual re-enable

---

## 10. Success Stories and Case Studies

### 10.1 Case Study Template

For each UAT participant, document:

**Before ARIS**:
- Research process description
- Time spent per research task
- Number of documents created
- Pain points and frustrations

**After ARIS** (3 months):
- New research process with ARIS
- Time saved per research task
- Document organization improvement
- Duplicate reduction metrics
- Overall satisfaction

**Quotes**:
- Direct user testimonials
- Specific feature praise
- Improvement suggestions

**Metrics**:
- Quantitative before/after comparison
- ROI calculation (time saved × hourly rate)

---

## 11. Next Steps After MVP Validation

### 11.1 If MVP Succeeds (GO Decision)

**Phase 2 Priorities**:
1. Expand user base (100+ users)
2. Add web UI for non-technical users
3. Implement advanced features (knowledge graph visualization)
4. Optimize costs further (target: < $0.25/query)
5. Add collaboration features (team workspaces)

### 11.2 If MVP Fails (NO-GO Decision)

**Pivot Options**:
1. Focus on single-user desktop app (simpler scope)
2. Partner with existing research tools (integration)
3. Pivot to specific niche (academic research only)
4. Open source and community-driven development

### 11.3 If MVP Conditional (EXTEND Decision)

**Focus Areas**:
1. Improve weak metrics (duplicate rate, cost, adoption)
2. Extended beta period (3 more months)
3. Targeted feature improvements
4. Aggressive user feedback incorporation

---

## Appendix A: Testing Tools and Frameworks

**Unit Testing**:
- pytest (test framework)
- pytest-asyncio (async test support)
- pytest-cov (coverage reporting)
- pytest-mock (mocking support)
- hypothesis (property-based testing)

**Integration Testing**:
- pytest-docker (containerized dependencies)
- testcontainers-python (PostgreSQL, Neo4j)
- responses (HTTP mocking)
- freezegun (time mocking)

**Performance Testing**:
- locust (load testing)
- py-spy (profiling)
- memory_profiler (memory analysis)
- pytest-benchmark (micro-benchmarks)

**E2E Testing**:
- playwright-python (browser automation)
- real API testing (with rate limits)

**Code Quality**:
- black (formatting)
- ruff (linting)
- mypy (type checking)
- bandit (security scanning)
- safety (dependency vulnerabilities)

---

## Appendix B: Sample Test Data

**Sample Queries for Testing**:

```python
SEMANTIC_DUPLICATE_QUERIES = [
    ("How do booking systems work offline?", "How do reservation systems handle no internet?"),
    ("What is PowerSync?", "Explain PowerSync offline-first architecture"),
    ("Python async/await tutorial", "How to use asyncio in Python"),
]

DIFFERENT_TOPIC_QUERIES = [
    ("How do booking systems work offline?", "What is quantum computing?"),
    ("Python async tutorial", "JavaScript promises explained"),
]

CONTROVERSIAL_QUERIES = [
    "Will AI replace all jobs?",
    "Is climate change man-made?",
    "Are GMO foods safe?",
]

TECHNICAL_QUERIES = [
    "How does React Server Components work?",
    "Explain PostgreSQL MVCC",
    "What is Kubernetes pod scheduling?",
]
```

---

## Appendix C: User Survey Templates

**Post-Query Survey**:

```
Thank you for using ARIS!

1. How confident are you in these research results?
   [ ] Very confident
   [ ] Confident
   [ ] Somewhat confident
   [ ] Not confident
   [ ] Not confident at all

2. How relevant were the findings to your query?
   [ ] Very relevant
   [ ] Relevant
   [ ] Somewhat relevant
   [ ] Not relevant

3. How would you rate the document quality?
   [1] [2] [3] [4] [5]

4. Was the cost of this query acceptable?
   [ ] Yes
   [ ] No

5. Any additional feedback? (optional)
   [Free text]
```

**Weekly Survey**:

```
Weekly ARIS Feedback

1. How many research queries did you conduct this week?
   [ ] 0  [ ] 1-2  [ ] 3-5  [ ] 6-10  [ ] 10+

2. What was your most valuable feature this week?
   [Free text]

3. What was your biggest pain point?
   [Free text]

4. Any feature requests?
   [Free text]
```

---

## Conclusion

This comprehensive testing and validation strategy provides a complete framework for proving ARIS solves the document proliferation problem while meeting all MVP success criteria. The multi-layered approach (unit, integration, performance, UAT) ensures both technical correctness and real-world usability.

**Key Success Factors**:
1. **Automated testing** catches regressions early
2. **Real user validation** proves product-market fit
3. **Metrics-driven decisions** based on objective data
4. **Clear go/no-go criteria** for Phase 2 decisions
5. **Failure scenarios planned** with rollback procedures

**Next Action**: Begin Phase 1 implementation with testing infrastructure in place from day one.
