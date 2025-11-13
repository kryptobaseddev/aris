# ARIS User Guide

**Version**: 1.0
**Date**: 2025-11-12
**Target Audience**: End Users

---

## Welcome to ARIS

**ARIS** (Autonomous Research Intelligence System) prevents document proliferation by intelligently updating existing documents instead of creating duplicates. It uses semantic similarity to detect when you're researching similar topics and automatically consolidates findings.

### Key Benefits
- **No More Duplicates**: ARIS updates existing documents instead of creating new ones
- **Context Retention**: Your research context persists across sessions
- **Quality Assurance**: Multi-model validation ensures accuracy
- **Cost Optimization**: Deduplication reduces redundant API calls
- **Version History**: Git-based tracking of all changes

---

## Quick Start

### Installation

1. **Prerequisites**
   - Python 3.11 or higher
   - Git installed on your system
   - System keyring support (usually pre-installed)

2. **Install ARIS**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd aris-tool

   # Install dependencies (with Poetry)
   poetry install

   # Activate virtual environment
   poetry shell

   # OR: Install with pip
   pip install -e .
   ```

3. **Verify Installation**
   ```bash
   aris --version
   ```

---

### First-Time Setup

#### Step 1: Initialize ARIS
```bash
aris init --name "My Research Project"
```

This creates:
- `.aris/` directory for ARIS data
- SQLite database for metadata
- Git repository for version control
- Configuration files

#### Step 2: Configure API Keys
```bash
# Set your API keys (stored securely in system keyring)
aris config set ANTHROPIC_API_KEY your_anthropic_key
aris config set OPENAI_API_KEY your_openai_key  # Optional
aris config set TAVILY_API_KEY your_tavily_key  # For web search
```

API keys are **never** stored in plain text - they use your system's secure keyring.

#### Step 3: Verify Configuration
```bash
aris config show
```

You should see your configuration with API keys masked.

---

## Core Concepts

### Deduplication
ARIS uses **semantic similarity** to detect when documents cover similar topics:
- **Similarity >0.85**: UPDATE existing document
- **Similarity 0.70-0.85**: MERGE documents
- **Similarity <0.70**: CREATE new document

### Document Structure
ARIS organizes documents by topic:
```
aris-research/
├── ai/
│   ├── machine-learning.md
│   └── natural-language-processing.md
├── databases/
│   └── postgresql-optimization.md
└── cloud/
    └── kubernetes-best-practices.md
```

### Version Control
Every change is tracked in Git:
- Automatic commits when documents are created or updated
- Full version history available
- Easy rollback if needed

---

## Common Workflows

### Workflow 1: Conduct Research

#### Basic Research Command
```bash
aris research "What are best practices for PostgreSQL indexing?"
```

**What Happens:**
1. ARIS searches for existing documents on similar topics
2. If found (similarity >0.85), updates existing document
3. If not found, creates new document in appropriate directory
4. Validates findings with multiple models (if configured)
5. Commits changes to Git with descriptive message

#### Research with Options
```bash
# Specify output directory
aris research "Kubernetes autoscaling strategies" --topic cloud/kubernetes

# Set maximum cost budget
aris research "React hooks patterns" --max-cost 0.50

# Force creation of new document (bypass deduplication)
aris research "New research topic" --force-new

# Verbose mode for debugging
aris research "Topic" --verbose
```

---

### Workflow 2: View Documents

#### Show Document Content
```bash
# Show specific document
aris show ai/machine-learning.md

# Show document with metadata
aris show ai/machine-learning.md --metadata

# Show in JSON format (machine-readable)
aris show ai/machine-learning.md --json
```

#### List All Documents
```bash
# Show system status and document count
aris status

# List all documents
aris status --documents

# List documents in specific topic
aris status --topic ai
```

---

### Workflow 3: Organize Documents

#### Organize by Topic
```bash
# Suggest organization improvements
aris organize suggest

# Apply suggested organization
aris organize apply

# Move document manually
aris organize move ai/ml.md ai/machine-learning.md
```

---

### Workflow 4: Manage Sessions

Sessions preserve your research context across ARIS runs.

#### Start New Session
```bash
aris session start "Project Alpha Research"
```

#### Resume Previous Session
```bash
# List available sessions
aris session list

# Resume specific session
aris session resume <session-id>
```

#### End Current Session
```bash
aris session end
```

---

### Workflow 5: Track Costs

#### View Cost Summary
```bash
# Show total costs
aris cost summary

# Show costs for specific time period
aris cost summary --period week
aris cost summary --period month

# Show per-query costs
aris cost breakdown
```

#### Set Cost Budget
```bash
# Set maximum cost per query
aris config set max_cost_per_query 0.50

# Set daily cost limit
aris config set daily_cost_limit 5.00
```

---

### Workflow 6: Version Control

#### View Document History
```bash
# Show Git log for specific document
aris git log ai/machine-learning.md

# Show recent changes
aris git log --limit 10
```

#### Compare Versions
```bash
# Show diff for document
aris git diff ai/machine-learning.md
```

#### Rollback Changes
```bash
# Revert to previous version
aris git rollback ai/machine-learning.md --commit <commit-hash>
```

---

### Workflow 7: Database Management

#### Check Database Health
```bash
# Show database statistics
aris db status

# Show document count by topic
aris db stats
```

#### Backup Database
```bash
# Create backup
aris db backup --output backup-2025-11-12.db
```

#### Reset Database (⚠️ Destructive)
```bash
# WARNING: This deletes all data
aris db reset --confirm
```

---

## Advanced Usage

### Custom Configuration

#### Configuration File
Create `~/.aris/config.yaml`:
```yaml
# Model configuration
primary_model: claude-3-5-sonnet-20241022
fallback_model: gpt-4

# Deduplication thresholds
update_threshold: 0.85
merge_threshold: 0.70

# Cost controls
max_cost_per_query: 0.50
daily_cost_limit: 5.00

# Performance
max_concurrent_models: 2
timeout_seconds: 60
```

#### Load Custom Config
```bash
aris --config-file ~/my-custom-config.yaml research "topic"
```

---

### JSON Output Mode

For programmatic access, use `--json`:

```bash
# Get status in JSON
aris status --json

# Show document in JSON
aris show ai/ml.md --json

# Research with JSON output
aris research "topic" --json
```

**Example JSON Output:**
```json
{
  "status": "success",
  "document": {
    "path": "ai/machine-learning.md",
    "title": "Machine Learning Best Practices",
    "topics": ["ai", "machine-learning"],
    "confidence": 0.92,
    "sources": 15,
    "created": "2025-11-12T10:30:00Z",
    "updated": "2025-11-12T14:45:00Z"
  }
}
```

---

### Batch Operations

#### Research Multiple Topics
```bash
# Create topics file
cat > topics.txt << EOF
PostgreSQL indexing strategies
Redis caching patterns
MongoDB aggregation pipeline
EOF

# Process batch
while read topic; do
  aris research "$topic" --json >> results.json
done < topics.txt
```

---

## Understanding ARIS Decisions

### Deduplication Workflow

When you run a research command, ARIS:

1. **Analyzes Your Query**
   - Extracts topics and keywords
   - Determines research scope

2. **Searches for Similar Documents**
   - Calculates semantic similarity
   - Considers topic overlap (40% weight)
   - Analyzes content similarity (40% weight)
   - Checks question overlap (20% weight)

3. **Makes Decision**
   - **CREATE** (similarity <0.70): New document needed
   - **MERGE** (similarity 0.70-0.85): Related but distinct
   - **UPDATE** (similarity >0.85): Duplicate research

4. **Executes Action**
   - CREATE: New document in appropriate directory
   - MERGE: Intelligent consolidation preserving both
   - UPDATE: Add findings to existing document

5. **Validates & Commits**
   - Validates with multiple models (if enabled)
   - Commits to Git with description
   - Updates database metadata

---

### Merge Strategies

When ARIS merges documents, it uses one of three strategies:

#### APPEND
- Adds new content at the end
- Use when: New findings are additive

#### INTEGRATE (Default)
- Merges content section by section
- Avoids duplication
- Use when: New findings complement existing

#### REPLACE
- Overwrites existing content
- Use when: New findings supersede old

---

### Conflict Detection

ARIS detects four types of conflicts:

1. **METADATA Conflicts**
   - Divergent confidence scores (>15% difference)
   - Different purpose statements
   - Low topic overlap (<50%)

2. **CONTENT Conflicts**
   - Contradictory claims
   - Opposite conclusions
   - Detected via keyword analysis

3. **STRUCTURAL Conflicts**
   - Major topic divergence
   - Different document structure

4. **CONFIDENCE Conflicts**
   - New research has much lower confidence
   - May indicate unreliable sources

**When conflicts occur:**
- ARIS logs the conflict with severity
- Uses configured resolution strategy (prefer_new, prefer_existing, manual)
- Includes conflict report in commit message

---

## Troubleshooting

### Problem: "API key not found"

**Solution:**
```bash
# Re-set your API key
aris config set ANTHROPIC_API_KEY your_key

# Verify it's set
aris config show
```

---

### Problem: "Database locked"

**Cause**: Another ARIS process is running

**Solution:**
```bash
# Find ARIS processes
ps aux | grep aris

# Kill hung process (if safe)
kill <pid>

# Or reset database (⚠️ loses data)
aris db reset --confirm
```

---

### Problem: "Git error: repository not initialized"

**Solution:**
```bash
# Re-initialize ARIS
aris init --force
```

---

### Problem: Documents not being deduplicated

**Possible Causes:**
- Similarity threshold too high
- Topics not matching
- Vector store not initialized

**Solutions:**
```bash
# Check deduplication settings
aris config show | grep threshold

# Lower threshold if needed
aris config set update_threshold 0.80

# Rebuild vector store
aris db rebuild-vectors
```

---

### Problem: "Cost budget exceeded"

**Solution:**
```bash
# Check current costs
aris cost summary

# Increase budget
aris config set max_cost_per_query 1.00

# Or reset daily limit
aris config set daily_cost_limit 10.00
```

---

### Problem: Slow performance

**Possible Causes:**
- Large document set (>1000 documents)
- Vector search not optimized
- Network latency

**Solutions:**
```bash
# Check database size
aris db stats

# Optimize database
aris db optimize

# Enable verbose logging to diagnose
aris research "topic" --verbose
```

---

## Best Practices

### 1. Regular Backups
```bash
# Backup weekly
aris db backup --output backup-$(date +%Y%m%d).db
```

### 2. Monitor Costs
```bash
# Check costs daily
aris cost summary --period day
```

### 3. Use Descriptive Queries
**Good**: "What are the best practices for PostgreSQL query optimization in high-traffic scenarios?"

**Bad**: "postgres help"

### 4. Review Merge Decisions
```bash
# After merge, review the result
aris show <merged-document> --metadata
aris git diff <merged-document>
```

### 5. Organize Regularly
```bash
# Weekly organization check
aris organize suggest
```

### 6. Session Management
```bash
# Start session for related research
aris session start "Project X Research Sprint"
# ... do research ...
aris session end
```

---

## Tips & Tricks

### Tip 1: Use Topics Strategically
Organize documents by technology/domain:
```
tech/databases/postgres/
tech/cloud/aws/
business/marketing/
```

### Tip 2: Set Per-Project Configs
```bash
# Create project-specific config
cat > .aris/project-config.yaml << EOF
max_cost_per_query: 0.25
update_threshold: 0.90
EOF

# Use it
aris --config-file .aris/project-config.yaml research "topic"
```

### Tip 3: Alias Common Commands
```bash
# Add to ~/.bashrc
alias ar='aris research'
alias as='aris status'
alias ash='aris show'
```

### Tip 4: JSON + jq for Filtering
```bash
# Find all AI-related documents
aris status --documents --json | jq '.documents[] | select(.topics[] | contains("ai"))'

# Get total cost
aris cost summary --json | jq '.total_cost'
```

### Tip 5: Git Integration
```bash
# View full research history
cd aris-research
git log --oneline

# Search commit messages
git log --grep="machine learning"

# See document evolution
git log -p ai/machine-learning.md
```

---

## Getting Help

### CLI Help
```bash
# General help
aris --help

# Command-specific help
aris research --help
aris config --help
aris db --help
```

### Verbose Mode
```bash
# See detailed execution
aris research "topic" --verbose
```

### Check Logs
```bash
# Logs location
~/.aris/logs/aris.log

# View recent logs
tail -f ~/.aris/logs/aris.log
```

### Report Issues
If you encounter a bug:
1. Note the exact command and error message
2. Run with `--verbose` flag
3. Check logs: `~/.aris/logs/aris.log`
4. Report to your team or repository issues

---

## Keyboard Shortcuts

When using interactive prompts:
- `Ctrl+C`: Cancel operation
- `Ctrl+D`: Exit interactive mode
- `Tab`: Autocomplete (if supported by shell)

---

## FAQ

**Q: Can I use ARIS without internet?**
A: No, ARIS requires API access to LLM providers and web search (Tavily).

**Q: Where is my data stored?**
A: All data is local:
- Database: `~/.aris/aris.db`
- Documents: `./aris-research/`
- Logs: `~/.aris/logs/`

**Q: Is my data encrypted?**
A: API keys are encrypted in system keyring. Documents and database are plain text (local-only).

**Q: Can I use my own models?**
A: Yes, configure in `~/.aris/config.yaml` with any OpenAI-compatible API.

**Q: What happens if two ARIS instances run simultaneously?**
A: SQLite handles concurrent reads, but writes may conflict. Use sessions to coordinate.

**Q: Can I export my research?**
A: Yes, documents are plain markdown in `aris-research/`. Copy or Git clone the directory.

**Q: How do I migrate to a new machine?**
A: Copy `.aris/` directory and `aris-research/` directory to new machine. Reconfigure API keys.

**Q: Can I customize the deduplication algorithm?**
A: Yes, adjust thresholds in config:
```yaml
update_threshold: 0.85  # Higher = more strict
merge_threshold: 0.70   # Lower = more aggressive
```

---

## What's Next?

Now that you understand ARIS basics:

1. **Try a Research Query**: `aris research "your topic"`
2. **Explore Documents**: `aris status --documents`
3. **Check Version History**: `aris git log`
4. **Monitor Costs**: `aris cost summary`
5. **Customize Config**: Edit `~/.aris/config.yaml`

For developer documentation, see `DEVELOPER-GUIDE.md`.
For deployment information, see `DEPLOYMENT-GUIDE.md`.

---

## Glossary

- **Deduplication**: Process of detecting and consolidating duplicate research
- **Semantic Similarity**: Meaning-based comparison (not just keywords)
- **Confidence Score**: Measure of validation agreement across models
- **Merge Strategy**: Method for combining documents (APPEND, INTEGRATE, REPLACE)
- **Session**: Research context that persists across commands
- **Provenance**: Tracking of sources and evidence for claims
- **Vector Store**: Database for semantic search and similarity
- **Circuit Breaker**: Safety mechanism for external service failures

---

**End of User Guide**

For questions or issues, consult your team or check `~/.aris/logs/aris.log` for diagnostic information.
