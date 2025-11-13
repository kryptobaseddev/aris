# ARIS Architectural Blueprint
**Autonomous Research Intelligence System - Complete Technical Design**

Generated: 2025-11-12
Version: 1.0.0

---

## Executive Summary

ARIS is a multi-agent research orchestration system designed to solve document proliferation and hallucination problems through consensus-based validation, semantic deduplication, and document-as-database architecture. Built as Python CLI tools optimized for LLM agent consumption.

**Key Differentiators**:
- Update existing documents, never create duplicates
- Multi-model consensus validation prevents hallucinations
- DAG-based task queue with dependency resolution
- State-driven workflow (SQLite → PostgreSQL migration path)
- Modular CLI scripts that coordinate via message bus
- LLM-friendly structured output formats

---

## 1. System Architecture Overview

### 1.1 Architectural Principles

**Reliability**:
- Consensus-based validation (3+ model agreement)
- Transactional state updates with rollback capability
- Circuit breakers for external API failures
- Comprehensive audit trails with provenance tracking

**Data Integrity**:
- Document versioning with Git-like diffs
- Atomic claim validation before persistence
- Conflict detection and resolution protocols
- Source authentication and authority scoring

**Performance**:
- Async-first with asyncio event loop
- Connection pooling for database and HTTP
- Semantic caching with vector embeddings
- Parallel task execution via DAG scheduler

**Security**:
- API key rotation and secure storage (keyring)
- Rate limiting for external APIs
- Input sanitization for all user queries
- Audit logging for all state mutations

### 1.2 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│  aris-research | aris-validate | aris-status | aris-export │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Orchestrator Core                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Query Parser │→ │ Task Planner │→ │ DAG Scheduler│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Agent Layer                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │Coordinator │  │ Researcher │  │  Validator │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │Synthesizer │  │ Challenger │  │  Archivist │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 Integration Layer                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │Context7 MCP│  │Tavily MCP  │  │Sequential  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │Serena MCP  │  │Playwright  │  │A2A Protocol│           │
│  └────────────┘  └────────────┘  └────────────┘           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 Persistence Layer                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │State DB    │  │Vector Store│  │Knowledge   │           │
│  │(SQLite/PG) │  │(Chroma)    │  │Graph(Neo4j)│           │
│  └────────────┘  └────────────┘  └────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Module Breakdown and Responsibilities

### 2.1 Core Modules

#### **aris_orchestrator** (core/orchestrator.py)
**Responsibility**: Main coordination hub, CLI entry point, task lifecycle management

**Key Functions**:
- Parse user queries and route to appropriate agents
- Initialize system state and restore from persistence
- Coordinate multi-agent workflows via A2A protocol
- Manage task queue lifecycle (create, monitor, complete)
- Handle graceful shutdown and state checkpointing

**Dependencies**:
- `state_manager`: Load/save system state
- `task_queue`: DAG-based task distribution
- `consensus`: Validation orchestration
- All agent modules for delegation

**API Signature**:
```python
class Orchestrator:
    async def execute_research(
        self,
        query: str,
        mode: ResearchMode = ResearchMode.UPDATE
    ) -> ResearchResult:
        """
        Main entry point for research operations.

        Args:
            query: User research question
            mode: UPDATE (default) or CREATE_NEW

        Returns:
            ResearchResult with task_id, status, document_path
        """
```

**Error Handling**:
- Circuit breaker for cascading agent failures
- Automatic retry with exponential backoff
- State rollback on transaction failures
- Comprehensive error logging with trace IDs

---

#### **state_manager** (core/state_manager.py)
**Responsibility**: ACID-compliant state persistence and recovery

**Key Functions**:
- Initialize database schema (SQLite development, PostgreSQL production)
- CRUD operations for topics, claims, sources, conflicts
- Transactional state updates with rollback
- State snapshot and restoration for checkpointing
- Database migration management (Alembic)

**Database Schema** (Complete):
```sql
-- Topics: Research entities
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    query_embedding VECTOR(1536),  -- For semantic search
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    state TEXT CHECK(state IN (
        'draft', 'researching', 'validating',
        'synthesizing', 'reviewed', 'published'
    )),
    confidence FLOAT CHECK(confidence BETWEEN 0.0 AND 1.0),
    version INTEGER DEFAULT 1,
    document_path TEXT NOT NULL UNIQUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Claims: Atomic facts with provenance
CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    claim_type TEXT CHECK(claim_type IN (
        'fact', 'opinion', 'statistic', 'definition'
    )),
    confidence FLOAT CHECK(confidence BETWEEN 0.0 AND 1.0),
    validated_at TIMESTAMP,
    validation_method TEXT,  -- consensus, manual, single_source
    created_at TIMESTAMP DEFAULT NOW(),
    invalidated_at TIMESTAMP,  -- Soft delete for history
    section_anchor TEXT  -- Where in document this appears
);

-- Sources: Provenance tracking
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    title TEXT,
    author TEXT,
    published_at TIMESTAMP,
    retrieved_at TIMESTAMP DEFAULT NOW(),
    authority_score FLOAT CHECK(authority_score BETWEEN 0.0 AND 1.0),
    content_hash TEXT NOT NULL,  -- Detect source changes
    source_type TEXT CHECK(source_type IN (
        'academic', 'documentation', 'news',
        'blog', 'forum', 'social', 'other'
    )),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Claim-Source relationships (many-to-many)
CREATE TABLE claim_sources (
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    relevance_score FLOAT CHECK(relevance_score BETWEEN 0.0 AND 1.0),
    quote_text TEXT,  -- Exact quote supporting claim
    PRIMARY KEY (claim_id, source_id)
);

-- Conflicts: Track disagreements between claims
CREATE TABLE conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_a UUID REFERENCES claims(id),
    claim_b UUID REFERENCES claims(id),
    conflict_type TEXT CHECK(conflict_type IN (
        'contradiction', 'temporal', 'scope', 'interpretation'
    )),
    severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    detected_at TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolution TEXT,
    resolved_by TEXT,  -- human, consensus, or agent_id
    resolved_at TIMESTAMP
);

-- Tasks: DAG task queue
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES tasks(id),  -- For subtasks
    agent_type TEXT NOT NULL,  -- Which agent handles this
    task_spec JSONB NOT NULL,  -- Task-specific parameters
    status TEXT CHECK(status IN (
        'pending', 'running', 'completed', 'failed', 'cancelled'
    )),
    priority INTEGER DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSONB,  -- Task output
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Task dependencies for DAG
CREATE TABLE task_dependencies (
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, depends_on_task_id),
    CHECK (task_id != depends_on_task_id)  -- Prevent self-dependency
);

-- Validation logs: Consensus tracking
CREATE TABLE validation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,  -- claude-4, gpt-4, gemini-pro
    agrees BOOLEAN NOT NULL,
    confidence FLOAT,
    reasoning TEXT,
    validated_at TIMESTAMP DEFAULT NOW()
);

-- Document versions: Git-like history
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    diff_from_previous TEXT,  -- Unified diff format
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT,  -- agent or human
    commit_message TEXT
);

-- Indexes for performance
CREATE INDEX idx_topics_embedding ON topics USING ivfflat (query_embedding vector_cosine_ops);
CREATE INDEX idx_claims_topic ON claims(topic_id);
CREATE INDEX idx_claims_confidence ON claims(confidence DESC);
CREATE INDEX idx_sources_url ON sources(url);
CREATE INDEX idx_tasks_status ON tasks(status, priority DESC);
CREATE INDEX idx_task_deps_waiting ON task_dependencies(depends_on_task_id);
```

**Migration Strategy**:
- Start with SQLite for development/single-user
- PostgreSQL migration path via Alembic
- Preserve all data during migration
- Vector extension (pgvector) for embeddings

---

#### **task_queue** (core/task_queue.py)
**Responsibility**: DAG-based task scheduling with dependency resolution

**Key Functions**:
- Create task graphs with dependencies
- Topological sort for execution order
- Parallel execution of independent tasks
- Retry logic with exponential backoff
- Task result propagation to dependent tasks
- Deadlock detection and prevention

**Task Lifecycle**:
```
pending → running → completed
            ↓
         failed → retry → running
                    ↓
                 cancelled
```

**API Signature**:
```python
class TaskQueue:
    async def submit_task(
        self,
        agent_type: AgentType,
        task_spec: Dict[str, Any],
        depends_on: List[UUID] = None,
        priority: int = 5
    ) -> UUID:
        """Submit task to queue with optional dependencies."""

    async def execute_dag(
        self,
        root_task_id: UUID,
        max_parallel: int = 5
    ) -> Dict[UUID, TaskResult]:
        """Execute task DAG with parallelism."""

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks whose dependencies are met."""
```

**Dependency Resolution Algorithm**:
```python
def topological_sort(tasks: List[Task]) -> List[List[Task]]:
    """
    Returns task execution levels:
    Level 0: No dependencies (run first)
    Level 1: Depends only on Level 0
    Level N: Depends on tasks in Level < N

    Tasks within same level can run in parallel.
    """
```

---

#### **consensus** (core/consensus.py)
**Responsibility**: Multi-model validation and hallucination prevention

**Key Functions**:
- Query multiple LLM providers for claim validation
- Calculate consensus scores (% agreement)
- Handle disagreements with explanation requests
- Track validation provenance in database
- Flag low-confidence claims for human review

**Validation Algorithm**:
```python
class ConsensusValidator:
    MODELS = [
        ("anthropic", "claude-sonnet-4-5"),
        ("openai", "gpt-4-turbo"),
        ("google", "gemini-1.5-pro")
    ]

    async def validate_claim(
        self,
        claim: str,
        sources: List[Source]
    ) -> ValidationResult:
        """
        Multi-model validation pipeline:
        1. Format validation prompt with claim and sources
        2. Query all models in parallel
        3. Parse responses (agree/disagree + confidence)
        4. Calculate consensus score
        5. If < threshold, request explanations
        6. Store validation logs in database
        7. Return result with approval decision
        """
```

**Consensus Thresholds**:
- **0.0-0.5**: Rejected (majority disagree)
- **0.5-0.7**: Low confidence (flag for human review)
- **0.7-0.9**: Accepted (good consensus)
- **0.9-1.0**: High confidence (unanimous agreement)

**Cost Optimization**:
- Cache validation results by (claim_hash, sources_hash)
- Use cheaper models for initial screening
- Invoke expensive models only for disagreements
- Batch validation requests where possible

---

### 2.2 Agent Modules

#### **coordinator** (agents/coordinator.py)
**Responsibility**: Query decomposition and research planning

**Key Functions**:
- Parse natural language queries
- Decompose into atomic sub-questions
- Check existing knowledge base for similar topics
- Decide CREATE_NEW vs UPDATE_EXISTING mode
- Create initial task DAG for research plan

**Semantic Deduplication**:
```python
async def find_existing_topic(query: str) -> Optional[Topic]:
    """
    1. Generate embedding for query
    2. Vector similarity search in topics table
    3. If cosine_similarity > 0.85, return existing
    4. Otherwise return None (new topic)
    """
```

**Query Decomposition Strategy**:
```python
def decompose_query(query: str) -> List[SubQuery]:
    """
    Examples:
    "How do escape rooms handle payments offline?"
    →
    [
        "What is offline-first architecture?",
        "Which escape room booking systems exist?",
        "How do payment processors handle offline mode?",
        "What are sync conflict resolution strategies?"
    ]
    """
```

---

#### **researcher** (agents/researcher.py)
**Responsibility**: Information gathering from external sources

**Key Functions**:
- Execute web searches via Tavily MCP
- Fetch technical documentation via Context7 MCP
- Scrape web pages via Playwright MCP
- Extract structured data from unstructured sources
- Store sources in database with authority scoring

**Source Authority Scoring**:
```python
def calculate_authority_score(source: Source) -> float:
    """
    Scoring factors:
    - Domain reputation (academic > documentation > blog)
    - Author credentials (if available)
    - Publication recency
    - Citation count (if academic)
    - HTTPS vs HTTP

    Returns: 0.0-1.0 score
    """
```

**MCP Integration Pattern**:
```python
class ResearchAgent:
    async def research_subtopic(self, query: str) -> List[Finding]:
        # Parallel execution of all search strategies
        results = await asyncio.gather(
            self.tavily_search(query),
            self.context7_lookup(query),
            self.web_scrape_targets(query),
            return_exceptions=True
        )

        # Filter out failures, combine successes
        findings = [r for r in results if not isinstance(r, Exception)]
        return self.deduplicate_findings(findings)
```

---

#### **validator** (agents/validator.py)
**Responsibility**: Fact-checking and cross-referencing claims

**Key Functions**:
- Extract claims from research findings
- Cross-reference claims against sources
- Invoke consensus validator for each claim
- Detect contradictions between claims
- Store validation results in database

**Claim Extraction**:
```python
async def extract_claims(text: str, sources: List[Source]) -> List[Claim]:
    """
    Use LLM to extract atomic factual claims from text.
    Each claim must be:
    - Verifiable
    - Attributed to source(s)
    - Self-contained (no dangling references)
    """
```

**Contradiction Detection**:
```python
async def detect_contradictions(
    new_claims: List[Claim],
    existing_claims: List[Claim]
) -> List[Conflict]:
    """
    1. For each new claim, embed it
    2. Find semantically similar existing claims
    3. Use LLM to determine if they contradict
    4. If yes, create conflict record with severity
    """
```

---

#### **synthesizer** (agents/synthesizer.py)
**Responsibility**: Document generation and updating

**Key Functions**:
- Generate markdown documents from validated claims
- Update existing documents (not create duplicates)
- Preserve structure and non-factual content
- Create unified diffs showing changes
- Version documents in database

**Document Update Strategy**:
```python
async def update_document(
    topic: Topic,
    new_claims: List[Claim],
    existing_doc: str
) -> DocumentUpdate:
    """
    1. Parse existing document structure
    2. Map new claims to appropriate sections
    3. Generate updated content for each section
    4. Preserve unchanged sections verbatim
    5. Create unified diff
    6. Store new version in database
    7. Update document file on disk
    """
```

**Section Mapping Algorithm**:
```python
def map_claim_to_section(
    claim: Claim,
    sections: List[Section]
) -> Section:
    """
    Use semantic similarity to find best section:
    - Embed claim content
    - Embed section headers + first paragraph
    - Return highest similarity match
    - If no good match, create new section
    """
```

---

#### **challenger** (agents/challenger.py)
**Responsibility**: Critical analysis and bias detection

**Key Functions**:
- Identify logical gaps in research
- Detect potential biases in sources
- Suggest counter-arguments
- Find missing perspectives
- Recommend additional research areas

**Logical Gap Detection**:
```python
async def find_gaps(topic: Topic, claims: List[Claim]) -> List[Gap]:
    """
    Use LLM to analyze research completeness:
    - Are key stakeholder perspectives included?
    - Are alternative explanations considered?
    - Are temporal/geographic limitations acknowledged?
    - Are cost/benefit trade-offs discussed?
    """
```

---

#### **archivist** (agents/archivist.py)
**Responsibility**: Cataloging, indexing, and knowledge graph maintenance

**Key Functions**:
- Index all documents for semantic search
- Build knowledge graph of topic relationships
- Deduplicate redundant sources
- Archive old document versions
- Generate topic taxonomy

**Knowledge Graph Structure**:
```python
# Neo4j schema
CREATE (t:Topic {id, title, confidence})
CREATE (c:Claim {id, content, confidence})
CREATE (s:Source {id, url, authority})

CREATE (t)-[:CONTAINS]->(c)
CREATE (c)-[:SUPPORTED_BY]->(s)
CREATE (c)-[:CONTRADICTS]->(c2:Claim)
CREATE (t)-[:RELATED_TO]->(t2:Topic)
```

---

### 2.3 Integration Modules

#### **mcp_client** (integrations/mcp_client.py)
**Responsibility**: Generic MCP server communication

**Key Functions**:
- Initialize MCP connections
- Route tool calls to appropriate servers
- Handle connection failures and retries
- Implement circuit breaker pattern

**Connection Management**:
```python
class MCPClient:
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    async def connect_server(self, server_name: str, config: Dict):
        """Establish connection with health check."""

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        **kwargs
    ) -> Any:
        """Route call through circuit breaker."""
```

---

#### **context7_client** (integrations/context7_client.py)
**Responsibility**: Context7 MCP wrapper for technical documentation

**API Methods**:
```python
async def search_documentation(
    library: str,
    query: str,
    version: Optional[str] = None
) -> List[DocResult]:
    """Search technical documentation."""

async def get_code_examples(
    library: str,
    topic: str
) -> List[CodeExample]:
    """Get implementation examples."""
```

---

#### **tavily_client** (integrations/tavily_client.py)
**Responsibility**: Tavily MCP wrapper for web search

**API Methods**:
```python
async def web_search(
    query: str,
    search_depth: str = "advanced",
    max_results: int = 10,
    include_domains: List[str] = None,
    exclude_domains: List[str] = None
) -> List[SearchResult]:
    """Execute web search with filtering."""

async def extract_content(url: str) -> str:
    """Extract clean text from URL."""
```

---

#### **a2a_protocol** (integrations/a2a_protocol.py)
**Responsibility**: Agent-to-Agent communication protocol

**Message Format**:
```python
@dataclass
class A2AMessage:
    protocol_version: str = "a2a-v1"
    message_id: UUID = field(default_factory=uuid4)
    from_agent: str
    to_agent: str
    message_type: str  # task, result, error, query
    payload: Dict[str, Any]
    trace_id: UUID
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 5

    def to_json(self) -> str:
        """Serialize to JSON for transport."""

    @classmethod
    def from_json(cls, data: str) -> "A2AMessage":
        """Deserialize from JSON."""
```

**Message Bus**:
```python
class MessageBus:
    """
    In-process message bus for agent communication.
    Future: Replace with RabbitMQ/Redis for distributed agents.
    """
    async def publish(self, message: A2AMessage):
        """Publish message to topic."""

    async def subscribe(
        self,
        agent_id: str,
        callback: Callable
    ):
        """Subscribe to messages for agent."""
```

---

### 2.4 Knowledge Modules

#### **graph_db** (knowledge/graph_db.py)
**Responsibility**: Knowledge graph management (Neo4j)

**Key Functions**:
```python
async def create_topic_node(topic: Topic) -> str:
    """Create topic node in graph."""

async def link_claims(
    topic_id: str,
    claims: List[Claim]
) -> None:
    """Create CONTAINS relationships."""

async def find_related_topics(
    topic_id: str,
    depth: int = 2
) -> List[Topic]:
    """Graph traversal for related topics."""
```

---

#### **vector_store** (knowledge/vector_store.py)
**Responsibility**: Embedding storage and semantic search (ChromaDB)

**Key Functions**:
```python
async def add_documents(
    documents: List[str],
    metadata: List[Dict]
) -> List[str]:
    """Add documents with embeddings."""

async def semantic_search(
    query: str,
    n_results: int = 5,
    filter: Dict = None
) -> List[Result]:
    """Find semantically similar documents."""
```

---

#### **provenance** (knowledge/provenance.py)
**Responsibility**: Source tracking and citation management

**Key Functions**:
```python
def generate_citations(
    claims: List[Claim],
    format: str = "apa"
) -> List[str]:
    """Generate formatted citations."""

def build_provenance_chain(
    claim: Claim
) -> ProvenanceChain:
    """Trace claim back to original sources."""
```

---

### 2.5 Output Modules

#### **renderer** (output/renderer.py)
**Responsibility**: Generate human-readable reports

**Output Formats**:
- Markdown (default)
- HTML (with CSS styling)
- PDF (via pandoc)
- JSON (for programmatic access)

**Template Structure**:
```markdown
# {topic.title}

**Confidence**: {topic.confidence} | **Last Updated**: {topic.updated_at}

## Executive Summary
{generated_summary}

## Detailed Findings

### {section.title}
{claim.content} [^{source_id}]

## Sources
[^{source_id}]: {source.citation}

## Change Log
- {version.created_at}: {version.commit_message}
```

---

#### **differ** (output/differ.py)
**Responsibility**: Show document evolution

**Key Functions**:
```python
def generate_diff(
    version_a: DocumentVersion,
    version_b: DocumentVersion,
    format: str = "unified"
) -> str:
    """Generate unified diff between versions."""

def highlight_changes(
    old_content: str,
    new_content: str
) -> str:
    """HTML with highlighted additions/deletions."""
```

---

## 3. Data Flow Architecture

### 3.1 Complete Research Workflow

```
1. USER INPUT
   ↓
   aris research "How do booking systems handle offline mode?"
   ↓
2. ORCHESTRATOR
   ├─ Parse query
   ├─ Check system state
   └─ Route to Coordinator Agent
   ↓
3. COORDINATOR AGENT
   ├─ Generate query embedding
   ├─ Semantic search for existing topics
   ├─ IF FOUND: Set mode=UPDATE, load existing document
   ├─ IF NOT: Set mode=CREATE, initialize new topic
   ├─ Decompose query into sub-questions
   ├─ Create task DAG
   └─ Submit tasks to queue
   ↓
4. TASK QUEUE
   ├─ Topological sort of tasks
   ├─ Execute level 0 tasks (no dependencies) in parallel
   └─ Propagate results to dependent tasks
   ↓
5. RESEARCHER AGENT (Multiple instances in parallel)
   ├─ Execute subtask query
   ├─ Call MCP tools:
   │  ├─ Tavily: Web search
   │  ├─ Context7: Technical docs
   │  └─ Playwright: Web scraping
   ├─ Extract raw findings
   ├─ Store sources in database
   └─ Return findings to queue
   ↓
6. VALIDATOR AGENT
   ├─ Receive all findings from researchers
   ├─ Extract atomic claims from text
   ├─ FOR EACH CLAIM:
   │  ├─ Format validation prompt
   │  ├─ Query consensus validator
   │  ├─ Store validation logs
   │  └─ Accept/reject based on threshold
   ├─ Detect contradictions with existing claims
   ├─ Create conflict records if needed
   └─ Return validated claims
   ↓
7. CHALLENGER AGENT
   ├─ Analyze validated claims
   ├─ Identify logical gaps
   ├─ Suggest missing perspectives
   ├─ Detect potential biases
   └─ Return recommendations
   ↓
8. SYNTHESIZER AGENT
   ├─ Receive validated claims + challenges
   ├─ Load existing document (if UPDATE mode)
   ├─ Map claims to sections
   ├─ Generate/update content
   ├─ Preserve unchanged sections
   ├─ Create unified diff
   ├─ Store new document version
   └─ Write file to disk
   ↓
9. ARCHIVIST AGENT
   ├─ Index new/updated document
   ├─ Update knowledge graph
   ├─ Store vector embeddings
   └─ Generate topic taxonomy
   ↓
10. ORCHESTRATOR
    ├─ Collect all results
    ├─ Update topic state → 'published'
    ├─ Generate CLI output
    └─ Return to user
    ↓
11. CLI OUTPUT (Structured)
    {
      "task_id": "uuid",
      "status": "completed",
      "topic_id": "uuid",
      "document_path": "research/booking-offline.md",
      "confidence": 0.91,
      "changes": {
        "added": 347,
        "removed": 89,
        "modified": 12
      },
      "validation": {
        "claims_validated": 42,
        "consensus_score": 0.91
      },
      "next_actions": [
        "Review 3 flagged conflicts",
        "Challenge analysis suggests missing cost comparison"
      ]
    }
```

---

## 4. State Management Strategy

### 4.1 State Transitions

**Topic State Machine**:
```
draft → researching → validating → synthesizing → reviewed → published
  ↑                                                              ↓
  └─────────────────── (challenge) ─────────────────────────────┘
```

**State Validation Gates**:
- **researching → validating**: Minimum 3 sources gathered
- **validating → synthesizing**: Consensus threshold met (>0.7)
- **synthesizing → reviewed**: Document diff generated
- **reviewed → published**: Human approval (optional) or auto-approve if confidence >0.9

### 4.2 Transactional Guarantees

**Database Transactions**:
```python
async with state_manager.transaction() as tx:
    # All operations succeed or all rollback
    await tx.create_topic(topic)
    await tx.add_claims(claims)
    await tx.link_sources(claim_sources)
    await tx.commit()
```

**Rollback Scenarios**:
- Validation failure below threshold
- Consensus timeout (models unavailable)
- Document write failure
- Conflict detection triggers abort

### 4.3 Checkpoint and Recovery

**Automatic Checkpointing**:
- After each agent completes task
- Every 100 tasks executed
- On user interrupt (SIGINT)
- Before system shutdown

**Recovery Process**:
```python
async def recover_state():
    # Find incomplete tasks
    incomplete = await state_manager.get_tasks(status='running')

    # Reset to pending for retry
    for task in incomplete:
        await state_manager.update_task(
            task.id,
            status='pending',
            retry_count=task.retry_count + 1
        )

    # Resume orchestrator
    await orchestrator.resume_from_checkpoint()
```

---

## 5. CLI Output Format Specification

### 5.1 LLM-Friendly Output Format

**Design Principles**:
- Structured (JSON) for parsing
- Human-readable section headers
- Hierarchical information presentation
- Consistent field naming
- Parseable status codes

**Standard Output Schema**:
```json
{
  "schema_version": "1.0",
  "command": "research",
  "status": "success|error|partial",
  "timestamp": "2025-11-12T10:30:00Z",
  "task_id": "uuid",
  "trace_id": "uuid",

  "result": {
    "topic": {
      "id": "uuid",
      "title": "string",
      "document_path": "path/to/doc.md",
      "state": "published",
      "confidence": 0.91,
      "version": 4
    },

    "changes": {
      "mode": "update|create",
      "previous_version": 3,
      "current_version": 4,
      "lines_added": 347,
      "lines_removed": 89,
      "sections_modified": 12,
      "diff_path": "path/to/diff.txt"
    },

    "validation": {
      "claims_extracted": 45,
      "claims_validated": 42,
      "claims_rejected": 3,
      "consensus_score": 0.91,
      "models_used": ["claude-sonnet-4-5", "gpt-4-turbo", "gemini-1.5-pro"],
      "conflicts_detected": 2,
      "conflicts_resolved": 1
    },

    "sources": {
      "total": 18,
      "by_type": {
        "documentation": 7,
        "academic": 3,
        "blog": 5,
        "news": 3
      },
      "average_authority": 0.78
    },

    "performance": {
      "duration_seconds": 127.3,
      "tasks_executed": 23,
      "api_calls": {
        "tavily": 8,
        "context7": 5,
        "anthropic": 15,
        "openai": 15,
        "google": 15
      }
    }
  },

  "warnings": [
    {
      "severity": "medium",
      "message": "2 conflicts require human review",
      "action": "aris conflicts list --topic {topic_id}"
    }
  ],

  "next_actions": [
    "Review flagged conflicts",
    "Consider adding cost comparison data",
    "Challenge analysis suggests geographic bias"
  ],

  "commands": {
    "view_document": "aris show {document_path}",
    "view_diff": "aris diff {document_path} --version {prev}:{current}",
    "review_conflicts": "aris conflicts list --topic {topic_id}"
  }
}
```

### 5.2 Progress Output (Streaming)

**Real-time Progress Updates**:
```
[2025-11-12 10:30:15] ORCHESTRATOR | Initializing research workflow
[2025-11-12 10:30:16] COORDINATOR  | Query parsed: 4 sub-questions identified
[2025-11-12 10:30:16] COORDINATOR  | Existing topic found: booking-systems.md (v3)
[2025-11-12 10:30:16] COORDINATOR  | Mode: UPDATE | Tasks created: 12
[2025-11-12 10:30:17] TASK_QUEUE   | Executing level 0 tasks (4 parallel)
[2025-11-12 10:30:18] RESEARCHER_1 | Tavily search: offline-first architecture [3/10 results]
[2025-11-12 10:30:22] RESEARCHER_2 | Context7: PowerSync documentation [COMPLETE]
[2025-11-12 10:30:25] RESEARCHER_1 | Tavily search: [COMPLETE] 10 sources found
[2025-11-12 10:30:26] VALIDATOR    | Extracting claims: 45 candidates identified
[2025-11-12 10:30:30] VALIDATOR    | Consensus validation: [=========>----] 65% (29/45)
[2025-11-12 10:30:45] VALIDATOR    | Validation complete: 42 accepted, 3 rejected
[2025-11-12 10:30:45] CHALLENGER   | Analyzing for gaps: 3 recommendations generated
[2025-11-12 10:30:46] SYNTHESIZER  | Updating document: mapping 42 claims to sections
[2025-11-12 10:30:50] SYNTHESIZER  | Document updated: +347/-89 lines (12 sections)
[2025-11-12 10:30:51] ARCHIVIST    | Indexing complete | Graph updated
[2025-11-12 10:30:51] ORCHESTRATOR | Research complete | Confidence: 0.91
```

**Progress Bar Format**:
```
Validating claims: [=========>----] 65% (29/45) | Consensus: 0.89 | ETA: 15s
```

---

## 6. Agent Coordination Pattern

### 6.1 A2A Message Flow

**Example: Research Task Coordination**

```
ORCHESTRATOR → COORDINATOR
{
  "from": "orchestrator",
  "to": "coordinator",
  "message_type": "task",
  "payload": {
    "action": "decompose_query",
    "query": "How do booking systems handle offline mode?",
    "mode": "auto"
  }
}

COORDINATOR → ORCHESTRATOR
{
  "from": "coordinator",
  "to": "orchestrator",
  "message_type": "result",
  "payload": {
    "mode": "update",
    "topic_id": "uuid",
    "sub_queries": [
      "What is offline-first architecture?",
      "Which booking systems support offline?",
      "How do payment processors handle offline?"
    ],
    "task_dag": {
      "root": "task-uuid-1",
      "tasks": [...]
    }
  }
}

ORCHESTRATOR → TASK_QUEUE
{
  "from": "orchestrator",
  "to": "task_queue",
  "message_type": "task",
  "payload": {
    "action": "execute_dag",
    "dag": {...}
  }
}

TASK_QUEUE → RESEARCHER_1 (parallel)
TASK_QUEUE → RESEARCHER_2 (parallel)
TASK_QUEUE → RESEARCHER_3 (parallel)
{
  "from": "task_queue",
  "to": "researcher_1",
  "message_type": "task",
  "payload": {
    "task_id": "uuid",
    "sub_query": "What is offline-first architecture?",
    "tools": ["tavily", "context7"]
  }
}

[All researchers complete and return results]

TASK_QUEUE → VALIDATOR
{
  "from": "task_queue",
  "to": "validator",
  "message_type": "task",
  "payload": {
    "task_id": "uuid",
    "findings": [...],
    "sources": [...]
  }
}
```

### 6.2 Error Propagation

**Error Handling Chain**:
```
AGENT encounters error
  ↓
Format error message with context
  ↓
Send error to parent task
  ↓
Parent decides: retry, skip, or abort
  ↓
IF retry → Reschedule with backoff
IF skip → Log warning, continue
IF abort → Rollback transaction, notify user
```

**Error Message Format**:
```json
{
  "message_type": "error",
  "payload": {
    "error_type": "APITimeout|ValidationFailure|DataCorruption",
    "message": "Human-readable error",
    "context": {
      "task_id": "uuid",
      "agent": "researcher",
      "operation": "tavily_search"
    },
    "retry_possible": true,
    "retry_count": 1,
    "max_retries": 3
  }
}
```

---

## 7. Scalability Considerations

### 7.1 Performance Optimization

**Caching Strategy**:
```python
# Vector embeddings cache (in-memory)
@lru_cache(maxsize=1000)
async def get_embedding(text: str) -> np.ndarray:
    """Cache embeddings to avoid recomputation."""

# Validation results cache (Redis)
cache_key = f"validation:{claim_hash}:{sources_hash}"
cached = await redis.get(cache_key)
if cached:
    return ValidationResult.from_json(cached)

# MCP response cache (time-based)
@cache(ttl=3600)
async def context7_search(query: str):
    """Cache Context7 results for 1 hour."""
```

**Database Query Optimization**:
- Indexed columns: topic embeddings, task status, claim confidence
- Materialized views for complex aggregations
- Connection pooling (max 20 connections)
- Prepared statements for common queries

**Parallel Execution Limits**:
```python
MAX_PARALLEL_TASKS = 10  # Concurrent tasks
MAX_PARALLEL_AGENTS = 5  # Concurrent agent instances
MAX_PARALLEL_API_CALLS = 3  # Per external API
```

### 7.2 Horizontal Scaling

**Stateless Agent Design**:
- All state in database, not in-memory
- Agents can be replicated across processes
- Task queue supports distributed workers

**Future Architecture (Distributed)**:
```
Load Balancer
    ↓
Multiple Orchestrator Instances
    ↓
RabbitMQ Message Bus
    ↓
Agent Worker Pool (Celery)
    ↓
PostgreSQL Primary (writes)
    ↓
PostgreSQL Replicas (reads)
```

**Migration Path**:
1. **Phase 1**: Single process, SQLite
2. **Phase 2**: Single process, PostgreSQL
3. **Phase 3**: Multi-process, shared PostgreSQL
4. **Phase 4**: Distributed agents, message queue

### 7.3 Resource Limits

**API Rate Limiting**:
```python
rate_limits = {
    "anthropic": 500/minute,
    "openai": 500/minute,
    "google": 300/minute,
    "tavily": 100/minute,
    "context7": 200/minute
}
```

**Cost Controls**:
- Budget alerts at 50%, 80%, 95% of limit
- Automatic throttling above threshold
- Cheaper models for preliminary validation
- Cache-first strategy for repeated queries

**Token Usage Tracking**:
```python
class TokenTracker:
    async def log_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float
    ):
        """Track and alert on token usage."""
```

---

## 8. Implementation Roadmap

### Phase 1: Core Foundation (Weeks 1-2)
**Deliverables**:
- ✅ Project structure and dependencies
- ✅ Database schema (SQLite)
- ✅ State manager with transactions
- ✅ Basic CLI (`aris init`, `aris status`)
- ✅ Orchestrator skeleton

**Validation**: Can initialize database and show status

---

### Phase 2: Single-Agent Pipeline (Weeks 3-4)
**Deliverables**:
- ✅ Coordinator agent (query parsing)
- ✅ Researcher agent (Tavily integration)
- ✅ Basic validator (single-model)
- ✅ Synthesizer (markdown generation)
- ✅ CLI: `aris research` command

**Validation**: Can execute full research workflow end-to-end

---

### Phase 3: Multi-Model Consensus (Weeks 5-6)
**Deliverables**:
- ✅ Consensus validator (3 models)
- ✅ Validation logging
- ✅ Conflict detection
- ✅ Confidence thresholds
- ✅ Human review workflow

**Validation**: Hallucination prevention working correctly

---

### Phase 4: Task Queue & Parallelism (Weeks 7-8)
**Deliverables**:
- ✅ DAG task queue
- ✅ Dependency resolution
- ✅ Parallel agent execution
- ✅ Retry logic
- ✅ Progress streaming

**Validation**: Can handle 50+ parallel tasks efficiently

---

### Phase 5: Document Management (Weeks 9-10)
**Deliverables**:
- ✅ Semantic deduplication
- ✅ Document versioning
- ✅ Diff generation
- ✅ Section mapping
- ✅ Preserve existing content

**Validation**: Never creates duplicate documents

---

### Phase 6: Knowledge Graph (Weeks 11-12)
**Deliverables**:
- ✅ Neo4j integration
- ✅ Topic relationships
- ✅ Claim contradictions
- ✅ Vector embeddings (ChromaDB)
- ✅ Semantic search

**Validation**: Can find related topics and detect contradictions

---

### Phase 7: MCP Integration (Weeks 13-14)
**Deliverables**:
- ✅ Context7 client
- ✅ Tavily client
- ✅ Sequential MCP
- ✅ Playwright MCP
- ✅ Circuit breakers

**Validation**: All MCP servers working with fallbacks

---

### Phase 8: Advanced Agents (Weeks 15-16)
**Deliverables**:
- ✅ Challenger agent
- ✅ Archivist agent
- ✅ A2A protocol
- ✅ Message bus
- ✅ Agent coordination

**Validation**: Full multi-agent workflows functioning

---

### Phase 9: Production Hardening (Weeks 17-18)
**Deliverables**:
- ✅ PostgreSQL migration
- ✅ Comprehensive error handling
- ✅ Monitoring and logging
- ✅ Performance optimization
- ✅ Security audit

**Validation**: Production-ready system

---

### Phase 10: Documentation & Release (Weeks 19-20)
**Deliverables**:
- ✅ User documentation
- ✅ API documentation
- ✅ Example workflows
- ✅ Installation guide
- ✅ v1.0 release

**Validation**: External users can install and use successfully

---

## 9. File Structure

```
aris-tool/
├── pyproject.toml              # Poetry dependencies
├── README.md                   # User documentation
├── LICENSE                     # MIT License
│
├── aris/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main coordination hub
│   │   ├── state_manager.py    # Database state management
│   │   ├── task_queue.py       # DAG task scheduler
│   │   └── consensus.py        # Multi-model validation
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class
│   │   ├── coordinator.py      # Query decomposition
│   │   ├── researcher.py       # Information gathering
│   │   ├── validator.py        # Fact-checking
│   │   ├── synthesizer.py      # Document generation
│   │   ├── challenger.py       # Critical analysis
│   │   └── archivist.py        # Cataloging & indexing
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── mcp_client.py       # Generic MCP client
│   │   ├── context7_client.py  # Context7 wrapper
│   │   ├── tavily_client.py    # Tavily wrapper
│   │   ├── sequential_client.py# Sequential MCP wrapper
│   │   ├── playwright_client.py# Playwright wrapper
│   │   └── a2a_protocol.py     # Agent communication
│   │
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── graph_db.py         # Neo4j knowledge graph
│   │   ├── vector_store.py     # ChromaDB embeddings
│   │   └── provenance.py       # Citation management
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── renderer.py         # Report generation
│   │   └── differ.py           # Document diff
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── topic.py            # Topic data model
│   │   ├── claim.py            # Claim data model
│   │   ├── source.py           # Source data model
│   │   ├── task.py             # Task data model
│   │   └── message.py          # A2A message model
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py          # Structured logging
│   │   ├── config.py           # Configuration management
│   │   ├── embedding.py        # Embedding utilities
│   │   └── retry.py            # Retry decorators
│   │
│   └── cli.py                  # Click CLI interface
│
├── tests/
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   │   ├── test_orchestrator.py
│   │   ├── test_agents.py
│   │   └── test_consensus.py
│   ├── integration/            # Integration tests
│   │   ├── test_workflow.py
│   │   └── test_mcp.py
│   └── fixtures/               # Test data
│
├── migrations/                 # Alembic migrations
│   ├── versions/
│   └── env.py
│
├── scripts/
│   ├── setup_db.py            # Database initialization
│   ├── migrate_to_postgres.py # SQLite → PostgreSQL
│   └── benchmark.py           # Performance testing
│
├── docs/
│   ├── architecture.md         # This document
│   ├── user_guide.md           # User documentation
│   ├── api_reference.md        # API documentation
│   └── examples/               # Usage examples
│
├── data/                       # Runtime data (gitignored)
│   ├── aris.db                # SQLite database
│   ├── cache/                 # Response caches
│   └── logs/                  # Application logs
│
└── claudedocs/                 # Claude-specific docs
    ├── ARIS-Architecture-Blueprint.md  # This file
    └── implementation_notes.md
```

---

## 10. Security Considerations

### 10.1 API Key Management

**Storage**:
- Use system keyring (keyring library)
- Fallback to encrypted .env file
- Never commit keys to version control

**Rotation**:
```python
async def rotate_api_key(provider: str, new_key: str):
    """
    1. Validate new key works
    2. Store in keyring
    3. Update active connections
    4. Log rotation event
    """
```

### 10.2 Input Sanitization

**Query Validation**:
```python
def sanitize_query(query: str) -> str:
    """
    - Remove SQL injection attempts
    - Strip excessive whitespace
    - Limit length (max 1000 chars)
    - Escape special characters
    """
```

### 10.3 Rate Limiting

**Per-User Quotas**:
```python
rate_limiter = {
    "requests_per_hour": 100,
    "api_calls_per_day": 5000,
    "tokens_per_month": 1000000
}
```

---

## 11. Monitoring and Observability

### 11.1 Logging Strategy

**Structured Logging**:
```python
logger.info(
    "task_completed",
    extra={
        "task_id": task.id,
        "agent": "researcher",
        "duration_ms": 1273,
        "status": "success",
        "sources_found": 10
    }
)
```

**Log Levels**:
- **DEBUG**: Detailed execution traces
- **INFO**: Task completions, state changes
- **WARNING**: Retries, fallbacks, low confidence
- **ERROR**: Failures, exceptions
- **CRITICAL**: System-level failures

### 11.2 Metrics Collection

**Key Metrics**:
```python
metrics = {
    "tasks_completed": Counter,
    "task_duration_seconds": Histogram,
    "api_call_latency": Histogram,
    "validation_confidence": Gauge,
    "database_connections": Gauge,
    "error_rate": Counter
}
```

### 11.3 Tracing

**Distributed Tracing**:
```python
@trace(name="research_workflow")
async def execute_research(query: str):
    span = get_current_span()
    span.set_attribute("query", query)
    span.set_attribute("mode", mode)
    # ... execution ...
    span.set_attribute("confidence", result.confidence)
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

**Coverage Targets**:
- Core modules: 90%+
- Agents: 85%+
- Integrations: 70%+ (mocked external APIs)
- Utils: 95%+

**Example Test**:
```python
@pytest.mark.asyncio
async def test_coordinator_semantic_deduplication():
    coordinator = CoordinatorAgent()

    # Create existing topic
    topic_id = await state_manager.create_topic(
        title="Offline booking systems",
        embedding=embed("how do booking systems work offline")
    )

    # Query with similar semantics
    result = await coordinator.find_existing_topic(
        "how do reservation systems handle no internet"
    )

    assert result is not None
    assert result.id == topic_id
```

### 12.2 Integration Tests

**Scenarios**:
- Full research workflow (mocked MCP servers)
- Database transaction rollback
- Task DAG execution with failures
- Multi-model consensus with disagreement

### 12.3 End-to-End Tests

**Real API Tests** (optional, expensive):
```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_real_research_workflow():
    """
    Execute real research with actual API calls.
    Requires API keys in environment.
    """
    result = await orchestrator.execute_research(
        "What is PowerSync offline-first architecture?"
    )
    assert result.confidence > 0.7
    assert result.document_path.exists()
```

---

## 13. Configuration Management

### 13.1 Configuration Files

**config.yaml**:
```yaml
system:
  debug: false
  log_level: INFO
  data_dir: ./data

database:
  type: sqlite  # or postgresql
  path: ./data/aris.db
  # PostgreSQL connection:
  # host: localhost
  # port: 5432
  # database: aris
  # user: aris_user
  # password: ${POSTGRES_PASSWORD}

agents:
  max_parallel: 10
  retry_max_attempts: 3
  retry_backoff_seconds: 2

task_queue:
  max_concurrent_tasks: 10
  task_timeout_seconds: 300

consensus:
  threshold: 0.7
  models:
    - provider: anthropic
      model: claude-sonnet-4-5
      weight: 1.0
    - provider: openai
      model: gpt-4-turbo
      weight: 1.0
    - provider: google
      model: gemini-1.5-pro
      weight: 1.0

integrations:
  tavily:
    search_depth: advanced
    max_results: 10
  context7:
    enabled: true
  sequential:
    enabled: true

output:
  format: json
  include_diff: true
  include_provenance: true
```

### 13.2 Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
TAVILY_API_KEY=...

# Database
POSTGRES_PASSWORD=...

# Monitoring
SENTRY_DSN=...
```

---

## 14. Error Handling and Recovery

### 14.1 Error Categories

**Transient Errors** (Retry):
- Network timeouts
- Rate limit exceeded
- API service unavailable

**Permanent Errors** (Fail):
- Invalid API key
- Malformed query
- Database corruption

**Degraded Errors** (Fallback):
- One model unavailable → Use remaining models
- MCP server down → Use alternative tool
- Low confidence → Flag for human review

### 14.2 Recovery Strategies

**Graceful Degradation**:
```python
try:
    result = await tavily_client.search(query)
except TavilyUnavailable:
    logger.warning("Tavily unavailable, falling back to native search")
    result = await native_search(query)
```

**Circuit Breaker**:
```python
class CircuitBreaker:
    states = [CLOSED, OPEN, HALF_OPEN]

    async def call(self, func, *args):
        if self.state == OPEN:
            raise CircuitOpenError("Too many failures")

        try:
            result = await func(*args)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
```

---

## 15. Deployment Strategy

### 15.1 Development Deployment

```bash
# Clone repository
git clone https://github.com/user/aris-tool.git
cd aris-tool

# Install with Poetry
poetry install

# Initialize database
poetry run aris init

# Configure API keys
poetry run aris config set anthropic_key sk-...

# Run research
poetry run aris research "your question"
```

### 15.2 Production Deployment

**Docker Compose**:
```yaml
version: '3.8'

services:
  aris:
    build: .
    environment:
      - DATABASE_TYPE=postgresql
      - POSTGRES_HOST=postgres
    depends_on:
      - postgres
      - neo4j
      - chroma
    volumes:
      - ./data:/app/data
    command: aris serve

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_DB=aris
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j_data:/data

  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/data

volumes:
  postgres_data:
  neo4j_data:
  chroma_data:
```

---

## 16. Future Enhancements

### 16.1 Phase 11+ (Future Work)

**Advanced Features**:
- Real-time collaboration (multiple users)
- Web UI dashboard for research management
- Custom agent plugins (user-defined agents)
- Export to Notion, Obsidian, Roam Research
- Slack/Discord bot integration
- Automated scheduled research updates
- Multi-language support (non-English research)

**Scalability**:
- Kubernetes deployment
- Distributed agent workers (Celery)
- Read replicas for PostgreSQL
- CDN for document serving

**Intelligence**:
- Active learning (improve from user feedback)
- Meta-learning (optimize agent coordination)
- Causal reasoning (understand why, not just what)
- Counterfactual analysis (what-if scenarios)

---

## 17. Success Metrics

### 17.1 System Performance

- **Task completion rate**: >95%
- **Average research duration**: <5 minutes
- **API success rate**: >99%
- **Database query latency**: <50ms p99

### 17.2 Research Quality

- **Consensus confidence**: >0.85 average
- **Duplicate document rate**: <1%
- **Hallucination detection**: >90% caught
- **Source authority**: >0.75 average

### 17.3 User Experience

- **CLI response time**: <200ms
- **Error rate**: <2%
- **User satisfaction**: >4.5/5
- **Adoption rate**: Growing

---

## Conclusion

This architectural blueprint provides a **complete, production-ready design** for ARIS. The system addresses all core requirements:

✅ **Document proliferation prevention** via semantic deduplication
✅ **Hallucination mitigation** through multi-model consensus
✅ **State management** with transactional ACID guarantees
✅ **Scalable architecture** from SQLite to distributed PostgreSQL
✅ **LLM-friendly CLI** with structured JSON output
✅ **Modular design** with clear separation of concerns
✅ **Comprehensive error handling** with graceful degradation
✅ **MCP integration** for Context7, Tavily, Sequential, Playwright
✅ **DAG task queue** with dependency resolution
✅ **A2A protocol** for agent coordination

The system is designed with **backend architect principles**: reliability first, data integrity guaranteed, performance optimized, and security baked in from the start.

**Next Step**: Begin Phase 1 implementation (Core Foundation).
