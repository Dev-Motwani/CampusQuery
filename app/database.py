"""
Database layer for CampusQuery.
Provides SQLAlchemy ORM extension and direct mysql-connector-python utilities.
"""
import logging
from flask_sqlalchemy import SQLAlchemy
from app.config import Config

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("campusquery.database")

# Shared SQLAlchemy instance
db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforces foreign key constraint checks on SQLite test engines."""
    if type(dbapi_connection).__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


def get_mysql_raw_connection():
    """
    Creates and returns a raw connection using mysql-connector-python.
    Uses credentials defined in app.config.Config.
    """
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connection_timeout=3
        )
        return connection
    except Exception as e:
        logger.warning("Failed to establish mysql-connector-python raw connection: %s", str(e))
        return None


def check_mysql_health():
    """
    Checks MySQL connectivity safely without leaking credentials.
    Returns:
        dict: {"connected": bool, "database": str, "message": str}
    """
    try:
        import pymysql
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connect_timeout=2
        )
        conn.close()
        return {
            "connected": True,
            "database": Config.DB_NAME,
            "message": "MySQL server reachable and database active"
        }
    except Exception as e:
        # Sanitize error message to prevent accidental credential leakage
        safe_msg = f"MySQL server not reachable on {Config.DB_HOST}:{Config.DB_PORT}"
        logger.info("MySQL healthcheck result: %s (%s)", safe_msg, type(e).__name__)
        return {
            "connected": False,
            "database": Config.DB_NAME,
            "message": safe_msg
        }
