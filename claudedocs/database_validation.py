#!/usr/bin/env python3
"""Database integrity validation script for ARIS.

This script performs read-only validation of the ARIS database:
- Checks if database file exists
- Validates schema structure
- Counts existing data
- Reports integrity status

NO WRITES OR MODIFICATIONS ARE PERFORMED.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from aris.models.config import ArisConfig
from aris.storage.models import Base
from aris.storage.database import DatabaseManager


def check_database_exists(db_path: Path) -> dict:
    """Check if database file exists and is accessible."""
    result = {
        "exists": db_path.exists(),
        "path": str(db_path),
        "size_bytes": 0,
        "readable": False,
        "writable": False,
    }

    if result["exists"]:
        result["size_bytes"] = db_path.stat().st_size
        result["readable"] = db_path.is_file() and db_path.stat().st_mode & 0o400
        result["writable"] = db_path.stat().st_mode & 0o200

    return result


def validate_schema(db_manager: DatabaseManager) -> dict:
    """Validate database schema against expected models."""
    result = {
        "schema_valid": False,
        "expected_tables": [],
        "existing_tables": [],
        "missing_tables": [],
        "extra_tables": [],
    }

    try:
        # Get expected tables from models
        expected_tables = sorted([table.name for table in Base.metadata.sorted_tables])
        result["expected_tables"] = expected_tables

        # Get existing tables from database
        inspector = inspect(db_manager.engine)
        existing_tables = sorted(inspector.get_table_names())
        result["existing_tables"] = existing_tables

        # Compare
        result["missing_tables"] = [t for t in expected_tables if t not in existing_tables]
        result["extra_tables"] = [t for t in existing_tables if t not in expected_tables]
        result["schema_valid"] = len(result["missing_tables"]) == 0

    except Exception as e:
        result["error"] = str(e)

    return result


def get_table_row_counts(db_manager: DatabaseManager, tables: list) -> dict:
    """Get row counts for each table (read-only)."""
    counts = {}

    try:
        with db_manager.session_scope() as session:
            for table_name in tables:
                try:
                    count = session.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    ).scalar()
                    counts[table_name] = count
                except Exception as e:
                    counts[table_name] = f"ERROR: {str(e)}"
    except Exception as e:
        counts["_error"] = str(e)

    return counts


def check_schema_details(db_manager: DatabaseManager) -> dict:
    """Check detailed schema information for key tables."""
    result = {}

    try:
        inspector = inspect(db_manager.engine)

        # Check key tables
        key_tables = [
            "topics", "documents", "sources", "research_sessions",
            "research_hops", "quality_metrics", "source_credibility"
        ]

        for table_name in key_tables:
            if table_name not in inspector.get_table_names():
                result[table_name] = {"status": "MISSING"}
                continue

            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)

            result[table_name] = {
                "status": "EXISTS",
                "column_count": len(columns),
                "columns": [col["name"] for col in columns],
                "index_count": len(indexes),
                "foreign_key_count": len(foreign_keys),
            }

            # Check for specific important columns
            column_names = [col["name"] for col in columns]

            # Table-specific validations
            if table_name == "research_sessions":
                required = ["id", "topic_id", "query_text", "budget_target", "total_cost"]
                result[table_name]["has_required_columns"] = all(
                    col in column_names for col in required
                )
            elif table_name == "quality_metrics":
                required = ["session_id", "overall_quality_score", "validation_passed"]
                result[table_name]["has_required_columns"] = all(
                    col in column_names for col in required
                )

    except Exception as e:
        result["_error"] = str(e)

    return result


def main():
    """Run database validation."""
    print("=" * 80)
    print("ARIS DATABASE INTEGRITY VALIDATION")
    print("=" * 80)
    print(f"Validation Time: {datetime.now().isoformat()}")
    print()

    # Load configuration
    print("Loading configuration...")
    config = ArisConfig()
    db_path = config.database_path
    print(f"Expected database path: {db_path}")
    print()

    # Check file existence
    print("1. DATABASE FILE STATUS")
    print("-" * 80)
    file_status = check_database_exists(db_path)
    for key, value in file_status.items():
        print(f"  {key}: {value}")
    print()

    if not file_status["exists"]:
        print("⚠️  DATABASE FILE DOES NOT EXIST")
        print("   This is expected for a fresh installation.")
        print("   Database will be created on first use.")
        print()
        return

    # Initialize database manager (read-only check)
    print("2. DATABASE CONNECTION")
    print("-" * 80)
    try:
        db_manager = DatabaseManager(db_path, echo=False)
        print("✓ Database connection successful")
        print()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print()
        return

    # Validate schema
    print("3. SCHEMA VALIDATION")
    print("-" * 80)
    schema_result = validate_schema(db_manager)
    print(f"Schema valid: {schema_result['schema_valid']}")
    print(f"Expected tables: {len(schema_result['expected_tables'])}")
    print(f"Existing tables: {len(schema_result['existing_tables'])}")

    if schema_result['missing_tables']:
        print(f"⚠️  Missing tables: {schema_result['missing_tables']}")

    if schema_result['extra_tables']:
        print(f"⚠️  Extra tables: {schema_result['extra_tables']}")

    if schema_result['schema_valid']:
        print("✓ All expected tables present")
    print()

    # Get row counts
    print("4. DATA SUMMARY")
    print("-" * 80)
    row_counts = get_table_row_counts(db_manager, schema_result['existing_tables'])

    total_rows = 0
    for table_name, count in sorted(row_counts.items()):
        if table_name == "_error":
            print(f"Error getting counts: {count}")
            continue
        print(f"  {table_name:30s}: {count:>8}")
        if isinstance(count, int):
            total_rows += count

    print(f"  {'TOTAL ROWS':30s}: {total_rows:>8}")
    print()

    # Detailed schema check
    print("5. SCHEMA DETAILS (Key Tables)")
    print("-" * 80)
    schema_details = check_schema_details(db_manager)

    for table_name, details in schema_details.items():
        if table_name == "_error":
            print(f"Error: {details}")
            continue

        print(f"\n  {table_name}:")
        for key, value in details.items():
            if key == "columns":
                print(f"    {key}: {', '.join(value[:5])}" +
                      ("..." if len(value) > 5 else ""))
            else:
                print(f"    {key}: {value}")
    print()

    # Final summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    if file_status["exists"]:
        print(f"✓ Database file exists: {db_path}")
        print(f"  Size: {file_status['size_bytes']:,} bytes")
    else:
        print(f"⚠️  Database file does not exist (fresh install)")
        return

    if schema_result['schema_valid']:
        print(f"✓ Schema is valid ({len(schema_result['existing_tables'])} tables)")
    else:
        print(f"✗ Schema issues detected")

    if total_rows > 0:
        print(f"✓ Database contains {total_rows:,} total rows")
    else:
        print(f"ℹ️  Database is empty (no data yet)")

    print()
    print("DATABASE INTEGRITY: " +
          ("✓ GOOD" if schema_result['schema_valid'] else "⚠️ ISSUES DETECTED"))
    print()

    # Close connection
    db_manager.close()


if __name__ == "__main__":
    main()
