# ARIS Optimization Roadmap

**Based on**: Performance Profile Assessment (2025-11-14)
**Priority Framework**: Impact × Feasibility
**Timeline**: Immediate → Medium → Long-term

---

## Priority Matrix

| Optimization | Impact | Complexity | Priority | Est. Time |
|--------------|--------|------------|----------|-----------|
| Ensure Vector Store Init | HIGH | LOW | **P0** | 1 hour |
| Add Topic Indexing | HIGH | LOW | **P0** | 4 hours |
| End-to-End Benchmarks | MEDIUM | LOW | **P1** | 8 hours |
| Parallelize Hops | HIGH | MEDIUM | **P1** | 16 hours |
| Result Caching | MEDIUM | LOW | **P1** | 8 hours |
| Connection Pooling | MEDIUM | LOW | **P2** | 4 hours |
| Stream Processing | MEDIUM | MEDIUM | **P2** | 16 hours |
| Distributed Vector Store | HIGH | HIGH | **P3** | 40 hours |
| Query Plan Optimization | LOW | MEDIUM | **P3** | 16 hours |

---

## P0: Critical Performance Fixes

### 1. Ensure Vector Store Initialization
**Problem**: O(n²) database fallback when vector store unavailable
**File**: `src/aris/core/deduplication_gate.py`
**Impact**: Prevents catastrophic performance degradation

**Implementation**:
```python
def __init__(self, db, research_dir, vector_store=None):
    # Current: Optional vector store
    self.vector_store = vector_store

    # Recommended: Required vector store with validation
    if vector_store is None:
        vector_dir = research_dir.parent / ".aris" / "vectors"
        self.vector_store = VectorStore(persist_dir=vector_dir)

    # Validate vector store is operational
    try:
        self.vector_store.get_collection_stats()
    except VectorStoreError as e:
        raise DeduplicationGateError(
            "Vector store required for performance. "
            f"Initialization failed: {e}"
        )
```

**Validation**:
- Add startup check in `research_orchestrator.py`
- Fail fast if vector store unavailable
- Provide clear error message with resolution steps

**Expected Improvement**: Eliminates O(n²) fallback path entirely

---

### 2. Add Topic Indexing Table
**Problem**: LIKE queries cause full table scans
**Files**:
- `src/aris/storage/models.py` (new model)
- `src/aris/core/document_finder.py` (update queries)
- `alembic/versions/` (migration)

**Database Schema**:
```python
# models.py
class DocumentTopic(Base):
    __tablename__ = "document_topics"

    document_id = Column(String, ForeignKey("documents.id"), primary_key=True)
    topic = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="topic_associations")

# Update Document model
class Document(Base):
    # ... existing fields ...
    topic_associations = relationship("DocumentTopic", back_populates="document")
```

**Migration**:
```python
# alembic/versions/xxx_add_topic_index.py
def upgrade():
    # Create table
    op.create_table(
        'document_topics',
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('document_id', 'topic')
    )
    op.create_index('idx_topic', 'document_topics', ['topic'])

    # Migrate existing data
    # Parse topics from existing documents and populate table

def downgrade():
    op.drop_index('idx_topic', table_name='document_topics')
    op.drop_table('document_topics')
```

**Update Query Logic**:
```python
# document_finder.py
def find_by_topics(self, topics, ...):
    with self.db.session_scope() as session:
        # Old: LIKE queries
        # for topic in topics:
        #     topic_docs = repo.search_by_title(topic)

        # New: Indexed lookup
        from aris.storage.models import DocumentTopic

        query = session.query(Document).join(DocumentTopic).filter(
            DocumentTopic.topic.in_(topics)
        ).distinct()

        results = query.all()
```

**Expected Improvement**: 10x faster topic searches (200ms → 20ms for 100 docs)

---

## P1: High-Impact Optimizations

### 3. Add End-to-End Performance Benchmarks
**Problem**: No validation of estimated execution times
**File**: `tests/integration/test_performance_benchmarks.py`

**New Benchmarks**:
```python
@pytest.mark.benchmark
class TestResearchWorkflowPerformance:
    """End-to-end research workflow benchmarks."""

    @pytest.mark.asyncio
    async def test_quick_research_performance(self, orchestrator):
        """Benchmark quick research (1 hop)."""
        start = time.perf_counter()
        result = await orchestrator.execute_research(
            query="Test query",
            depth="quick",
            max_cost=0.20
        )
        elapsed = time.perf_counter() - start

        assert result.success
        assert elapsed < 30.0  # 30s target
        print(f"Quick research: {elapsed:.2f}s")

    @pytest.mark.asyncio
    async def test_standard_research_performance(self, orchestrator):
        """Benchmark standard research (3 hops)."""
        # Target: 45-90s
        # Assertions + detailed timing breakdown

    @pytest.mark.asyncio
    async def test_vector_store_scaling(self, benchmark_doc_store):
        """Benchmark vector store with 100/1K/10K documents."""
        for count in [100, 1000, 10000]:
            # Measure search time at scale
```

**Expected Value**: Validate estimates, identify real-world bottlenecks

---

### 4. Parallelize Independent Hops
**Problem**: Sequential execution when hops could run in parallel
**File**: `src/aris/core/research_orchestrator.py`

**Current Implementation**:
```python
# Lines 235-300: Sequential loop
for hop_num in range(1, max_hops + 1):
    hop_result = await self.reasoning_engine.execute_research_hop(
        plan=plan, hop_number=hop_num
    )
    context.add_hop_result(hop_result)

    # Check budget, early stopping
    if context.overall_confidence >= target_confidence:
        break
```

**Optimized Implementation**:
```python
async def _execute_research_hops(self, session, plan, max_hops, target_confidence):
    """Execute hops with intelligent parallelization."""
    context = ReasoningContext(query=session.query.query_text)

    # Phase 1: Parallel initial exploration (hops 1-2)
    if max_hops >= 2:
        async with asyncio.TaskGroup() as tg:
            hop1_task = tg.create_task(
                self._execute_single_hop(session, plan, 1)
            )
            hop2_task = tg.create_task(
                self._execute_single_hop(session, plan, 2)
            )

        context.add_hop_result(hop1_task.result())
        context.add_hop_result(hop2_task.result())

        # Check early stopping after parallel phase
        if context.overall_confidence >= target_confidence:
            return context

    # Phase 2: Sequential refinement (hops 3+)
    for hop_num in range(3, max_hops + 1):
        # Refine based on previous results
        refined_plan = await self._refine_plan(plan, context)
        hop_result = await self._execute_single_hop(session, refined_plan, hop_num)
        context.add_hop_result(hop_result)

        if context.overall_confidence >= target_confidence:
            break

    return context
```

**Design Decisions**:
- **Hops 1-2**: Parallel (independent exploration)
- **Hops 3+**: Sequential (depends on synthesis)
- **Budget Checking**: Per-hop enforcement
- **Early Stopping**: After each phase

**Expected Improvement**: 30-50% time reduction for standard/deep research

---

### 5. Implement Result Caching
**Problem**: Repeated searches waste API calls and time
**Files**:
- `src/aris/mcp/tavily_client.py` (search cache)
- `src/aris/core/deduplication_gate.py` (similarity cache)

**Search Result Cache**:
```python
# tavily_client.py
from functools import lru_cache
import hashlib

class TavilyClient:
    def __init__(self, ...):
        self._search_cache = {}  # {query_hash: (results, timestamp)}
        self._cache_ttl = 3600  # 1 hour

    async def search(self, query, ...):
        # Check cache
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash in self._search_cache:
            results, timestamp = self._search_cache[query_hash]
            if time.time() - timestamp < self._cache_ttl:
                logger.info(f"Cache hit for query: {query[:50]}")
                return results

        # Execute search
        results = await self._make_request("/search", payload)

        # Cache results
        self._search_cache[query_hash] = (results, time.time())

        return results
```

**Similarity Score Cache**:
```python
# deduplication_gate.py
@functools.lru_cache(maxsize=1000)
def _calculate_similarity_cached(
    content_hash: str,
    existing_hash: str,
    topics_tuple: tuple,
    existing_topics_tuple: tuple
) -> float:
    """Cached similarity calculation using content hashes."""
    # Convert hashes back to content (requires cache storage)
    # Calculate similarity as before
```

**Cache Invalidation**:
- Time-based: 1 hour TTL for searches
- Event-based: Clear on document updates
- Size-based: LRU eviction at 1000 entries

**Expected Improvement**: 70% reduction on repeated queries (common in iterative research)

---

## P2: Medium-Term Improvements

### 6. Database Connection Pooling
**Problem**: Single connection limits concurrency
**File**: `src/aris/storage/database.py`

**Current**:
```python
self.engine = create_engine(
    self.database_url,
    poolclass=StaticPool,  # Single connection
)
```

**Optimized**:
```python
from sqlalchemy.pool import QueuePool

self.engine = create_engine(
    self.database_url,
    poolclass=QueuePool,
    pool_size=5,           # Normal pool size
    max_overflow=10,       # Burst capacity
    pool_timeout=30,       # Connection wait timeout
    pool_recycle=3600,     # Refresh connections hourly
)
```

**Considerations**:
- SQLite limitations: Write serialization remains
- Better for read concurrency
- Consider PostgreSQL for production multi-user

**Expected Improvement**: Enables 5-10 concurrent read operations

---

### 7. Stream Large Document Processing
**Problem**: Full file reads cause memory spikes
**Files**: Multiple (deduplication_gate, document_finder)

**Current**:
```python
with open(doc_path, "r", encoding="utf-8") as f:
    doc_content = f.read()  # Full read into memory
```

**Optimized**:
```python
def read_document_chunked(file_path: Path, chunk_size: int = 4096):
    """Read document in chunks for memory efficiency."""
    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

# Usage for deduplication
chunks = []
for chunk in read_document_chunked(doc_path):
    chunks.append(chunk)
    if len(''.join(chunks)) >= 1000:  # First 1000 chars for embedding
        break
content_preview = ''.join(chunks)[:1000]
```

**Trade-offs**:
- Memory: Reduces from O(file_size) to O(chunk_size)
- Complexity: More complex processing logic
- Benefit: Significant for >1MB documents (rare in research use case)

**Expected Improvement**: 50% memory reduction for large documents

---

## P3: Long-Term Strategic Optimizations

### 8. Distributed Vector Store
**Problem**: ChromaDB limited to single-node scaling
**Recommendation**: Evaluate Qdrant or Weaviate

**Qdrant Implementation Sketch**:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class DistributedVectorStore:
    def __init__(self, url="http://localhost:6333"):
        self.client = QdrantClient(url)
        self.collection_name = "documents"

        # Initialize collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,  # Embedding dimension
                distance=Distance.COSINE
            )
        )

    async def add_document(self, doc_id, embedding, metadata):
        """Add document with vector."""
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload=metadata
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

    async def search_similar(self, query_embedding, limit=10):
        """Search for similar documents."""
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit
        )
        return [(r.id, r.score, r.payload) for r in results]
```

**Benefits**:
- Horizontal scaling (multiple nodes)
- Built-in replication
- Production-ready performance (100K+ documents)

**Migration Effort**: HIGH (40+ hours)

---

### 9. Query Plan Optimization
**Problem**: Potential inefficiencies in SQLAlchemy queries
**Approach**: Analyze and optimize

**Tools**:
```python
# Enable query logging
engine = create_engine(..., echo=True)

# Analyze query plans
with engine.connect() as conn:
    result = conn.execute(text("EXPLAIN QUERY PLAN SELECT ..."))
    print(result.fetchall())
```

**Common Optimizations**:
- Add composite indices: `CREATE INDEX idx_doc_status_confidence ON documents(status, confidence)`
- Eager loading: `.options(joinedload(Document.hops))`
- Query result caching: `@cached_property`

**Expected Improvement**: 20-40% reduction in complex query times

---

## Implementation Timeline

### Sprint 1 (Week 1): P0 Critical Fixes
- [ ] Ensure vector store initialization (Day 1)
- [ ] Design topic indexing schema (Day 2)
- [ ] Implement topic table migration (Day 3)
- [ ] Update document_finder queries (Day 4)
- [ ] Test and validate improvements (Day 5)

**Deliverables**:
- Vector store requirement enforced
- Topic searches 10x faster
- Performance regression tests added

---

### Sprint 2 (Week 2-3): P1 High-Impact
- [ ] Add end-to-end benchmarks (Week 2, Days 1-2)
- [ ] Implement hop parallelization (Week 2, Days 3-5)
- [ ] Add result caching (Week 3, Days 1-2)
- [ ] Validate performance improvements (Week 3, Days 3-5)

**Deliverables**:
- Benchmark suite covering all research depths
- 30-50% faster standard/deep research
- 70% cache hit rate on repeated queries

---

### Sprint 3 (Week 4): P2 Medium-Term
- [ ] Upgrade connection pooling (Week 4, Days 1-2)
- [ ] Implement streaming for large docs (Week 4, Days 3-5)

**Deliverables**:
- Support for concurrent operations
- Memory-efficient large document handling

---

### Future Sprints: P3 Strategic
- [ ] Evaluate Qdrant vs Weaviate (1 week research)
- [ ] Implement distributed vector store (2-3 weeks)
- [ ] Query plan optimization pass (1 week)

---

## Validation Strategy

### Performance Testing
1. **Baseline Measurement**
   - Run current benchmarks
   - Record execution times for quick/standard/deep
   - Document memory usage profiles

2. **Post-Optimization Measurement**
   - Run same benchmarks
   - Compare against baseline
   - Validate improvement targets met

3. **Regression Prevention**
   - Add CI performance gates
   - Alert on >10% performance degradation
   - Track performance metrics over time

### Success Metrics

| Metric | Current | Target (P0) | Target (P1) |
|--------|---------|-------------|-------------|
| Quick Research | 15-30s | 10-20s | 8-15s |
| Standard Research | 45-90s | 40-80s | 30-60s |
| Deep Research | 2-4min | 90-180s | 60-120s |
| Topic Search (100 docs) | 200ms | 20ms | 15ms |
| Deduplication (1000 docs) | 8min | 50ms | 30ms |
| Memory Usage (200KB doc) | ~5MB | ~3MB | ~2MB |

---

## Risk Assessment

### Low Risk
- Topic indexing (backward compatible migration)
- Result caching (transparent to users)
- Connection pooling (fallback to StaticPool)

### Medium Risk
- Hop parallelization (complex logic, early stopping)
- Streaming (changes processing patterns)

### High Risk
- Vector store requirement (breaking change)
- Distributed vector store (major architecture change)

**Mitigation**:
- Feature flags for new optimizations
- Gradual rollout with monitoring
- Rollback plan for each optimization

---

## Conclusion

This roadmap provides a **structured path** from current **MODERATE** performance to **FAST** performance suitable for production deployment at scale.

**Immediate Focus**: P0 items eliminate worst-case scenarios (O(n²) fallback, topic scan)

**High-Impact Focus**: P1 items provide measurable improvements (30-70% speedup)

**Strategic Focus**: P3 items enable enterprise-scale deployment (100K+ documents)

**Estimated Total Effort**:
- P0: 5 hours
- P1: 32 hours
- P2: 20 hours
- P3: 56+ hours
- **Total**: ~113 hours (14 work days)

**Expected Outcome**:
- Quick: 15-30s → **8-15s** (50% improvement)
- Standard: 45-90s → **30-60s** (40% improvement)
- Deep: 2-4min → **60-120s** (50% improvement)
- Scalability: 1K docs → **10K+ docs** (10x improvement)

---

**Roadmap Created**: 2025-11-14
**Based On**: Performance Profile Assessment
**Status**: Ready for Implementation
