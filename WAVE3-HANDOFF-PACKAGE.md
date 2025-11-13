# WAVE 3 HANDOFF PACKAGE - Semantic Deduplication

**From**: Wave 2 Validation
**To**: Wave 3 Implementation Team
**Date**: 2025-11-12
**Status**: READY FOR IMPLEMENTATION

---

## OVERVIEW

This document provides Wave 3 (Semantic Deduplication) with all necessary context, APIs, and integration points required to implement document deduplication and intelligent update workflows.

---

## WAVE 3 OBJECTIVES

### Primary Goal
Implement semantic similarity detection and intelligent document updates to prevent research duplication.

### Key Requirements
1. **Vector Embedding Integration**: Generate embeddings for research documents
2. **Similarity Detection**: Find semantically similar documents before creating new ones
3. **Intelligent Updates**: Update existing documents instead of creating duplicates
4. **Deduplication Pipeline**: End-to-end dedup workflow in research orchestrator

### Success Criteria
- Duplicate detection accuracy: 90%+ precision
- Processing time: <500ms per document
- Integration with Wave 2 workflow
- User control over deduplication (enable/disable)
- Documentation of dedup decisions

---

## WAVE 2 FOUNDATION - WHAT YOU INHERIT

### Fully Operational Components

#### 1. Tavily Web Search (TavilyClient)
**Location**: `src/aris/mcp/tavily_client.py`
**Status**: Production-ready
**Key Methods**:
```python
async def search(query: str) -> Dict[str, Any]
    """Search Tavily with results and rankings"""

async def extract(url: str) -> Dict[str, Any]
    """Extract content from URL"""

async def crawl(url: str, depth: int = 1) -> Dict[str, Any]
    """Crawl website with depth control"""

async def map(query: str) -> Dict[str, Any]
    """Map search results"""
```

**Cost Tracking**: $0.01 per operation
**Status**: Ready for production

#### 2. Sequential Reasoning Engine (SequentialClient)
**Location**: `src/aris/mcp/sequential_client.py`
**Status**: Production-ready
**Key Methods**:
```python
async def plan_research(query: str) -> ResearchPlan
    """Generate structured research plan with hypotheses"""

async def generate_hypotheses(context: str) -> List[Hypothesis]
    """Generate testable hypotheses"""

async def test_hypothesis(hypothesis: Hypothesis, evidence: List[str]) -> HypothesisResult
    """Test hypothesis against evidence"""

async def synthesize_findings(results: List[HypothesisResult]) -> Synthesis
    """Synthesize multi-source findings"""
```

**Status**: Ready for production

#### 3. Research Orchestrator (ResearchOrchestrator)
**Location**: `src/aris/core/research_orchestrator.py`
**Status**: Production-ready
**Key Methods**:
```python
async def execute_research(
    query: str,
    depth: str = "standard",
    max_cost: float = None,
    stream_progress: bool = True
) -> ResearchResult

async def get_session_status(session_id: str) -> Dict[str, Any]
    """Get current session status and progress"""
```

**Integration Points**:
- ProgressTracker for streaming updates
- SessionManager for persistence
- DocumentStore for storage

#### 4. Session Management
**Location**: `src/aris/storage/session_manager.py`
**Status**: Production-ready
**Key Methods**:
```python
def create_session(query: str, config: ArisConfig) -> ResearchSession
    """Create new research session"""

def get_session(session_id: str) -> ResearchSession
    """Retrieve session by ID"""

def list_sessions(status: str = None) -> List[ResearchSession]
    """List sessions with optional filtering"""

def update_session(session_id: str, **updates) -> ResearchSession
    """Update session metadata"""
```

#### 5. Document Storage
**Location**: `src/aris/storage/document_store.py`
**Status**: Partially ready (awaiting Wave 3)
**Key Methods**:
```python
def create_document(
    content: str,
    title: str,
    session_id: str,
    metadata: Dict[str, Any]
) -> str:
    """Create new research document
    Returns: document_id"""

def load_document(doc_id: str) -> ResearchDocument
    """Load document by ID"""

def update_document(
    doc_id: str,
    content: str,
    metadata: Dict[str, Any] = None
) -> ResearchDocument
    """Update existing document"""

def find_similar_documents(query: str) -> List[Tuple[str, float]]:
    """Find semantically similar documents
    Returns: [(doc_id, similarity_score), ...]
    NOTE: Implementation deferred to Wave 3"""
```

#### 6. Git Integration
**Location**: `src/aris/storage/git_manager.py`
**Status**: Production-ready
**Key Methods**:
```python
def commit_document(
    file_path: str,
    message: str,
    is_update: bool = False
) -> str:
    """Commit document to Git
    Returns: commit_hash"""

def get_document_history(doc_id: str) -> List[Dict[str, Any]]
    """Get document version history"""

def get_diff(doc_id: str, from_hash: str, to_hash: str) -> str
    """Get diff between versions"""
```

---

## CRITICAL APIS FOR WAVE 3 IMPLEMENTATION

### 1. DocumentStore API Extension (PRIMARY FOCUS)

#### Current Implementation
```python
class DocumentStore:
    def create_document(self, content: str, title: str, session_id: str, metadata: Dict) -> str
    def load_document(self, doc_id: str) -> ResearchDocument
    def update_document(self, doc_id: str, content: str, metadata: Dict) -> ResearchDocument
```

#### WAVE 3 REQUIREMENT: Implement find_similar_documents()

**Method Signature**:
```python
async def find_similar_documents(
    self,
    query: Union[str, List[float]],
    threshold: float = 0.85,
    limit: int = 10
) -> List[Tuple[str, float]]:
    """Find documents similar to query.

    Args:
        query: Either text query OR embedding vector
        threshold: Similarity threshold (0.0-1.0), default 0.85
        limit: Max results to return

    Returns:
        List of (document_id, similarity_score) tuples,
        sorted by similarity descending

    Example:
        # Find similar documents by text
        similar = await doc_store.find_similar_documents(
            query="machine learning algorithms",
            threshold=0.85
        )
        # Returns: [("doc_123", 0.92), ("doc_456", 0.87)]

        # Find by embedding vector
        embedding = embedding_model.encode(text)
        similar = await doc_store.find_similar_documents(
            query=embedding,
            threshold=0.85
        )
    """
```

**Implementation Requirements**:
1. Accept both text and embedding inputs
2. Generate embeddings for text inputs (using embedding model)
3. Query vector database for similarity
4. Filter by threshold
5. Return sorted by similarity
6. Cache embeddings for performance

---

### 2. Embedding Generation Service (NEW)

**Location**: `src/aris/core/embedding_service.py` (CREATE THIS)

**Interface**:
```python
class EmbeddingService:
    """Vector embedding generation service."""

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embed multiple texts"""

    def similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
```

**Options**:
- OpenAI embeddings-3-small (recommended)
- Cohere embeddings
- Local open-source (Hugging Face)

---

### 3. Vector Database Integration (NEW)

**Location**: `src/aris/storage/vector_store.py` (CREATE THIS)

**Interface**:
```python
class VectorStore:
    """Vector database for semantic search."""

    async def store_embedding(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store embedding with metadata"""

    async def search_similar(
        self,
        query_embedding: List[float],
        threshold: float = 0.85,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Search for similar embeddings"""

    async def delete_embedding(self, doc_id: str) -> None:
        """Remove embedding from vector store"""
```

**Recommended Database**:
- Chroma (already in dependencies)
- Config: Persistent storage in `{research_dir}/.chroma`

---

### 4. Deduplication Pipeline (NEW)

**Location**: `src/aris/core/deduplication_pipeline.py` (CREATE THIS)

**Interface**:
```python
class DeduplicationPipeline:
    """Intelligent document deduplication."""

    async def check_and_update(
        self,
        query: str,
        new_content: str,
        session_id: str,
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """Check for duplicates and update if found.

        Returns:
            {
                "action": "create" | "update",
                "document_id": str,
                "similar_document_id": str (if update),
                "similarity_score": float (if update),
                "previous_version": str (if update),
                "timestamp": datetime
            }
        """

    async def merge_findings(
        self,
        existing_doc_id: str,
        new_content: str,
        new_sources: List[Dict]
    ) -> str:
        """Intelligently merge findings into existing document."""
```

---

## INTEGRATION POINTS WITH RESEARCH ORCHESTRATOR

### Current Flow (Wave 2)
```
ResearchOrchestrator.execute_research()
    ├─ Plan research
    ├─ Multi-hop execution
    ├─ Synthesize findings
    └─ DocumentStore.create_document() → NEW DOCUMENT
    └─ GitManager.commit_document()
```

### Wave 3 Enhanced Flow (REQUIRED)
```
ResearchOrchestrator.execute_research()
    ├─ Plan research
    ├─ Multi-hop execution
    ├─ Synthesize findings
    ├─ NEW: DeduplicationPipeline.check_and_update()
    │       ├─ Find similar documents
    │       ├─ If similar (score > threshold):
    │       │   └─ Update existing document
    │       └─ If unique:
    │           └─ Create new document
    └─ GitManager.commit_document()
```

### Code Location to Modify
**File**: `src/aris/core/research_orchestrator.py`
**Method**: `_save_research_document()`

**Current Code** (approx line 328):
```python
def _save_research_document(
    self,
    query: str,
    findings: Synthesis,
    session: ResearchSession,
    hops_executed: int,
) -> None:
```

**Wave 3 Enhancement**:
```python
# BEFORE DocumentStore.create_document():
dedup_result = await self.deduplication_pipeline.check_and_update(
    query=query,
    new_content=formatted_findings,
    session_id=session.id,
    similarity_threshold=self.config.dedup_threshold
)

if dedup_result["action"] == "update":
    # Update existing document
    doc_id = dedup_result["document_id"]
    # Log the update action
    session.dedup_info = {
        "similar_document_id": dedup_result["similar_document_id"],
        "similarity_score": dedup_result["similarity_score"]
    }
else:
    # Create new document
    doc_id = await self.document_store.create_document(...)
```

---

## DATABASE SCHEMA EXTENSIONS

### Wave 2 Current Schema
```sql
ResearchSession:
    - id (PK)
    - query (TEXT)
    - status (VARCHAR)
    - created_at (DATETIME)
    - updated_at (DATETIME)
    - total_cost (FLOAT)
    - confidence (FLOAT)
```

### Wave 3 Required Extensions

#### Add to ResearchSession Table
```sql
ALTER TABLE research_session ADD COLUMN:
    - dedup_source_id (VARCHAR, FK to research_document)
    - similarity_score (FLOAT)
    - was_update (BOOLEAN)
    - merged_from_id (VARCHAR)
```

#### New Table: DocumentEmbedding
```sql
CREATE TABLE document_embedding:
    - id (PK)
    - document_id (FK)
    - embedding_vector (BLOB or VECTOR)
    - embedding_model (VARCHAR)
    - created_at (DATETIME)
    - UNIQUE(document_id)
```

#### New Table: DeduplicationRecord
```sql
CREATE TABLE deduplication_record:
    - id (PK)
    - source_session_id (FK)
    - target_document_id (FK)
    - similarity_score (FLOAT)
    - action_type (VARCHAR: 'create' | 'update')
    - merged_findings (TEXT)
    - created_at (DATETIME)
```

### Migration Strategy
Use Alembic to create new tables and schema changes:
1. Create `alembic/versions/003_add_deduplication.py`
2. Add DocumentEmbedding table
3. Add DeduplicationRecord table
4. Add columns to ResearchSession
5. Create indexes on document_id, similarity_score

---

## CONFIGURATION REQUIREMENTS

### Add to ArisConfig (src/aris/models/config.py)
```python
class ArisConfig(BaseSettings):
    # ... existing fields ...

    # Deduplication settings
    dedup_enabled: bool = True
    dedup_threshold: float = 0.85  # Similarity threshold
    dedup_strategy: str = "merge"  # "merge" or "update"

    # Embedding service settings
    embedding_provider: str = "openai"  # "openai", "cohere", "local"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Vector database settings
    vector_db_type: str = "chroma"  # "chroma" or "pinecone"
    vector_db_path: str = ".chroma"  # Relative to research_dir

    class Config:
        env_prefix = "ARIS_"
```

### Environment Variables to Support
```bash
# Embedding service
ARIS_EMBEDDING_PROVIDER=openai
ARIS_EMBEDDING_MODEL=text-embedding-3-small

# Deduplication
ARIS_DEDUP_ENABLED=true
ARIS_DEDUP_THRESHOLD=0.85

# Vector database
ARIS_VECTOR_DB_TYPE=chroma
ARIS_VECTOR_DB_PATH=.chroma
```

---

## STEP-BY-STEP IMPLEMENTATION GUIDE

### Phase 1: Foundation (Week 1)

#### Step 1.1: Create Embedding Service
- Create `src/aris/core/embedding_service.py`
- Implement OpenAI integration (or chosen provider)
- Add configuration for embedding model
- Add unit tests

#### Step 1.2: Create Vector Store
- Create `src/aris/storage/vector_store.py`
- Integrate Chroma (already in dependencies)
- Implement store_embedding(), search_similar()
- Add initialization logic
- Add unit tests

**Files to Create**:
- `src/aris/core/embedding_service.py`
- `src/aris/storage/vector_store.py`
- `tests/unit/test_embedding_service.py`
- `tests/unit/test_vector_store.py`

---

### Phase 2: Deduplication Logic (Week 2)

#### Step 2.1: Create Deduplication Pipeline
- Create `src/aris/core/deduplication_pipeline.py`
- Implement check_and_update()
- Implement merge_findings()
- Add similarity threshold logic
- Add comprehensive logging

#### Step 2.2: Extend DocumentStore
- Implement find_similar_documents()
- Add embedding generation on document creation
- Add similarity search interface
- Maintain backward compatibility

**Files to Modify**:
- `src/aris/storage/document_store.py` (add find_similar_documents)
- `src/aris/models/config.py` (add dedup config)

**Files to Create**:
- `src/aris/core/deduplication_pipeline.py`
- `tests/unit/test_deduplication_pipeline.py`

---

### Phase 3: Integration (Week 3)

#### Step 3.1: Integrate into ResearchOrchestrator
- Modify _save_research_document() to use deduplication
- Add dedup status to progress events
- Update session metadata with dedup info
- Add dedup logging

#### Step 3.2: Database Migrations
- Create Alembic migration for new tables
- Create migration for schema changes
- Test migration path

#### Step 3.3: Update CLI
- Add `--dedup-enabled/--dedup-disabled` flag
- Add `--dedup-threshold` option
- Display dedup results in progress output
- Update help text

**Files to Modify**:
- `src/aris/core/research_orchestrator.py` (_save_research_document)
- `src/aris/cli/research_commands.py` (add dedup flags)

**Files to Create**:
- `alembic/versions/003_add_deduplication.py`

---

### Phase 4: Testing & Polish (Week 4)

#### Step 4.1: Integration Tests
- Test end-to-end deduplication flow
- Test edge cases (similar, exact, dissimilar)
- Test update vs create decision
- Test with real Tavily results

#### Step 4.2: Performance Testing
- Benchmark embedding generation
- Benchmark similarity search
- Profile memory usage
- Optimize as needed

#### Step 4.3: Documentation
- Document deduplication workflow
- Document configuration options
- Document API changes
- Create user guide

**Files to Create**:
- `tests/integration/test_deduplication.py`
- `tests/integration/test_document_update.py`
- `docs/DEDUPLICATION.md`

---

## DATA FLOW DIAGRAMS

### New Research Document Flow
```
User Query: "What is quantum computing?"
    ↓
ResearchOrchestrator.execute_research()
    ├─ Generate embedding for query
    ├─ Search VectorStore for similar docs
    ├─ Find "what is quantum mechanics?" (score: 0.88)
    ├─ DeduplicationPipeline.check_and_update()
    │   ├─ Score > threshold (0.88 > 0.85) → UPDATE
    │   ├─ Get existing document content
    │   ├─ Merge new findings
    │   └─ Return update_action
    ├─ DocumentStore.update_document(doc_id)
    └─ GitManager.commit_document("Update quantum computing")
        ↓
    Updated Document in Git with new findings
    Session metadata shows: merged from doc_xyz, score: 0.88
```

### Unique Research Document Flow
```
User Query: "Latest GPT-5 architecture"
    ↓
ResearchOrchestrator.execute_research()
    ├─ Generate embedding for query
    ├─ Search VectorStore for similar docs
    ├─ No matches above threshold
    ├─ DeduplicationPipeline.check_and_update()
    │   └─ No duplicates → CREATE
    ├─ DocumentStore.create_document()
    │   ├─ Generate document
    │   ├─ Create embedding
    │   └─ Store in VectorStore
    └─ GitManager.commit_document("Add GPT-5 architecture")
        ↓
    New Document in Git
```

---

## TESTING STRATEGY FOR WAVE 3

### Unit Tests Required
1. **EmbeddingService**
   - Text embedding generation
   - Batch embedding
   - Similarity calculation
   - Error handling

2. **VectorStore**
   - Store embedding
   - Search by similarity
   - Delete embedding
   - Database operations

3. **DeduplicationPipeline**
   - Duplicate detection
   - Non-duplicate handling
   - Merge logic
   - Edge cases (threshold boundary, empty results)

### Integration Tests Required
1. **Full Deduplication Workflow**
   - Create document → search for similar → dedup decision
   - Update existing → merge findings
   - Create new → store embedding

2. **ResearchOrchestrator Integration**
   - Research execution with dedup
   - Session metadata tracking
   - Git commit with dedup info

### End-to-End Tests Required
1. **Multi-hop with Deduplication**
   - Execute research that finds existing doc
   - Verify document updated instead of created
   - Check Git history shows updates

2. **Edge Cases**
   - Very similar documents (0.99 similarity)
   - Borderline cases (exactly at threshold)
   - Multiple similar documents (take best match)

---

## PERFORMANCE TARGETS

### Latency Targets
- Embedding generation: <200ms per document
- Similarity search: <100ms
- Dedup decision: <50ms
- Total dedup overhead: <500ms per research

### Throughput Targets
- Batch embeddings: >10 documents/sec
- Similarity searches: >50 queries/sec

### Resource Targets
- Memory per embedding: ~6KB (1536 dims × 4 bytes)
- Disk per document: ~10KB (embedding + metadata)
- Chroma index: <1GB for 10k documents

---

## MONITORING & OBSERVABILITY

### Metrics to Track
```python
# In progress events and logs:
{
    "event": "deduplication_check",
    "query": str,
    "similar_docs_found": int,
    "top_similarity_score": float,
    "action_taken": "create" | "update",
    "processing_time_ms": float,
    "timestamp": datetime
}
```

### Logging Points
1. Embedding generation start/complete
2. Vector search execution
3. Similarity scores for top results
4. Dedup decision and rationale
5. Document merge/update execution

### Dashboard Metrics
- Dedup rate (updates vs creates)
- Average similarity scores
- Duplicate detection accuracy
- Processing time percentiles

---

## ERROR HANDLING & FALLBACK STRATEGIES

### Embedding Service Errors
```python
try:
    embedding = await embedding_service.embed_text(text)
except EmbeddingServiceError:
    # Fallback: Skip dedup, create new document
    logger.warning(f"Embedding failed, creating new document")
    dedup_result = {"action": "create"}
```

### Vector Store Errors
```python
try:
    similar = await vector_store.search_similar(embedding)
except VectorStoreError:
    # Fallback: Skip similarity search
    similar = []
```

### Network/API Errors
- Retry with exponential backoff
- Log failure for monitoring
- Continue with fallback behavior
- No user-facing failures

---

## BACKWARD COMPATIBILITY

### Wave 2 Compatibility (CRITICAL)
- All existing documents remain accessible
- Old documents without embeddings are handled gracefully
- Dedup can be disabled entirely
- Config is backward compatible

### Migration Strategy
1. Existing documents remain unchanged
2. When first accessed, generate embeddings on-demand
3. Lazy embedding generation for backward compatibility
4. No data loss or schema breaking changes

---

## SECURITY CONSIDERATIONS

### Embedding Privacy
- Embeddings stored locally (Chroma)
- No embeddings sent to external services (if using local model)
- If using OpenAI embeddings: data is NOT retained per OpenAI policy

### Vector Database Security
- Chroma database in research directory
- Includes in .gitignore (vectors not versioned)
- Access control via filesystem permissions
- No network exposure

### Configuration Security
- API keys for embedding service via keyring
- Environment variables for non-sensitive config
- No keys in Git or logs

---

## WAVE 3 COMPLETION CHECKLIST

### Code Implementation
- [ ] EmbeddingService class created and tested
- [ ] VectorStore class created and tested
- [ ] DeduplicationPipeline class created and tested
- [ ] DocumentStore.find_similar_documents() implemented
- [ ] ResearchOrchestrator integration complete
- [ ] CLI flags added for dedup control
- [ ] Database migrations created
- [ ] All type hints in place
- [ ] Error handling comprehensive

### Testing
- [ ] Unit tests: EmbeddingService (8+ tests)
- [ ] Unit tests: VectorStore (10+ tests)
- [ ] Unit tests: DeduplicationPipeline (12+ tests)
- [ ] Integration tests: Full workflow (6+ tests)
- [ ] E2E tests: Research with dedup (4+ tests)
- [ ] Edge case coverage: 95%+

### Documentation
- [ ] API documentation complete
- [ ] User guide for dedup features
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Performance tuning guide

### Quality Standards
- [ ] Black formatting: 100%
- [ ] Ruff linting: 0 errors
- [ ] mypy strict mode: 0 errors
- [ ] Docstrings: 100% coverage
- [ ] Test coverage: 85%+

### Security Review
- [ ] No credentials in code
- [ ] No sensitive data in logs
- [ ] Input validation complete
- [ ] SQL injection prevention verified
- [ ] Error messages sanitized

### Performance
- [ ] Embedding latency: <200ms
- [ ] Search latency: <100ms
- [ ] Total dedup overhead: <500ms
- [ ] Memory usage: Reasonable
- [ ] Database indexes optimized

---

## RESOURCE REQUIREMENTS

### Team
- 1-2 Python engineers (4 weeks)
- Code review (ongoing)
- QA testing (1 week)

### Dependencies
- All in `pyproject.toml` already
- Chroma 0.4.18+ (installed)
- OpenAI API key (if using OpenAI embeddings)

### Infrastructure
- None (local Chroma database)
- Optional: Vector DB service (for future scale)

---

## KNOWN RISKS & MITIGATION

### Risk 1: Embedding Quality
**Risk**: Poor embeddings lead to bad dedup decisions
**Mitigation**:
- Configurable threshold
- User can disable dedup
- Monitor dedup accuracy metrics
- Test with multiple embedding models

### Risk 2: Performance Impact
**Risk**: Embedding/search adds latency
**Mitigation**:
- Async operations throughout
- Caching of embeddings
- Batch operations where possible
- Performance targets defined

### Risk 3: Vector DB Size
**Risk**: Vector database grows with documents
**Mitigation**:
- Delete embeddings with documents
- Regular cleanup jobs
- Monitor disk usage
- Archive old embeddings

---

## NEXT PHASE: WAVE 4+ OPPORTUNITIES

### Potential Enhancements
1. **Multi-language Support**: Embeddings in multiple languages
2. **Custom Embedding Models**: Fine-tune on domain-specific text
3. **Cross-document Linking**: Link related documents
4. **Document Clustering**: Automatic document grouping
5. **Collaborative Deduplication**: User feedback on dedup decisions
6. **Hierarchical Deduplication**: Dedup within topics
7. **Vector DB Scaling**: Pinecone or Qdrant for large scale

---

## APPENDIX: CODE TEMPLATES

### Template 1: EmbeddingService Interface
```python
# src/aris/core/embedding_service.py

from abc import ABC, abstractmethod
from typing import List, Union
from pydantic import BaseModel

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    text: str
    embedding: List[float]

class EmbeddingService(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embed texts."""
        pass

    @staticmethod
    def similarity(emb1: List[float], emb2: List[float]) -> float:
        """Cosine similarity between embeddings."""
        # Implementation: use numpy or scipy
        pass

class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI embeddings provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model

    async def embed_text(self, text: str) -> List[float]:
        # Call OpenAI API
        pass

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Batch call OpenAI API
        pass
```

### Template 2: VectorStore Interface
```python
# src/aris/storage/vector_store.py

from typing import List, Tuple, Dict, Any
from pathlib import Path

class VectorStore:
    """Vector database for semantic search."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        # Initialize Chroma client

    async def store_embedding(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store embedding with metadata."""
        # Store in Chroma

    async def search_similar(
        self,
        query_embedding: List[float],
        threshold: float = 0.85,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Search for similar embeddings.

        Returns:
            [(doc_id, similarity_score), ...]
        """
        # Query Chroma

    async def delete_embedding(self, doc_id: str) -> None:
        """Remove embedding."""
        # Delete from Chroma
```

### Template 3: DeduplicationPipeline Interface
```python
# src/aris/core/deduplication_pipeline.py

from typing import Dict, Any
from datetime import datetime

class DeduplicationResult(BaseModel):
    action: str  # "create" or "update"
    document_id: str
    similar_document_id: str = None
    similarity_score: float = None
    previous_version: str = None
    timestamp: datetime

class DeduplicationPipeline:
    """Intelligent deduplication."""

    async def check_and_update(
        self,
        query: str,
        new_content: str,
        session_id: str,
        similarity_threshold: float = 0.85
    ) -> DeduplicationResult:
        """Check for duplicates and decide action.

        Returns:
            DeduplicationResult with action and details
        """
        # 1. Generate embedding for query
        # 2. Search for similar documents
        # 3. Decide: create or update
        # 4. Return result

    async def merge_findings(
        self,
        existing_doc_id: str,
        new_content: str,
        new_sources: List[Dict]
    ) -> str:
        """Merge findings intelligently.

        Returns:
            Updated document ID
        """
        # 1. Load existing document
        # 2. Merge content
        # 3. Update sources
        # 4. Return updated doc
```

---

## CONCLUSION

Wave 3 is now fully specced and ready for implementation. All integration points are documented, APIs are defined, and a clear 4-week implementation path has been provided. The Wave 2 foundation is solid and production-ready for Wave 3 to build upon.

**Status**: READY FOR IMPLEMENTATION ✓
**Estimated Timeline**: 4 weeks
**Team Required**: 1-2 engineers
**Complexity**: Moderate (well-defined scope)

---

**Prepared By**: Wave 2 Validation Team
**For**: Wave 3 Implementation Team
**Date**: 2025-11-12
**Next Review**: Upon Wave 3 completion
