# ARIS Suggested Commands

## Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/aris --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_config.py -v

# Run specific test
pytest tests/unit/test_config.py::TestConfigManager::test_singleton_pattern -v
```

## Code Quality
```bash
# Format code
black src tests --line-length 100

# Lint code
ruff check src tests

# Type check
mypy src

# Security audit
bandit -r src
```

## Development
```bash
# Create virtual environment (if needed)
python3 -m venv venv
source venv/bin/activate

# Install dependencies (when Poetry available)
poetry install

# Activate shell (when Poetry available)
poetry shell
```

## Configuration Management
```bash
# Initialize ARIS configuration
python -m aris.cli.main config init

# Set API key (secure, in keyring)
python -m aris.cli.main config set-key tavily <YOUR_KEY>

# View configuration
python -m aris.cli.main config show

# View configuration with full keys (unmasked)
python -m aris.cli.main config show --no-secure

# Validate configuration
python -m aris.cli.main config validate

# List configured API keys
python -m aris.cli.main config list-keys

# Delete API key
python -m aris.cli.main config delete-key tavily
```

## Git Workflow
```bash
# Check status
git status

# Create feature branch
git checkout -b feature/database-schema

# Stage changes
git add src/aris/storage/

# Commit
git commit -m "feat: implement database schema for SQLite"

# Push
git push origin feature/database-schema
```

## Project Navigation
```bash
# List project structure
ls -la src/aris/

# Find files
find src -name "*.py" -type f

# Search code
grep -r "ConfigManager" src/
```

## System Information
```bash
# Python version
python3 --version

# Check installed packages
pip list

# Check keyring backend
python3 -c "import keyring; print(keyring.get_keyring())"
```
