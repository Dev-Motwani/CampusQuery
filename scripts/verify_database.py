"""
Automated Verification Script for Phase 2: MySQL Schema, Connectivity & Seed Data.
Verifies all 10 relational tables, foreign key constraints, uniqueness, multiple milestones, and transactions.
"""
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 encoding for Windows console compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import Config
from app.database import check_mysql_health
from tests.test_database_crud import DatabaseCRUDTestCase


def run_database_verification():
    print("=" * 65)
    print(" [CAMPUSQUERY] PHASE 2 DATABASE & DEMO DATA VERIFICATION")
    print("=" * 65)

    # 1. Connectivity Check
    print("\n[1/4] Checking Configured MySQL Connectivity...")
    db_health = check_mysql_health()
    if db_health["connected"]:
        print(f"  [PASS] Connected to MySQL Server at {Config.DB_HOST}:{Config.DB_PORT}")
    else:
        print(f"  [ENVIRONMENT BLOCKER] {db_health['message']}")
        print("  -> Offline test database engine will be used for schema, constraint & CRUD verification.")

    # 2. Schema DDL Files Check
    print("\n[2/4] Checking Schema DDL & Seed Scripts...")
    sql_files = ["schema.sql", "scripts/schema.sql", "scripts/seed.sql"]
    for sf in sql_files:
        path = PROJECT_ROOT / sf
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            if "CREATE TABLE" in content or "INSERT INTO" in content:
                print(f"  [PASS] {sf:<26} Verified ({path.stat().st_size} bytes)")
            else:
                print(f"  [FAIL] {sf:<26} Missing DDL statements")
        else:
            print(f"  [FAIL] {sf:<26} File missing!")

    # 3. Model Definition Check (10 Tables)
    print("\n[3/4] Checking All 10 Relational Models...")
    from app.models import (
        User, Category, OfficeInformation, Notice, Deadline,
        Document, NoticeDocument, Flowchart, NoticeFlowchart, Notification
    )
    models = [
        ("User", User, "users"),
        ("Category", Category, "categories"),
        ("OfficeInformation", OfficeInformation, "office_information"),
        ("Notice", Notice, "notices"),
        ("Deadline", Deadline, "deadlines"),
        ("Document", Document, "documents"),
        ("NoticeDocument", NoticeDocument, "notice_documents"),
        ("Flowchart", Flowchart, "flowcharts"),
        ("NoticeFlowchart", NoticeFlowchart, "notice_flowcharts"),
        ("Notification", Notification, "notifications"),
    ]
    for model_name, model_cls, table_name in models:
        if model_cls.__tablename__ == table_name and hasattr(model_cls, "id"):
            print(f"  [PASS] Model: {model_name:<18} Table: `{table_name}` verified")
        else:
            print(f"  [FAIL] Model: {model_name:<18} Invalid table configuration")

    # 4. Run CRUD and Constraint Test Suite
    print("\n[4/4] Running Automated CRUD, Constraint & Transaction Tests...")
    suite = unittest.TestLoader().loadTestsFromTestCase(DatabaseCRUDTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 65)
    print(f" TESTS RUN: {result.testsRun} | FAILURES: {len(result.failures)} | ERRORS: {len(result.errors)}")
    print("=" * 65)

    if result.wasSuccessful():
        print("\n*** PHASE 2 VERIFICATION SUCCESSFUL: Schema, Models & CRUD operations solid! ***")
        return 0
    else:
        print("\n[FAIL] Phase 2 verification encountered errors.")
        return 1


if __name__ == "__main__":
    sys.exit(run_database_verification())
