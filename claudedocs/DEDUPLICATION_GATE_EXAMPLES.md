# Deduplication Gate Usage Examples

## Quick Start

### Basic Usage

```python
from pathlib import Path
from aris.core.deduplication_gate import DeduplicationGate
from aris.storage.database import DatabaseManager

# Initialize
db = DatabaseManager(Path("data/aris.db"))
gate = DeduplicationGate(
    db=db,
    research_dir=Path("research")
)

# Check if content is duplicate before writing
result = await gate.check_before_write(
    content="Latest AI safety research findings...",
    metadata={
        "title": "AI Safety Review 2024",
        "topics": ["AI", "safety", "governance"],
        "purpose": "Understand AI safety landscape"
    },
    query="AI safety recent developments"
)

# Check decision
if result.should_create:
    print("Creating new document")
    # Create new document
elif result.should_update:
    print(f"Updating: {result.target_document.metadata.title}")
    # Merge with existing document
```

## Decision Flow Examples

### Example 1: No Similar Documents (CREATE)

**Input:**
```python
result = await gate.check_before_write(
    content="Comprehensive review of quantum computing error correction",
    metadata={
        "title": "Quantum Error Correction",
        "topics": ["quantum", "error correction", "quantum computing"],
        "purpose": "Understand QEC approaches"
    },
    query="quantum computing error correction latest"
)
```

**Output:**
```
result.action = DeduplicationAction.CREATE
result.should_create = True
result.should_update = False
result.target_document = None
result.matches = []
result.confidence = 1.0
result.reason = "No documents with similar content or topics found"
result.recommendation = "Creating new document"
```

**Decision:** Create new document - unique content

---

### Example 2: High Similarity Found (UPDATE)

**Input:**
- Existing document: "AI Safety Principles and Implementation"
  - Topics: ["AI", "safety", "governance"]
  - Confidence: 0.75

```python
result = await gate.check_before_write(
    content="Additional findings on AI safety governance frameworks...",
    metadata={
        "title": "AI Governance Frameworks",
        "topics": ["AI", "governance", "safety"],
        "purpose": "Review safety governance"
    },
    query="AI safety governance"
)
```

**Output:**
```
result.action = DeduplicationAction.UPDATE
result.should_create = False
result.should_update = True
result.target_document = <Document: "AI Safety Principles and Implementation">
result.matches = [
    SimilarityMatch(
        document=<existing_doc>,
        similarity_score=0.87,
        reason="Topic overlap: AI, safety, governance"
    )
]
result.confidence = 0.87
result.reason = "High similarity (87%) detected with existing document"
result.recommendation = "Update existing document instead of creating duplicate"
```

**Decision:** Merge with existing - high topic and content overlap

---

### Example 3: Moderate Similarity (MERGE)

**Input:**
- Existing: "Machine Learning Security Vulnerabilities"
  - Topics: ["ML", "security", "adversarial"]

```python
result = await gate.check_before_write(
    content="Survey of AI robustness and adversarial training methods...",
    metadata={
        "title": "AI Robustness and Adversarial Training",
        "topics": ["AI", "adversarial", "robustness"],
        "purpose": "Understand adversarial resilience"
    },
    query="adversarial robustness training"
)
```

**Output:**
```
result.action = DeduplicationAction.MERGE
result.should_create = False
result.should_update = True
result.target_document = <Document: "Machine Learning Security Vulnerabilities">
result.matches = [
    SimilarityMatch(
        document=<existing_doc>,
        similarity_score=0.74,
        reason="Topic overlap: adversarial"
    )
]
result.confidence = 0.74
result.reason = "Moderate similarity (74%) - recommend integration"
result.recommendation = "Consider merging with existing document"
```

**Decision:** Suggest merge - moderate overlap, user can decide

---

### Example 4: Low Similarity (CREATE)

**Input:**
- Existing: "AI Safety Research" (topics: AI, safety)

```python
result = await gate.check_before_write(
    content="Advances in quantum entanglement and quantum teleportation...",
    metadata={
        "title": "Quantum Teleportation",
        "topics": ["quantum", "physics", "teleportation"],
        "purpose": "Review quantum physics"
    },
    query="quantum teleportation recent progress"
)
```

**Output:**
```
result.action = DeduplicationAction.CREATE
result.should_create = True
result.should_update = False
result.target_document = None
result.matches = [
    SimilarityMatch(
        document=<existing_ai_doc>,
        similarity_score=0.15,
        reason="No topic overlap"
    )
]
result.confidence = 0.85  # confidence = 1.0 - 0.15
result.reason = "Low similarity with existing documents (best match: 15%)"
result.recommendation = "Creating new document with unique content"
```

**Decision:** Create new - completely different topics

---

## Integration with ResearchOrchestrator

### Automatic Deduplication in Research Workflow

```python
async def execute_research(
    self,
    query: str,
    depth: str = "standard"
):
    # ... research execution ...

    # Before saving document:
    document = await self._save_research_document(
        session=session,
        context=reasoning_context,
        query=query
    )
    # _save_research_document automatically:
    # 1. Formats findings
    # 2. Calls deduplication_gate.check_before_write()
    # 3. Either creates new or updates existing
    # 4. Logs decision and reasoning
```

### Workflow Example

```python
orchestrator = ResearchOrchestrator(config)

# User initiates research
result = await orchestrator.execute_research(
    query="Latest advances in AI safety",
    depth="standard"
)

# Orchestrator:
# 1. Creates research session
# 2. Executes multi-hop research with Tavily
# 3. Uses Sequential for structured reasoning
# 4. **[GATE VALIDATION]** Checks for duplicates
# 5. Creates or updates document based on gate decision
# 6. Returns document path and metadata

print(f"Document: {result.document_path}")
print(f"Was merged: {result.was_merged}")
print(f"Confidence: {result.confidence:.2%}")
```

## Configuring Thresholds

### Strict Mode (High Threshold)

```python
gate = DeduplicationGate(
    db=db,
    research_dir=research_dir,
    similarity_threshold=0.95,  # Very strict
    merge_threshold=0.85
)
# Only exact matches are considered updates
# More new documents created
# Lower chance of unwanted merges
```

### Aggressive Mode (Low Threshold)

```python
gate = DeduplicationGate(
    db=db,
    research_dir=research_dir,
    similarity_threshold=0.75,  # Aggressive
    merge_threshold=0.60
)
# More documents merged automatically
# Fewer new documents created
# Higher chance of merging related topics
```

### Balanced Mode (Default)

```python
gate = DeduplicationGate(
    db=db,
    research_dir=research_dir,
    similarity_threshold=0.85,  # Recommended
    merge_threshold=0.70
)
# Balanced between creating and merging
# Default configuration
# Good for most use cases
```

## Analyzing Gate Decisions

### Understanding Similarity Scores

```python
result = await gate.check_before_write(...)

# Examine the decision
print(f"Decision: {result.action}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Reason: {result.reason}")
print(f"Recommendation: {result.recommendation}")

# Look at matches
for match in result.matches:
    print(f"\n  Similar document: {match.document.metadata.title}")
    print(f"  Similarity: {match.similarity_score:.2%}")
    print(f"  Reason: {match.reason}")
```

### Debug Logging

Enable debug logging to see similarity calculation details:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

result = await gate.check_before_write(...)
# Logs will show:
# - Topic overlap calculations
# - Content similarity scoring
# - Question matching
# - Overall similarity calculation
# - Decision logic
```

## Advanced: Custom Similarity Weights

The gate uses fixed weights for similarity criteria:
- Topic overlap: 40%
- Content similarity: 40%
- Question overlap: 20%

To adjust these in the future (Wave 4+):

```python
# This will be available after enhancement
gate = DeduplicationGate(
    db=db,
    research_dir=research_dir,
    weights={
        "topic_overlap": 0.5,      # Emphasize topics
        "content_similarity": 0.3,
        "question_overlap": 0.2
    }
)
```

## Error Handling

### Graceful Degradation

```python
try:
    result = await gate.check_before_write(
        content=content,
        metadata=metadata,
        query=query
    )
except Exception as e:
    logger.error(f"Gate check failed: {e}")
    # Fallback: always create new document
    result = DeduplicationResult(
        action=DeduplicationAction.CREATE,
        reason="Gate check failed, creating new document as fallback"
    )
```

### Empty Content Handling

```python
# Gate handles empty content gracefully
result = await gate.check_before_write(
    content="",  # Empty
    metadata={"title": "Empty Doc", "topics": []},
    query=""
)
# Returns CREATE decision (creates new document)
```

## Monitoring and Metrics

### Track Gate Decisions

```python
decisions = {
    "create": 0,
    "update": 0,
    "merge": 0,
    "total_documents": 0
}

for document_path in research_dir.glob("**/*.md"):
    # Load document metadata
    # Track decision type
    # Update metrics

print(f"Documents created: {decisions['create']}")
print(f"Documents updated: {decisions['update']}")
print(f"Documents merged: {decisions['merge']}")
print(f"Duplication prevention rate: "
      f"{(decisions['update'] + decisions['merge']) / decisions['total_documents']:.1%}")
```

## Best Practices

1. **Always use gate before writing**: Call check_before_write() for all new content

2. **Review recommendations**: For MERGE decisions, consider user feedback before merging

3. **Monitor thresholds**: Adjust thresholds based on your duplicate detection success rate

4. **Log decisions**: Enable logging to understand gate behavior

5. **Handle failures gracefully**: If gate fails, fallback to CREATE decision

6. **Update metadata**: Keep topic and question metadata accurate for better matching

## Troubleshooting

### Gate always creates new documents

**Problem**: Similarity scores are always low

**Solutions**:
- Check if topics are spelled consistently
- Verify metadata is populated correctly
- Lower similarity_threshold temporarily for testing
- Enable debug logging to see similarity calculations

### Gate too aggressively merges

**Problem**: Unrelated documents are being merged

**Solutions**:
- Increase similarity_threshold
- Increase merge_threshold
- Check if topics are too generic
- Review similarity calculations in debug logs

### Many similar_docs in results but no action

**Problem**: Gate reports many matches but doesn't take action

**Solutions**:
- All matches below merge_threshold
- Lower thresholds to see if that helps
- Check if content_similarity calculation is working
- Review topic overlap calculations

## Future Enhancements

When Wave 4 is implemented with semantic similarity:

```python
# Future: Semantic similarity
gate = DeduplicationGate(
    db=db,
    research_dir=research_dir,
    use_semantic_similarity=True,  # Uses embeddings
    embedding_model="all-MiniLM-L6-v2"
)
```

This will provide much more accurate duplicate detection based on meaning rather than word frequency.
