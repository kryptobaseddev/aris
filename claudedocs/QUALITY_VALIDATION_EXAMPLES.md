# Quality Validation Examples & Usage Guide

**For**: Wave 4 Integration - Quality Validation Framework
**Date**: 2025-11-12
**Status**: Complete Examples Package

---

## Quick Start

### Basic Query Validation

```bash
# Validate a research query before starting
aris quality validate \
    --query "What are the latest advances in quantum computing?" \
    --depth standard \
    --budget 0.50

# Output:
# Pre-Execution Validation Report
# Query: What are the latest advances in quantum computing?
# Depth: standard
# Budget: $0.50
#
# Validation Scores:
#   Query Clarity:      0.85
#   Query Specificity:  0.80
#   Budget Sufficiency: 1.00
#   Feasibility:        0.75
#   Overall Readiness:  0.85
#
# ✓ Can Proceed
```

### Classify Source Credibility

```bash
# Determine credibility tier for a source
aris quality sources classify https://arxiv.org/paper/2310.12345

# Output:
# Source Classification
# URL: https://arxiv.org/paper/2310.12345
# Tier: TIER_1
# Credibility Score: 0.950
# Description: Academic, peer-reviewed, official government (0.90-1.00)
```

### Check Source Score with Verification

```bash
aris quality sources score \
    --url https://example.edu/research \
    --verified 2

# Output:
# Source Credibility Scoring
# URL: https://example.edu/research
# Tier: TIER_1
# Verifications: 2
#
# Scoring:
#   Base Score:              0.950
#   Verification Boost:      +0.034
#   Final Score:             0.984
```

---

## Code Examples

### Python API - Pre-Execution Validation

```python
import asyncio
from aris.core.quality_validator import QualityValidator
from aris.models.quality import QualityGateLevel

async def validate_before_research():
    # Create validator with standard gate level
    validator = QualityValidator(gate_level=QualityGateLevel.STANDARD)

    # Validate research query
    report = await validator.validate_pre_execution(
        session_id="research-123",
        query="How does CRISPR gene editing work in treating cancer?",
        depth="standard",
        budget=0.50
    )

    # Check results
    print(f"Can proceed: {report.can_proceed}")
    print(f"Overall readiness: {report.overall_readiness:.2f}")

    if not report.can_proceed:
        print("Issues found:")
        for issue in report.issues:
            print(f"  - {issue}")

        print("Recommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")

    return report
```

### Python API - Post-Execution Validation

```python
import asyncio
from aris.core.quality_validator import QualityValidator
from aris.models.source import Source, SourceType

async def validate_research_results():
    validator = QualityValidator()

    # Prepare sources from research
    sources = [
        Source(
            url="https://www.nature.com/articles/nature12373",
            title="CRISPR-Cas9 for Targeted Cancer Treatment",
            source_type=SourceType.ACADEMIC,
        ),
        Source(
            url="https://pubmed.gov/article/12345",
            title="Gene Therapy Clinical Trials",
            source_type=SourceType.ACADEMIC,
        ),
        Source(
            url="https://www.cancer.org/research",
            title="Cancer Research Overview",
            source_type=SourceType.DOCUMENTATION,
        ),
        Source(
            url="https://github.com/docs/crispr",
            title="CRISPR Implementation Guide",
            source_type=SourceType.DOCUMENTATION,
        ),
        Source(
            url="https://medium.com/biotech/crispr-guide",
            title="Expert Guide to CRISPR",
            source_type=SourceType.BLOG,
        ),
    ]

    # Research findings
    findings = [
        "CRISPR-Cas9 has shown 85%+ success rate in cancer cell targeting",
        "Off-target effects have been reduced to <1% with recent modifications",
        "Clinical trials are underway with promising preliminary results",
        "Gene editing accuracy has improved dramatically in past 3 years",
        "Ethical considerations require careful regulation of human trials",
    ]

    # Validate
    report = await validator.validate_post_execution(
        session_id="research-123",
        query="How does CRISPR work in cancer treatment?",
        sources=sources,
        findings=findings,
        duration_seconds=180
    )

    # Analyze results
    print(f"Validation passed: {report.passed_validation}")
    print(f"Quality score: {report.quality_score:.2f}")
    print(f"Source count: {report.source_count}")
    print(f"Average credibility: {report.average_source_credibility:.2f}")

    if report.contradictions_detected:
        print(f"\nContradictions detected: {report.contradictions_detected}")
        for contradiction in report.contradictions:
            print(f"  Finding 1: {contradiction.finding_1}")
            print(f"  Finding 2: {contradiction.finding_2}")
            print(f"  Severity: {contradiction.severity}")

    if report.issues:
        print("\nIssues:")
        for issue in report.issues:
            print(f"  - {issue}")

    return report
```

### Python API - Confidence Breakdown

```python
import asyncio
from aris.core.quality_validator import QualityValidator
from aris.models.source import Source, SourceType

async def analyze_confidence():
    validator = QualityValidator()

    sources = [
        Source(url="https://arxiv.org/paper/1", title="P1", source_type=SourceType.ACADEMIC),
        Source(url="https://docs.example.com", title="Docs", source_type=SourceType.DOCUMENTATION),
        Source(url="https://medium.com/article", title="Article", source_type=SourceType.BLOG),
    ]

    findings = [
        "Finding 1",
        "Finding 2",
        "Finding 3",
        "Finding 4",
    ]

    # Calculate detailed confidence breakdown
    breakdown = await validator.calculate_confidence_breakdown(
        sources=sources,
        findings=findings,
        duration_seconds=120
    )

    print(f"Overall Confidence: {breakdown.overall_confidence:.2f}")
    print(f"Confidence Level: {breakdown.confidence_summary}\n")

    print("Component Breakdown:")
    for component in breakdown.components:
        weighted = component.weighted_contribution
        print(f"  {component.name}:")
        print(f"    Score: {component.score:.2f}")
        print(f"    Weight: {component.weight:.2f}")
        print(f"    Contribution: {weighted:.2f}")
        print(f"    Rationale: {component.rationale}\n")

    return breakdown
```

### Python API - Source Credibility Tracking

```python
from aris.core.quality_validator import SourceCredibilityTracker
from aris.models.source import Source, SourceType

def track_sources():
    tracker = SourceCredibilityTracker()

    # Classify multiple sources
    sources = [
        ("https://arxiv.org/paper/123", "Academic Paper"),
        ("https://medium.com/article", "Blog Post"),
        ("https://en.wikipedia.org/page", "Wikipedia"),
        ("https://example-blog.blogspot.com/post", "Personal Blog"),
    ]

    print("Source Classification Results:\n")

    for url, title in sources:
        source = Source(
            url=url,
            title=title,
            source_type=SourceType.OTHER
        )

        record = tracker.track_source(source)

        print(f"URL: {url}")
        print(f"Tier: {record.tier.value}")
        print(f"Credibility Score: {record.credibility_score:.3f}")
        print(f"Verification Status: {record.verification_status}\n")

    # Verify a source and see score improvement
    first_source_id = list(tracker.source_records.keys())[0]
    print(f"Before verification:")
    print(f"  Score: {tracker.source_records[first_source_id].credibility_score:.3f}")

    tracker.verify_source(first_source_id)

    print(f"After verification:")
    print(f"  Score: {tracker.source_records[first_source_id].credibility_score:.3f}")
```

### Python API - Different Gate Levels

```python
import asyncio
from aris.core.quality_validator import QualityValidator
from aris.models.quality import QualityGateLevel

async def compare_gate_levels():
    query = "What is machine learning?"
    depth = "standard"
    budget = 0.50

    print("Comparing quality validation across gate levels:\n")

    for level in [QualityGateLevel.PERMISSIVE, QualityGateLevel.STANDARD, QualityGateLevel.STRICT]:
        validator = QualityValidator(gate_level=level)

        report = await validator.validate_pre_execution(
            session_id=f"test-{level.value}",
            query=query,
            depth=depth,
            budget=budget
        )

        print(f"{level.value.upper()} Gate:")
        print(f"  Can Proceed: {report.can_proceed}")
        print(f"  Readiness Score: {report.overall_readiness:.2f}")
        print(f"  Issues Found: {len(report.issues)}")
        if report.issues:
            for issue in report.issues:
                print(f"    - {issue}")
        print()
```

---

## Real-World Scenarios

### Scenario 1: High-Quality Academic Research

**Situation**: Validating a well-formed research query on academic topic

```python
# Input
query = "What are the latest peer-reviewed findings on quantum entanglement in practical applications?"
depth = "deep"
budget = 2.00

# Expected Pre-Execution Results
query_clarity_score = 0.88       # Specific, contains "what" question
query_specificity_score = 0.85   # Multiple specific terms
budget_sufficiency_score = 1.0   # Sufficient for deep research
feasibility_score = 0.85         # Feasible with good budget

# Expected Overall
can_proceed = True
overall_readiness = 0.89

# Expected Post-Execution with good sources
source_count = 8
distinct_sources = 8
average_credibility = 0.87       # Mix of TIER_1 and TIER_2
findings_count = 6
quality_score = 0.85
passed_validation = True
```

### Scenario 2: Vague Query with Budget Concerns

**Situation**: User provides unclear query with limited budget

```python
# Input
query = "stuff and things about technology"
depth = "deep"
budget = 0.10

# Expected Pre-Execution Results
query_clarity_score = 0.25       # Very short, vague
query_specificity_score = 0.15   # Contains vague words
budget_sufficiency_score = 0.3   # Insufficient for deep research
feasibility_score = 0.4          # Not feasible

# Expected Overall
can_proceed = False (with STANDARD gate)
can_proceed = True  (with PERMISSIVE gate)
overall_readiness = 0.28

# Recommendations
# - Refine query to be more specific
# - Add keywords related to actual topic
# - Increase budget or change depth to "quick"
```

### Scenario 3: Research with Contradictions

**Situation**: Research finds conflicting information

```python
# Sources
sources = [  # 3 TIER_1, 2 TIER_2 academic sources
]

# Findings
findings = [
    "Technology X is effective in clinical trials",
    "Technology X is not effective based on meta-analysis",
    "Long-term effects require further study",
    "Short-term results are promising",
    "Additional research is needed",
]

# Expected Post-Execution Results
passed_validation = True         # Issues but not critical
contradictions_detected = 1      # Finding 1 vs 2
quality_score = 0.72             # Reduced due to contradiction
average_credibility = 0.88       # Good sources

# Recommendation
# "Contradiction detected: Findings 1 and 2 conflict.
#  Resolution: Both appear valid - outcomes may differ by timeframe.
#  Suggest separate sections for short-term vs long-term effects."
```

### Scenario 4: Poor Source Quality

**Situation**: Research relies on low-credibility sources

```python
# Sources
sources = [
    Source(url="https://forum.example.com/post", ...),      # TIER_4
    Source(url="https://blog.example.com/article", ...),    # TIER_4
    Source(url="https://reddit.com/thread", ...),           # TIER_3
]

# Expected Post-Execution Results
source_count = 3
distinct_sources = 3
average_credibility = 0.48       # Below standard threshold (0.60)
passed_validation = False        # Quality gate failed
quality_score = 0.45             # Low quality

# Issues
# "Average source credibility 0.48 below minimum 0.60"
# "Consider additional searches for more reputable sources"
```

---

## CLI Workflow Examples

### Example 1: Complete Research Workflow

```bash
# Step 1: Pre-validate the query
aris quality validate \
    --query "What are CRISPR gene therapy advances for treating cancer?" \
    --depth standard \
    --budget 0.50 \
    --gate-level standard

# Step 2: If validation passes, execute research
# (integration with aris research execute command)

# Step 3: View quality report
aris quality report <session-id>

# Step 4: Check source credibility of key sources
aris quality sources classify https://www.nature.com/articles/...
aris quality sources classify https://pubmed.gov/article/...
```

### Example 2: Strict Quality Validation

```bash
# For critical decisions, use strict gate
aris quality validate \
    --query "Safety of experimental gene therapy for inherited blindness" \
    --depth deep \
    --budget 5.00 \
    --gate-level strict

# Strict gate requires:
# - Query clarity > 0.80
# - Query specificity > 0.80
# - Budget sufficiency > 0.85
# - Feasibility > 0.80
```

### Example 3: Permissive Validation for Exploration

```bash
# For early-stage exploration, use permissive gate
aris quality validate \
    --query "AI applications" \
    --depth quick \
    --budget 0.20 \
    --gate-level permissive

# Permissive gate allows:
# - Query clarity > 0.40
# - Quick, exploratory research
# - Lower budget requirements
```

---

## Configuration Examples

### Custom Configuration for Strict Research

```python
# In config file or ArisConfig
quality_config = {
    "quality_gate_level": "strict",

    # Pre-execution thresholds
    "min_query_clarity": 0.80,
    "min_query_specificity": 0.80,
    "min_budget_sufficiency": 0.85,
    "min_feasibility": 0.80,

    # Post-execution thresholds
    "min_source_credibility": 0.75,
    "min_source_diversity": 5,
    "min_coverage_completeness": 0.90,
    "max_contradiction_tolerance": 0.10,

    # Enforcement
    "enforce_pre_execution_gates": True,
    "enforce_post_execution_gates": True,
    "auto_suggest_improvements": True,
}
```

### Custom Configuration for Exploratory Research

```python
# In config file or ArisConfig
quality_config = {
    "quality_gate_level": "permissive",

    # Pre-execution thresholds (relaxed)
    "min_query_clarity": 0.40,
    "min_query_specificity": 0.40,
    "min_budget_sufficiency": 0.50,
    "min_feasibility": 0.50,

    # Post-execution thresholds (permissive)
    "min_source_credibility": 0.50,
    "min_source_diversity": 2,
    "min_coverage_completeness": 0.60,
    "max_contradiction_tolerance": 0.30,

    # Enforcement
    "enforce_pre_execution_gates": False,  # Warnings only
    "enforce_post_execution_gates": False,
    "auto_suggest_improvements": True,
}
```

---

## Troubleshooting

### Q: My query fails pre-execution validation

**A**: Check these aspects:

```bash
# Validate with verbose output
aris quality validate \
    --query "Your query here" \
    --depth standard \
    --budget 0.50 \
    --verbose

# Check specific aspects:
# 1. Query clarity - use specific terms
aris quality validate --query "What is..." --depth quick

# 2. Query specificity - avoid vague words
# Change: "things about technology"
# To: "Applications of machine learning in healthcare"

# 3. Budget sufficiency
# Increase budget or reduce depth:
aris quality validate --query "..." --depth quick --budget 0.20
```

### Q: Post-execution validation fails due to sources

**A**: Improve source quality:

```bash
# Check source credibility
aris quality sources classify <url>

# Look for TIER_1 and TIER_2 sources:
# - TIER_1: .edu, .gov, arxiv.org, published papers
# - TIER_2: Official documentation, established tech blogs

# Rerun research with better source diversity
aris research execute --query "..." --depth deep --focus-on-quality
```

### Q: Contradictions detected in findings

**A**: Investigate and resolve:

```bash
# 1. Review the contradiction details
aris quality report <session_id>

# 2. Consider these possibilities:
# - Different timeframes (short-term vs long-term)
# - Different contexts (different diseases, populations)
# - Genuine disagreement (need more sources)
# - Outdated information (use recent sources)

# 3. Resolve by:
# - Clarifying context in documentation
# - Adding more sources to confirm
# - Separating findings by condition
```

---

## Performance Expectations

### Validation Timing

| Operation | Expected Time | Notes |
|-----------|---|---|
| Pre-execution validation | <100ms | No DB access |
| Post-execution validation | 100-500ms | Depends on source count |
| Confidence calculation | <200ms | 5 components |
| Contradiction detection | O(n²) | 10 findings = ~10ms |
| Source classification | <10ms | Pattern matching |

### For 1000 Research Sessions

| Operation | Total Time | Avg per Session |
|-----------|---|---|
| All pre-validations | ~100 seconds | <100ms |
| All post-validations | ~300 seconds | <300ms |
| Full cycle | ~400 seconds | <400ms |

---

## Integration Checklist

Before using quality validation in production:

- [ ] Run all unit tests: `pytest tests/unit/test_quality_validator.py`
- [ ] Test pre-execution validation with various queries
- [ ] Test post-execution validation with sample sources
- [ ] Verify database schema migration
- [ ] Test all three gate levels (permissive/standard/strict)
- [ ] Validate contradiction detection algorithm
- [ ] Check confidence score calculations
- [ ] Test CLI commands
- [ ] Review security aspects
- [ ] Check performance with large datasets

---

## Next Steps

1. **Integration**: Integrate QualityValidator into ResearchOrchestrator
2. **Testing**: Run comprehensive integration tests
3. **Deployment**: Deploy database schema with Alembic
4. **Monitoring**: Set up metrics collection for quality gates
5. **Tuning**: Adjust gate thresholds based on real-world data

---

**Document**: Quality Validation Examples & Usage Guide
**Status**: Complete
**Last Updated**: 2025-11-12
