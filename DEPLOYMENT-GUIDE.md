# ARIS Deployment Guide

**Version**: 1.0
**Date**: 2025-11-12
**Status**: Pre-Production
**Target**: System Administrators & DevOps Engineers

---

## Table of Contents
1. [Deployment Overview](#deployment-overview)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Security Hardening](#security-hardening)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)

---

## Deployment Overview

### Deployment Modes

ARIS supports three deployment modes:

1. **Single User (Local)**
   - One user, one machine
   - All data local
   - Simplest deployment
   - **Recommended for**: Individual researchers, developers

2. **Shared Environment (Multi-User)**
   - Multiple users, shared server
   - Central database and storage
   - Shared research repository
   - **Recommended for**: Small teams (3-10 users)

3. **Distributed (Enterprise)** ⚠️ Future
   - Multiple instances
   - Load balancing
   - High availability
   - **Status**: Not yet supported

**This guide covers modes 1 and 2.**

---

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 10 GB free space
- **OS**: Linux, macOS, Windows 10+
- **Python**: 3.11 or higher
- **Git**: 2.30 or higher

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 50+ GB SSD
- **OS**: Linux (Ubuntu 22.04+) or macOS
- **Python**: 3.11+
- **Git**: 2.40+

### Network Requirements
- **Outbound HTTPS**: Required for API calls
  - `api.anthropic.com` (Claude API)
  - `api.openai.com` (Optional, OpenAI API)
  - `api.tavily.com` (Web search)
- **Bandwidth**: ~1 MB/query (average)
- **Latency**: <500ms to API endpoints

---

## Installation Methods

### Method 1: Poetry Installation (Recommended)

**Best For**: Development, testing, production

```bash
# 1. Install system dependencies
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv git

# macOS
brew install python@3.11 git

# 2. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# 3. Clone ARIS
git clone https://github.com/your-org/aris-tool.git
cd aris-tool

# 4. Install dependencies
poetry install --no-dev  # Production
# OR
poetry install           # Development (includes dev dependencies)

# 5. Activate environment
poetry shell

# 6. Verify installation
aris --version
```

---

### Method 2: pip Installation

**Best For**: Quick deployment, CI/CD

```bash
# 1. Create virtual environment
python3.11 -m venv aris-env
source aris-env/bin/activate

# 2. Clone and install
git clone https://github.com/your-org/aris-tool.git
cd aris-tool
pip install -e .

# 3. Verify
aris --version
```

---

### Method 3: Docker Installation ⚠️ Future

**Status**: Not yet implemented

```bash
# Future capability
docker pull aris-tool:latest
docker run -v ~/.aris:/root/.aris aris-tool aris --help
```

---

## Configuration

### Step 1: Initialize ARIS

```bash
# Create ARIS workspace
aris init --name "Production Research"

# This creates:
# ~/.aris/              # Config and database
# ./aris-research/      # Document repository (Git)
```

### Step 2: Configure API Keys

#### Option A: Interactive Configuration
```bash
# Set API keys (stored in system keyring)
aris config set ANTHROPIC_API_KEY your_anthropic_key
aris config set TAVILY_API_KEY your_tavily_key
aris config set OPENAI_API_KEY your_openai_key  # Optional
```

#### Option B: Environment Variables
```bash
# Create .env file
cat > ~/.aris/.env << EOF
ANTHROPIC_API_KEY=your_anthropic_key
TAVILY_API_KEY=your_tavily_key
OPENAI_API_KEY=your_openai_key
ARIS_LOG_LEVEL=INFO
EOF

# Set permissions
chmod 600 ~/.aris/.env
```

#### Option C: System Environment
```bash
# Add to ~/.bashrc or ~/.profile
export ANTHROPIC_API_KEY="your_key"
export TAVILY_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

# Reload
source ~/.bashrc
```

### Step 3: Verify Configuration

```bash
# Show configuration (keys masked)
aris config show

# Test API connectivity
aris research "test query" --dry-run
```

---

### Configuration Files

#### System Configuration: `~/.aris/config.yaml`

```yaml
# Model Configuration
primary_model: claude-3-5-sonnet-20241022
fallback_model: gpt-4

# Deduplication Settings
update_threshold: 0.85  # Similarity for UPDATE
merge_threshold: 0.70   # Similarity for MERGE

# Cost Controls
max_cost_per_query: 0.50
daily_cost_limit: 5.00

# Performance
max_concurrent_models: 2
timeout_seconds: 60
retry_attempts: 3

# Logging
log_level: INFO
log_file: ~/.aris/logs/aris.log
log_retention_days: 30

# Storage
database_path: ~/.aris/aris.db
research_directory: ./aris-research
backup_directory: ~/.aris/backups

# Vector Store
vector_model: all-MiniLM-L6-v2
vector_dimension: 384
```

#### Project Configuration: `.aris/project-config.yaml`

Override system settings per project:

```yaml
# Project-specific overrides
max_cost_per_query: 0.25
update_threshold: 0.90
```

---

## Security Hardening

### 1. API Key Security

**DO**:
- ✅ Use system keyring (default)
- ✅ Set restrictive permissions: `chmod 600 ~/.aris/.env`
- ✅ Use environment variables in production
- ✅ Rotate keys regularly (every 90 days)
- ✅ Use separate keys for dev/staging/prod

**DON'T**:
- ❌ Store keys in plain text config files
- ❌ Commit keys to version control
- ❌ Share keys between environments
- ❌ Use root/admin keys

### 2. File Permissions

```bash
# Secure ARIS directory
chmod 700 ~/.aris
chmod 600 ~/.aris/aris.db
chmod 600 ~/.aris/.env
chmod 644 ~/.aris/config.yaml  # If no secrets

# Secure research repository
chmod 755 ./aris-research
```

### 3. Network Security

**For production deployments**:
- Use firewall to restrict outbound connections
- Enable HTTPS only (no HTTP)
- Consider API proxy for rate limiting
- Use VPN for sensitive research

```bash
# Example: UFW firewall rules (Ubuntu)
sudo ufw enable
sudo ufw allow out 443/tcp  # HTTPS only
sudo ufw deny out 80/tcp    # Block HTTP
```

### 4. User Access Control

**Single User**:
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash aris-user
sudo su - aris-user

# Install ARIS
# ... installation steps ...
```

**Multi-User (Shared)**:
```bash
# Create shared group
sudo groupadd aris-users
sudo usermod -a -G aris-users user1
sudo usermod -a -G aris-users user2

# Set group permissions
sudo chgrp -R aris-users /opt/aris-shared
sudo chmod -R 770 /opt/aris-shared
```

### 5. Logging & Auditing

Enable comprehensive logging:

```yaml
# ~/.aris/config.yaml
log_level: INFO  # INFO, DEBUG, WARNING, ERROR
log_file: ~/.aris/logs/aris.log
audit_log: ~/.aris/logs/audit.log  # Track all operations
```

Review logs regularly:
```bash
# Check for errors
tail -f ~/.aris/logs/aris.log | grep ERROR

# Check for suspicious activity
grep -i "failed\|error\|denied" ~/.aris/logs/audit.log
```

---

## Monitoring & Maintenance

### Health Checks

#### System Health
```bash
# Check ARIS status
aris status

# Check database
aris db status

# Check Git repository
aris git status
```

#### Performance Monitoring
```bash
# Check costs
aris cost summary --period day
aris cost summary --period week

# Check document stats
aris db stats

# Check system resources
df -h ~/.aris              # Disk usage
du -sh ./aris-research     # Repository size
```

### Automated Monitoring Script

Create `/opt/aris/monitor.sh`:

```bash
#!/bin/bash
# ARIS Health Check Script

# Configuration
LOG_FILE="/var/log/aris-health.log"
ALERT_EMAIL="admin@example.com"
MAX_COST_DAILY=10.00
MAX_DISK_PCT=80

# Function: Check disk space
check_disk() {
    usage=$(df -h ~/.aris | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $usage -gt $MAX_DISK_PCT ]; then
        echo "$(date): ALERT - Disk usage at ${usage}%" | tee -a $LOG_FILE
        # Send alert
    fi
}

# Function: Check daily costs
check_costs() {
    cost=$(aris cost summary --period day --json | jq '.total_cost')
    if (( $(echo "$cost > $MAX_COST_DAILY" | bc -l) )); then
        echo "$(date): ALERT - Daily cost exceeded: \$${cost}" | tee -a $LOG_FILE
        # Send alert
    fi
}

# Function: Check database health
check_database() {
    aris db status > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "$(date): ERROR - Database health check failed" | tee -a $LOG_FILE
        # Send alert
    fi
}

# Run checks
check_disk
check_costs
check_database

echo "$(date): Health check completed" >> $LOG_FILE
```

Schedule with cron:
```bash
# Run every hour
0 * * * * /opt/aris/monitor.sh
```

---

### Log Rotation

Create `/etc/logrotate.d/aris`:

```
/home/*/.aris/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 user user
}
```

---

### Maintenance Tasks

#### Daily
- [ ] Monitor costs (`aris cost summary --period day`)
- [ ] Check error logs (`tail ~/.aris/logs/aris.log | grep ERROR`)

#### Weekly
- [ ] Review deduplication accuracy
- [ ] Clean up old sessions (`aris session cleanup --older-than 30d`)
- [ ] Check database size (`du -sh ~/.aris/aris.db`)

#### Monthly
- [ ] Backup database (see Backup section)
- [ ] Rotate API keys
- [ ] Review and archive old documents
- [ ] Update dependencies (`poetry update`)

#### Quarterly
- [ ] Security audit
- [ ] Performance review
- [ ] Dependency vulnerability scan

---

## Backup & Recovery

### Backup Strategy

#### Critical Data
1. **Database**: `~/.aris/aris.db`
2. **Config**: `~/.aris/config.yaml`, `~/.aris/.env`
3. **Research Repository**: `./aris-research/` (Git)

#### Backup Script

Create `/opt/aris/backup.sh`:

```bash
#!/bin/bash
# ARIS Backup Script

# Configuration
BACKUP_DIR="/backup/aris"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp ~/.aris/aris.db $BACKUP_DIR/aris_${TIMESTAMP}.db

# Backup config (excluding secrets)
cp ~/.aris/config.yaml $BACKUP_DIR/config_${TIMESTAMP}.yaml

# Backup research repository (Git bundle)
cd ./aris-research
git bundle create $BACKUP_DIR/repo_${TIMESTAMP}.bundle --all

# Compress
cd $BACKUP_DIR
tar -czf aris_backup_${TIMESTAMP}.tar.gz \
    aris_${TIMESTAMP}.db \
    config_${TIMESTAMP}.yaml \
    repo_${TIMESTAMP}.bundle

# Clean up individual files
rm aris_${TIMESTAMP}.db config_${TIMESTAMP}.yaml repo_${TIMESTAMP}.bundle

# Remove old backups
find $BACKUP_DIR -name "aris_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: aris_backup_${TIMESTAMP}.tar.gz"
```

Schedule with cron:
```bash
# Daily backup at 2 AM
0 2 * * * /opt/aris/backup.sh
```

---

### Recovery Procedures

#### Restore Database
```bash
# Stop ARIS (if running)
pkill -f aris

# Restore database
cp /backup/aris/aris_backup_<timestamp>.tar.gz ~/
cd ~
tar -xzf aris_backup_<timestamp>.tar.gz
cp aris_<timestamp>.db ~/.aris/aris.db

# Restart ARIS
aris status
```

#### Restore Research Repository
```bash
# Extract backup
tar -xzf aris_backup_<timestamp>.tar.gz

# Restore from bundle
git clone repo_<timestamp>.bundle ./aris-research

# Or restore into existing repo
cd ./aris-research
git fetch /path/to/repo_<timestamp>.bundle
git reset --hard <commit-hash>
```

#### Disaster Recovery

If complete data loss:

1. **Restore from Backup**
   ```bash
   # Extract latest backup
   tar -xzf /backup/aris/aris_backup_latest.tar.gz

   # Restore database
   cp aris_*.db ~/.aris/aris.db

   # Restore config
   cp config_*.yaml ~/.aris/config.yaml

   # Restore repository
   git clone repo_*.bundle ./aris-research
   ```

2. **Reconfigure API Keys**
   ```bash
   # Re-enter API keys (not in backup for security)
   aris config set ANTHROPIC_API_KEY your_key
   aris config set TAVILY_API_KEY your_key
   ```

3. **Verify Recovery**
   ```bash
   aris status
   aris db status
   aris show <some-document>
   ```

---

## Troubleshooting

### Common Issues

#### Issue: "aris: command not found"

**Cause**: ARIS not in PATH or virtual environment not activated

**Solution**:
```bash
# If using Poetry
poetry shell

# If using venv
source aris-env/bin/activate

# If installed globally
export PATH="$HOME/.local/bin:$PATH"
```

---

#### Issue: "API key not found or invalid"

**Cause**: API keys not configured or keyring not accessible

**Solution**:
```bash
# Re-configure keys
aris config set ANTHROPIC_API_KEY your_key

# Check keyring availability
python -c "import keyring; print(keyring.get_keyring())"

# Fallback to environment variables
export ANTHROPIC_API_KEY="your_key"
```

---

#### Issue: "Database is locked"

**Cause**: Multiple ARIS processes or crashed process

**Solution**:
```bash
# Find ARIS processes
ps aux | grep aris

# Kill hung processes
kill <pid>

# If persists, check for .lock files
rm ~/.aris/.lock

# Or restart database
aris db optimize
```

---

#### Issue: "Out of disk space"

**Solution**:
```bash
# Check disk usage
df -h ~/.aris
du -sh ./aris-research

# Clean up old sessions
aris session cleanup --older-than 30d

# Optimize database
aris db vacuum

# Archive old documents
git -C ./aris-research archive --format=tar.gz --output=old-docs.tar.gz HEAD
```

---

#### Issue: "Git push rejected"

**Cause**: Git repository misconfiguration

**Solution**:
```bash
cd ./aris-research

# Check status
git status

# Check remote
git remote -v

# If needed, configure remote
git remote add origin https://github.com/your-org/research.git
git push -u origin main
```

---

### Debug Mode

Enable detailed logging:

```bash
# Set log level to DEBUG
export ARIS_LOG_LEVEL=DEBUG

# Run with verbose flag
aris research "topic" --verbose

# Check logs
tail -f ~/.aris/logs/aris.log
```

---

## Production Checklist

### Pre-Deployment ✅

- [ ] System requirements met (Python 3.11+, Git, disk space)
- [ ] Dependencies installed (Poetry or pip)
- [ ] API keys obtained (Anthropic, Tavily)
- [ ] Configuration reviewed (`~/.aris/config.yaml`)
- [ ] Security hardening applied (file permissions, keyring)
- [ ] Backup strategy implemented (automated backups)
- [ ] Monitoring configured (health checks, alerts)
- [ ] Log rotation configured
- [ ] Network connectivity verified (HTTPS to APIs)
- [ ] User access controls set (if multi-user)

### Post-Deployment ✅

- [ ] ARIS initialized (`aris init`)
- [ ] API keys configured (`aris config set`)
- [ ] Test research query successful
- [ ] Database healthy (`aris db status`)
- [ ] Git repository functional (`aris git status`)
- [ ] Costs tracked (`aris cost summary`)
- [ ] Logs reviewed (no errors)
- [ ] Backup tested (restore from backup)
- [ ] User training completed (if applicable)
- [ ] Documentation accessible to users

### Ongoing Operations ✅

- [ ] Daily cost monitoring
- [ ] Weekly log reviews
- [ ] Monthly backups verified
- [ ] Quarterly security audits
- [ ] Dependency updates applied
- [ ] User feedback collected
- [ ] Performance metrics reviewed
- [ ] Deduplication accuracy validated

---

## Advanced Deployment

### Multi-User Shared Environment

**Architecture**:
- Shared database: `/opt/aris-shared/aris.db`
- Shared repository: `/opt/aris-shared/research`
- Per-user configs: `~/.aris/config.yaml`

**Setup**:
```bash
# Create shared directory
sudo mkdir -p /opt/aris-shared
sudo groupadd aris-users
sudo chgrp -R aris-users /opt/aris-shared
sudo chmod -R 770 /opt/aris-shared

# Set SGID bit (new files inherit group)
sudo chmod g+s /opt/aris-shared

# User configuration
cat > ~/.aris/config.yaml << EOF
database_path: /opt/aris-shared/aris.db
research_directory: /opt/aris-shared/research
EOF

# Initialize shared repository
cd /opt/aris-shared
aris init --name "Team Research"
```

**Considerations**:
- Use SQLite write-ahead logging (WAL) for concurrency
- Set up Git hooks for automatic pulls
- Monitor for merge conflicts
- Consider PostgreSQL for >10 users

---

### High-Availability Setup ⚠️ Future

**Not yet supported**, but planned features:
- Load balancing across multiple instances
- PostgreSQL instead of SQLite
- Distributed vector store
- Centralized cost tracking
- Real-time synchronization

---

## Support & Resources

### Internal Resources
- **User Guide**: `/USER-GUIDE.md`
- **Developer Guide**: `/DEVELOPER-GUIDE.md`
- **Architecture Docs**: `/docs/` and `/claudedocs/`

### Getting Help
- Check logs: `~/.aris/logs/aris.log`
- Run diagnostics: `aris status --verbose`
- Review documentation
- Contact your team lead or administrator

---

**End of Deployment Guide**

For production deployment, ensure all items in the Production Checklist are completed before going live.
