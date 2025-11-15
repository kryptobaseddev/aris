#!/usr/bin/env python3
"""Test database creation and schema validation.

This script creates a test database to verify schema integrity.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aris.models.config import ArisConfig
from aris.storage.database import DatabaseManager

# Use a test database path
TEST_DB_PATH = Path(__file__).parent / "test_metadata.db"

print("=" * 80)
print("DATABASE CREATION TEST")
print("=" * 80)
print(f"Test Time: {datetime.now().isoformat()}")
print(f"Test DB Path: {TEST_DB_PATH}")
print()

# Clean up any existing test database
if TEST_DB_PATH.exists():
    print("Removing existing test database...")
    TEST_DB_PATH.unlink()
    print()

# Create database using DatabaseManager
print("1. CREATING DATABASE WITH SCHEMA")
print("-" * 80)
try:
    db_manager = DatabaseManager(TEST_DB_PATH, echo=False)
    db_manager.initialize_database()
    print("✓ Database created successfully")
    print()
except Exception as e:
    print(f"✗ Failed to create database: {e}")
    sys.exit(1)

# Validate tables were created
print("2. VALIDATING SCHEMA")
print("-" * 80)
try:
    conn = sqlite3.connect(str(TEST_DB_PATH))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"Tables created: {len(tables)}")
    for table in tables:
        print(f"  - {table}")
    print()

    # Expected tables
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
    if missing:
        print(f"⚠️  Missing tables: {missing}")
    else:
        print("✓ All expected tables created")
    print()

except Exception as e:
    print(f"✗ Schema validation failed: {e}")
    conn.close()
    sys.exit(1)

# Check key table structures
print("3. KEY TABLE STRUCTURES")
print("-" * 80)

key_tables = [
    "topics",
    "documents",
    "sources",
    "research_sessions",
    "research_hops",
    "quality_metrics",
    "source_credibility",
]

for table in key_tables:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"\n  {table} ({len(columns)} columns):")
        for col in columns[:5]:  # Show first 5 columns
            col_id, name, col_type, not_null, default, pk = col
            nullable = "" if not_null else "NULL"
            pk_marker = "PK" if pk else ""
            print(f"    - {name:20s} {col_type:15s} {nullable:5s} {pk_marker}")
        if len(columns) > 5:
            print(f"    ... and {len(columns) - 5} more columns")
    except Exception as e:
        print(f"  ✗ Error checking {table}: {e}")

print()

# Check indexes
print("4. INDEX VALIDATION")
print("-" * 80)
try:
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
    indexes = cursor.fetchall()
    print(f"Total indexes: {len(indexes)}")

    # Group by table
    by_table = {}
    for idx_name, tbl_name in indexes:
        if tbl_name not in by_table:
            by_table[tbl_name] = []
        by_table[tbl_name].append(idx_name)

    for table, idxs in sorted(by_table.items()):
        print(f"\n  {table}:")
        for idx in idxs:
            print(f"    - {idx}")
except Exception as e:
    print(f"✗ Index check failed: {e}")

print()

# Check foreign keys
print("5. FOREIGN KEY CONSTRAINTS")
print("-" * 80)
for table in key_tables:
    try:
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        if fks:
            print(f"\n  {table}:")
            for fk in fks:
                fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                print(f"    - {from_col} → {ref_table}.{to_col} (on_delete: {on_delete})")
    except Exception as e:
        print(f"  ✗ Error checking {table}: {e}")

print()
print()

# Summary
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"✓ Database creation: SUCCESS")
print(f"✓ Schema validation: {'SUCCESS' if not missing else 'INCOMPLETE'}")
print(f"✓ Tables created: {len(tables)}")
print(f"✓ Indexes created: {len(indexes)}")
print()
print(f"Test database: {TEST_DB_PATH}")
print(f"Size: {TEST_DB_PATH.stat().st_size:,} bytes")
print()

# Cleanup
conn.close()
db_manager.close()

print("Note: Test database can be deleted after review")
print(f"  rm {TEST_DB_PATH}")
print()
