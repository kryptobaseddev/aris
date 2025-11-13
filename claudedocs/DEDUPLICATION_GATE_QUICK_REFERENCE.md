# Deduplication Gate - Quick Reference Card

## Module Path
```python
from aris.core.deduplication_gate import (
    DeduplicationGate,
    DeduplicationResult,
    DeduplicationAction,
    SimilarityMatch,
)
```

## Initialization
```python
gate = DeduplicationGate(
    db=database_manager,
    research_dir=Path("research"),
    similarity_threshold=0.85,  # UPDATE threshold
    merge_threshold=0.70         # MERGE threshold
)
```

## Main API
```python
result = await gate.check_before_write(
    content="Document content...",
    metadata={
        "title": "Document Title",
        "topics": ["topic1", "topic2"],
        "purpose": "What problem does this solve?"
    },
    query="Research query used"
)
```

## Decision Output
```python
result.action              # DeduplicationAction (CREATE|UPDATE|MERGE)
result.should_create       # bool - True if CREATE
result.should_update       # bool - True if UPDATE or MERGE
result.target_document     # Document - The document to update (if UPDATE/MERGE)
result.matches            # list[SimilarityMatch] - All similar documents
result.confidence         # float - Confidence in decision (0.0-1.0)
result.reason             # str - Why this decision was made
result.recommendation     # str - What user should do
```

## Decision Thresholds
```
Similarity ≥ 0.85  →  UPDATE    (merge automatically)
0.70 ≤ S < 0.85   →  MERGE     (suggest merge)
Similarity < 0.70  →  CREATE    (new document)
No docs found      →  CREATE    (confidence = 1.0)
```

## Similarity Calculation
```
Total = (topic_overlap × 0.40) + (content_sim × 0.40) + (question_overlap × 0.20)

Topic Overlap:      Jaccard similarity of topic sets
Content Similarity: Word frequency-based comparison
Question Overlap:   Search context vs answered questions
```

## Working with Results

### Create New Document
```python
if result.should_create:
    document = document_store.create_document(
        title=title,
        content=content,
        topics=topics,
        confidence=confidence
    )
```

### Update Existing Document
```python
if result.should_update:
    target = result.target_document
    target.update_content(content, merge_strategy="append")
    target.metadata.confidence = max(target.metadata.confidence, new_confidence)
    target.metadata.source_count += additional_sources
    document = document_store.update_document(target)
```

### Examine Matches
```python
for match in result.matches:
    print(f"{match.document.metadata.title}: {match.similarity_score:.2%}")
    print(f"  Reason: {match.reason}")
```

## Configuration Presets

### Strict Mode (Fewer Merges)
```python
gate = DeduplicationGate(db, research_dir,
    similarity_threshold=0.95,
    merge_threshold=0.85
)
```

### Balanced Mode (Default)
```python
gate = DeduplicationGate(db, research_dir,
    similarity_threshold=0.85,
    merge_threshold=0.70
)
```

### Aggressive Mode (More Merges)
```python
gate = DeduplicationGate(db, research_dir,
    similarity_threshold=0.75,
    merge_threshold=0.60
)
```

## Integration with ResearchOrchestrator

Gate is automatically initialized in `ResearchOrchestrator.__init__`:
```python
self.deduplication_gate = DeduplicationGate(db, research_dir)
```

Used automatically in `_save_research_document()`:
```python
dedup_result = await self.deduplication_gate.check_before_write(...)

if dedup_result.should_create:
    document = document_store.create_document(...)
else:
    document = document_store.update_document(target_doc)
```

## Error Handling

### Graceful Degradation
```python
try:
    result = await gate.check_before_write(content, metadata, query)
except Exception as e:
    logger.error(f"Gate check failed: {e}")
    # Fallback: create new document
    result = DeduplicationResult(action=DeduplicationAction.CREATE)
```

### Enable Debug Logging
```python
import logging
logging.getLogger('aris.core.deduplication_gate').setLevel(logging.DEBUG)

result = await gate.check_before_write(...)
# Debug logs show similarity calculations
```

## Common Scenarios

### Unique Research (No Similar Docs)
```
Result: CREATE
Confidence: 1.0
Recommendation: Creating new document
```

### Duplicate Content Found
```
Result: UPDATE
Confidence: 0.87
Target: "Existing Document Title"
Recommendation: Update existing document instead of creating duplicate
```

### Related Topic (Moderate Overlap)
```
Result: MERGE
Confidence: 0.74
Target: "Related Research"
Recommendation: Consider merging with existing document
```

### Different Topic (No Overlap)
```
Result: CREATE
Confidence: 0.85
Similar Docs: 1 found but low similarity (15%)
Recommendation: Creating new document with unique content
```

## Testing

### Run Unit Tests
```bash
pytest tests/unit/test_deduplication_gate.py -v
```

### Test Categories
- SimilarityMatch validation
- DeduplicationResult validation
- Gate decision logic
- Similarity calculations
- Integration scenarios
- Edge cases

### Key Test Coverage
- ✓ Threshold boundaries
- ✓ Empty content/topics
- ✓ Database integration
- ✓ Decision logging
- ✓ Error handling

## Monitoring

### Track Decisions
```python
CREATE_count = 0
UPDATE_count = 0
MERGE_count = 0

# Track in your workflow...

print(f"Created: {CREATE_count}")
print(f"Updated: {UPDATE_count}")
print(f"Suggested Merge: {MERGE_count}")
print(f"Duplication Prevention: {(UPDATE_count + MERGE_count) / total:.1%}")
```

### Decision Logging
All decisions are logged automatically:
```
INFO: Validation gate: Checking for duplicate documents
WARNING: Validation gate: High similarity (0.87) detected - recommend UPDATE
INFO: Research document updated: research/2024-01/doc.md
```

## Troubleshooting

### Too Many New Documents Created
```
Problem: Gate always returns CREATE
Solution:
  1. Lower similarity_threshold (try 0.80)
  2. Check that metadata.topics are populated
  3. Enable debug logging to see similarity scores
  4. Verify document topics are spelled consistently
```

### Too Many Documents Merged
```
Problem: Unrelated documents being merged
Solution:
  1. Raise similarity_threshold (try 0.90)
  2. Raise merge_threshold (try 0.75)
  3. Check topic specificity
  4. Review similarity calculations in debug logs
```

### Gate Hangs/Times Out
```
Problem: check_before_write() takes too long
Solution:
  1. Check research_dir size (sequential search)
  2. Reduce number of documents to search
  3. Wave 4 will add vector search for speed
```

## Future Enhancements (Wave 4+)

### Semantic Similarity
```python
# Will be available:
gate = DeduplicationGate(
    db, research_dir,
    use_semantic_similarity=True,
    embedding_model="all-MiniLM-L6-v2"
)
```

### Configurable Weights
```python
# Will be available:
gate = DeduplicationGate(
    db, research_dir,
    weights={
        "topic_overlap": 0.5,
        "content_similarity": 0.3,
        "question_overlap": 0.2
    }
)
```

### Vector Search
```python
# Will be available for faster similarity search
gate = DeduplicationGate(
    db, research_dir,
    use_vector_search=True,
    vector_db="pgvector"
)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/aris/core/deduplication_gate.py` | Main implementation |
| `src/aris/core/research_orchestrator.py` | Integration point |
| `tests/unit/test_deduplication_gate.py` | Comprehensive tests |
| `claudedocs/WAVE3_VALIDATION_GATE.md` | Detailed docs |
| `claudedocs/DEDUPLICATION_GATE_EXAMPLES.md` | Usage examples |

## Quick Links

- **Implementation**: See `WAVE3_VALIDATION_GATE.md`
- **Examples**: See `DEDUPLICATION_GATE_EXAMPLES.md`
- **Full Summary**: See `WAVE3_AGENT3_SUMMARY.md`
- **Tests**: See `tests/unit/test_deduplication_gate.py`

## Quick Start Example

```python
from pathlib import Path
from aris.core.deduplication_gate import DeduplicationGate
from aris.storage.database import DatabaseManager

# Setup
db = DatabaseManager(Path("data/aris.db"))
gate = DeduplicationGate(db, Path("research"))

# Check for duplicates
result = await gate.check_before_write(
    content="My research findings...",
    metadata={
        "title": "My Research",
        "topics": ["AI", "safety"],
        "purpose": "Explore AI safety"
    },
    query="AI safety"
)

# Handle result
if result.should_create:
    print("Creating new document")
elif result.should_update:
    print(f"Merging with: {result.target_document.metadata.title}")
    print(f"Similarity: {result.confidence:.2%}")
```

---

**Status**: Production Ready
**Version**: Wave 3 Complete
**Last Updated**: 2025-11-12
