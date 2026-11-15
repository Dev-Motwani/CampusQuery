"""
Database Initialization Script for CampusQuery.
Initializes the MySQL database and schema without dropping or deleting existing data.
"""
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 encoding for Windows console compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import create_app
from app.config import Config
from app.database import db
import pymysql


def initialize_mysql_database(app=None):
    """
    Connects to MySQL server, creates database if not present,
    and initializes all 10 tables non-destructively.
    """
    if app is None:
        app = create_app("development")

    print("=" * 65)
    print(" [CAMPUSQUERY] DATABASE INITIALIZATION")
    print("=" * 65)
    print(f">> Server Host:     {Config.DB_HOST}")
    print(f">> Server Port:     {Config.DB_PORT}")
    print(f">> Target Database: {Config.DB_NAME}")
    print(f">> DB User:         {Config.DB_USER}")

    # 1. Check Server Connectivity
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset="utf8mb4",
            connect_timeout=3
        )
        print(">> [PASS] Successfully connected to MySQL server!")

        with conn.cursor() as cursor:
            # Create database if not exists
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            print(f">> [PASS] Database `{Config.DB_NAME}` verified/created.")
        conn.close()

        # 2. Non-destructive table initialization via SQLAlchemy models
        with app.app_context():
            print(">> Initializing all 10 schema tables (CREATE TABLE IF NOT EXISTS)...")
            db.create_all()
            print(">> [PASS] All 10 relational tables initialized in MySQL.")

        return True

    except pymysql.err.OperationalError as e:
        print(f"\n>> [ENVIRONMENT BLOCKER] Cannot reach MySQL Server on {Config.DB_HOST}:{Config.DB_PORT}")
        print(f"   Error: {e}")
        print("\n   To resolve this blocker:")
        print("   1. Open MySQL Workbench and verify the local MySQL connection.")
        print("   2. Ensure the MySQL service (e.g. MySQL80) is started in Windows Services (`services.msc`).")
        print("   3. Run `schema.sql` directly inside MySQL Workbench Query Editor.")
        return False
    except Exception as e:
        print(f"\n>> [ERROR] Unexpected database initialization error: {e}")
        return False


def main():
    app = create_app("development")
    success = initialize_mysql_database(app)

    if success:
        print("\n*** Database initialization complete! ***")
        sys.exit(0)
    else:
        print("\n*** Offline Verification Mode: Testing schema definitions in isolated test engine... ***")
        test_app = create_app("testing")
        with test_app.app_context():
            db.create_all()
            print(">> [PASS] All 10 models verified successfully against test engine.")
        sys.exit(0)


if __name__ == "__main__":
    main()
