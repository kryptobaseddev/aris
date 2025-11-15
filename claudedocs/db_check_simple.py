#!/usr/bin/env python3
"""Simple database integrity check using sqlite3."""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Expected database path
DB_PATH = Path.cwd() / ".aris" / "metadata.db"

print("=" * 80)
print("ARIS DATABASE INTEGRITY CHECK")
print("=" * 80)
print(f"Check Time: {datetime.now().isoformat()}")
print(f"Database Path: {DB_PATH}")
print()

# Check file existence
print("1. FILE STATUS")
print("-" * 80)
if DB_PATH.exists():
    size = DB_PATH.stat().st_size
    print(f"✓ Database file exists")
    print(f"  Size: {size:,} bytes")
    print()
else:
    print("⚠️  Database file does NOT exist")
    print("   Expected path: {}".format(DB_PATH))
    print("   This is normal for a fresh installation.")
    print("   Database will be created on first use.")
    print()
    sys.exit(0)

# Connect and check schema
print("2. SCHEMA VALIDATION")
print("-" * 80)
try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"Tables found: {len(tables)}")
    for table in tables:
        print(f"  - {table}")
    print()

    # Expected tables from models.py
    expected_tables = [
        "conflict_detection",
        "conflicts",
        "document_sources",
        "documents",
        "quality_metrics",
        "relationships",
        "research_hops",
        "research_sessions",
        "source_credibility",
        "sources",
        "topics",
        "validation_rule_history",
    ]

    missing = [t for t in expected_tables if t not in tables]
    extra = [t for t in tables if t not in expected_tables]

    if missing:
        print("⚠️  Missing expected tables:")
        for t in missing:
            print(f"  - {t}")
        print()

    if extra:
        print("ℹ️  Additional tables (not in expected list):")
        for t in extra:
            print(f"  - {t}")
        print()

    if not missing:
        print("✓ All expected tables present")
        print()

except Exception as e:
    print(f"✗ Error connecting to database: {e}")
    conn.close()
    sys.exit(1)

# Count rows in each table
print("3. DATA SUMMARY")
print("-" * 80)
total_rows = 0
for table in sorted(tables):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:30s}: {count:>8,}")
        total_rows += count
    except Exception as e:
        print(f"  {table:30s}: ERROR - {e}")

print(f"  {'TOTAL ROWS':30s}: {total_rows:>8,}")
print()

# Check key table schemas
print("4. KEY TABLE DETAILS")
print("-" * 80)

key_tables = {
    "topics": ["id", "name", "status", "confidence", "created_at"],
    "research_sessions": ["id", "topic_id", "query_text", "status", "budget_target", "total_cost"],
    "quality_metrics": ["session_id", "overall_quality_score", "validation_passed"],
    "documents": ["id", "topic_id", "title", "file_path", "status"],
    "sources": ["id", "url", "title", "tier", "credibility_score"],
}

for table, expected_cols in key_tables.items():
    if table not in tables:
        print(f"\n  {table}: MISSING TABLE")
        continue

    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]

        print(f"\n  {table}:")
        print(f"    Total columns: {len(col_names)}")

        # Check for expected columns
        missing_cols = [c for c in expected_cols if c not in col_names]
        if missing_cols:
            print(f"    ⚠️  Missing expected columns: {missing_cols}")
        else:
            print(f"    ✓ All expected columns present")

        # Show first few columns
        print(f"    Columns: {', '.join(col_names[:5])}" +
              ("..." if len(col_names) > 5 else ""))

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"    Rows: {count:,}")

    except Exception as e:
        print(f"\n  {table}: ERROR - {e}")

print()

# Check for migrations/schema version
print("5. MIGRATION STATUS")
print("-" * 80)
try:
    if "alembic_version" in tables:
        cursor.execute("SELECT version_num FROM alembic_version")
        version = cursor.fetchone()
        if version:
            print(f"✓ Alembic version: {version[0]}")
        else:
            print("⚠️  No migration version recorded")
    else:
        print("ℹ️  No alembic_version table found")
        print("   Database may have been created with create_all() instead of migrations")
except Exception as e:
    print(f"Error checking migration: {e}")

print()

# Sample data check
print("6. SAMPLE DATA (if any)")
print("-" * 80)
if total_rows > 0:
    try:
        # Show topics
        cursor.execute("SELECT name, status FROM topics LIMIT 3")
        topics = cursor.fetchall()
        if topics:
            print("\n  Topics:")
            for name, status in topics:
                print(f"    - {name} ({status})")

        # Show sessions
        cursor.execute("SELECT query_text, status, total_cost FROM research_sessions LIMIT 3")
        sessions = cursor.fetchall()
        if sessions:
            print("\n  Recent Sessions:")
            for query, status, cost in sessions:
                print(f"    - {query[:50]}... ({status}, ${cost:.2f})")

    except Exception as e:
        print(f"Error retrieving sample data: {e}")
else:
    print("  No data in database yet")

print()

# Final summary
print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

status = "✓ GOOD"
if missing:
    status = "⚠️  SCHEMA INCOMPLETE"
elif total_rows == 0:
    status = "ℹ️  EMPTY (ready for use)"

print(f"Database Status: {status}")
print(f"  Path: {DB_PATH}")
print(f"  Size: {DB_PATH.stat().st_size:,} bytes")
print(f"  Tables: {len(tables)}")
print(f"  Total Rows: {total_rows:,}")
print()

conn.close()
