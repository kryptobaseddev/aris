# Vector Store Design Documentation

## Overview

The VectorStore is a ChromaDB-based system for semantic document similarity detection. It enables ARIS to identify duplicate and related documents through vector embeddings, a core capability for preventing document proliferation.

## Architecture

### Component: VectorStore
**Location**: `src/aris/storage/vector_store.py`
**Purpose**: Manage document embeddings and provide semantic search

### Key Responsibilities
1. Document embedding generation (via ChromaDB's built-in embeddings)
2. Semantic similarity search with configurable thresholds
3. Vector store persistence to disk
4. Collection and document lifecycle management

## Core API

### VectorStore Methods

#### `__init__(persist_dir: Optional[Path] = None) -> None`
Initialize the vector store.
- **Args**:
  - `persist_dir`: Optional directory for persistent storage. If None, uses in-memory store.
- **Raises**: `VectorStoreError` if initialization fails
- **Usage**: Both in-memory (testing) and persistent (production) modes supported

#### `add_document(doc_id: str, content: str, metadata: Optional[dict] = None) -> str`
Add a document to the vector store with automatic embedding.
- **Args**:
  - `doc_id`: Unique document identifier
  - `content`: Document text to embed (full content or summary)
  - `metadata`: Optional dict with doc title, topic, status, etc.
- **Returns**: The document ID
- **Raises**: `VectorStoreError` if doc_id or content is empty
- **Example**:
  ```python
  store.add_document(
      "doc_001",
      "Machine learning fundamentals...",
      {"title": "ML Guide", "topic": "AI", "status": "draft"}
  )
  ```

#### `search_similar(query: str, threshold: float = 0.85, limit: int = 10) -> list[tuple[str, float, dict]]`
Search for semantically similar documents.
- **Args**:
  - `query`: Query text for semantic search
  - `threshold`: Similarity threshold 0.0-1.0 (default 0.85 for duplicates)
  - `limit`: Max results to return (default 10)
- **Returns**: List of (doc_id, similarity_score, metadata) tuples, sorted by similarity descending
- **Raises**: `VectorStoreError` if query is empty or threshold invalid
- **Thresholds**:
  - **0.85-1.0**: Duplicate detection (near-identical content)
  - **0.70-0.85**: Related documents (significant overlap)
  - **0.50-0.70**: Topic-related documents (same domain)
  - **<0.50**: Loosely related documents

#### `update_document(doc_id: str, content: str, metadata: Optional[dict] = None) -> None`
Update a document's embedding and metadata.
- **Args**:
  - `doc_id`: Document ID to update
  - `content`: New document content
  - `metadata`: Updated metadata
- **Raises**: `VectorStoreError` if update fails

#### `delete_document(doc_id: str) -> None`
Delete a document from the vector store.
- **Args**:
  - `doc_id`: Document ID to delete
- **Raises**: `VectorStoreError` if deletion fails

#### `get_document(doc_id: str) -> Optional[dict[str, str]]`
Retrieve a document from the vector store.
- **Args**:
  - `doc_id`: Document ID to retrieve
- **Returns**: Dict with id, content, metadata, or None if not found
- **Raises**: `VectorStoreError` if retrieval fails

#### `delete_all() -> None`
Delete all documents from the vector store.
- **WARNING**: This is irreversible
- **Raises**: `VectorStoreError` if deletion fails

#### `get_collection_stats() -> dict[str, int]`
Get statistics about the vector store.
- **Returns**: Dict with total_documents count and collection_name
- **Usage**: Monitor indexing progress and storage health

#### `persist() -> None`
Persist the vector store to disk.
- **Only works** if initialized with persist_dir
- **Usage**: Called after batch operations to ensure durability

## Integration Layer

### Component: VectorStoreIntegration
**Location**: `src/aris/storage/integrations.py`
**Purpose**: Seamless integration between VectorStore and DocumentStore

### Integration Methods

#### `index_document(doc_id, content, title="", topic="") -> None`
Index a document from DocumentStore into VectorStore.

#### `find_duplicates(content, threshold=0.85, limit=10) -> list[tuple[str, float]]`
Find potential duplicate documents.
- **Returns**: List of (doc_id, similarity_score) tuples

#### `find_related_documents(content, threshold=0.70, limit=10) -> list[tuple[str, float]]`
Find related but non-duplicate documents.
- **Returns**: List of (doc_id, similarity_score) tuples

#### `update_indexed_document(doc_id, content, title="", topic="") -> None`
Update a document's index.

#### `remove_indexed_document(doc_id) -> None`
Remove a document from the index.

#### `get_indexing_stats() -> dict[str, int]`
Get vector store statistics.

## Embedding Strategy

### ChromaDB Default Embedding
- Uses all-MiniLM-L6-v2 by default (384-dimensional embeddings)
- Optimized for semantic similarity (cosine distance)
- Supports both static and dynamic content

### Content Preparation
For best results:
- Use full document content for comprehensive similarity
- Or use document summary (first 500-1000 words) for efficiency
- Include metadata for filtering (title, topic, author, etc.)

### Similarity Scoring
- **Cosine Distance** used as metric (0 = identical, 2 = opposite)
- **Similarity Score** = 1 - distance (normalized to 0-1 range)
- **Threshold 0.85** captures near-duplicates with >85% similarity

## Storage Architecture

### In-Memory Mode (Testing)
```python
store = VectorStore(persist_dir=None)
```
- Uses ChromaDB's in-memory storage
- Fast, no disk I/O
- Lost on process exit
- Suitable for unit tests and development

### Persistent Mode (Production)
```python
store = VectorStore(persist_dir=Path("/data/vectors"))
```
- Uses DuckDB + Parquet persistence
- Durable across restarts
- Enables large-scale indexing
- Recommended for production

## Workflow Integration

### Typical Duplicate Detection Workflow
1. **New document created** in DocumentStore
2. **Extract content** from document
3. **Search vector store** with threshold 0.85
4. **If matches found**: Flag as potential duplicate
5. **If no matches**: Add to vector store and continue

### Indexing Workflow
```python
from aris.storage import DocumentStore, VectorStore

# Initialize stores
doc_store = DocumentStore(config)
vec_store = VectorStore(persist_dir=Path("/data/vectors"))

# Index existing documents
for doc in doc_store.get_all_documents():
    vec_store.add_document(
        doc.id,
        doc.content,
        {"title": doc.title, "topic": doc.topic_id}
    )

# Check for duplicates in new document
query_results = vec_store.search_similar(new_content, threshold=0.85)
duplicates = [doc_id for doc_id, score, _ in query_results]
```

## Error Handling

### Exception Hierarchy
- `VectorStoreError`: Base exception for all vector store operations
  - Invalid inputs (empty doc_id, empty content, invalid threshold)
  - ChromaDB operation failures (add, update, delete, search)
  - Collection management failures

### Common Errors
| Error | Cause | Recovery |
|-------|-------|----------|
| `VectorStoreError` - "doc_id and content required" | Empty doc_id or content | Validate inputs before calling |
| `VectorStoreError` - "Threshold must be 0.0-1.0" | Invalid threshold | Ensure 0.0 <= threshold <= 1.0 |
| `VectorStoreError` - "Failed to initialize" | ChromaDB/permission issue | Check disk space, permissions |
| `VectorStoreError` - "Search failed" | ChromaDB query error | Retry; check collection state |

## Performance Characteristics

### Operations
- **Add Document**: O(1) - Fast embedding generation
- **Search**: O(n log n) - ANN search with HNSW indexing
- **Update**: O(1) - Direct replacement
- **Delete**: O(1) - Direct removal

### Storage
- **Per Document**: ~500 bytes (384-dim embedding + metadata)
- **Collection Overhead**: ~1MB
- **Example**: 10,000 documents ≈ 5MB total

### Search Latency
- **Typical**: <100ms for 10,000 documents
- **Worst case**: <1s for 1M documents
- **Batch Indexing**: 100 docs/second typical

## Testing

### Test File
**Location**: `tests/unit/storage/test_vector_store.py`
**Coverage**:
- Initialization (in-memory, persistent)
- Document operations (add, update, delete, get)
- Similarity search (basic, threshold, limits)
- Duplicate detection (near-duplicates, false positives)
- Persistence and stats

### Running Tests
```bash
pytest tests/unit/storage/test_vector_store.py -v
pytest tests/unit/storage/test_vector_store.py::TestDuplicateDetection -v
```

## Security Considerations

### Data Protection
- Embeddings are deterministic (same content = same embedding)
- No sensitive data stored in vector store (only IDs, metadata)
- All document IDs should be opaque identifiers
- Consider encryption for persistent storage in sensitive environments

### Input Validation
- All inputs validated (non-empty doc_id, content, valid thresholds)
- ChromaDB handles malformed inputs gracefully
- Large documents (>1MB) should be summarized before indexing

## Future Enhancements

### Planned Features
1. **Custom Embedding Models**: Support for domain-specific embeddings
2. **Batch Operations**: Optimize bulk indexing and updates
3. **Filtering**: Semantic search with metadata filtering
4. **Reranking**: Multi-stage ranking for improved relevance
5. **Hybrid Search**: Combine semantic + keyword search
6. **Clustering**: Automatic document grouping by topic

### Scalability
- Current design supports 1M+ documents
- Plan for PostgreSQL vector extension (pgvector) in future
- Consider distributed vector databases for 100M+ scale

## Best Practices

### Indexing
1. **Batch Updates**: Group multiple documents for efficiency
2. **Regular Persistence**: Call `persist()` after batch operations
3. **Content Quality**: Use full documents for better similarity; summaries for efficiency
4. **Metadata**: Always include title and topic for context

### Search
1. **Threshold Selection**: Use 0.85 for duplicates, 0.70 for related
2. **Result Limits**: Start with limit=10 to balance speed/completeness
3. **Query Refinement**: Retry with adjusted thresholds if needed

### Maintenance
1. **Monitor Stats**: Periodically check `get_collection_stats()`
2. **Clean Orphans**: Delete documents removed from DocumentStore
3. **Regular Backups**: Backup persist_dir for disaster recovery
4. **Index Rebuild**: Consider periodic reindexing with new models

## References

- **ChromaDB Documentation**: https://docs.trychroma.com/
- **Embeddings Guide**: https://docs.trychroma.com/embeddings
- **Similarity Metrics**: https://en.wikipedia.org/wiki/Cosine_similarity
- **ARIS Architecture**: See `ARIS_ARCHITECTURE.md`
