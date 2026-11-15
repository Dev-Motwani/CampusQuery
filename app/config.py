"""
Configuration module for CampusQuery application.
Loads and validates environment variables.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Base directory: points to the root CampusQuery project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("campusquery.config")


class Config:
    """Base configuration class with validation helpers."""

    # Core Flask Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-key-campusquery-tybca-2026")

    # Database Configuration (supports both DB_* and MYSQL_* naming)
    DB_HOST = os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost"))
    try:
        DB_PORT = int(os.getenv("DB_PORT", os.getenv("MYSQL_PORT", 3306)))
    except (ValueError, TypeError):
        DB_PORT = 3306

    DB_NAME = os.getenv("DB_NAME", os.getenv("MYSQL_DB", "campusqueri_db"))
    DB_USER = os.getenv("DB_USER", os.getenv("MYSQL_USER", "root"))
    DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))

    # Backward compatibility aliases
    MYSQL_HOST = DB_HOST
    MYSQL_PORT = DB_PORT
    MYSQL_DB = DB_NAME
    MYSQL_USER = DB_USER
    MYSQL_PASSWORD = DB_PASSWORD

    # SQLAlchemy Database URI (uses pure-Python PyMySQL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"connect_args": {"connect_timeout": 2}}
        if "mysql" in SQLALCHEMY_DATABASE_URI
        else {}
    )

    # Google Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Uploads (resolved strictly relative to BASE_DIR if relative)
    _raw_upload = os.getenv("UPLOAD_FOLDER", "uploads")
    UPLOAD_FOLDER = str((BASE_DIR / _raw_upload).resolve()) if not os.path.isabs(_raw_upload) else _raw_upload
    DOCUMENTS_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "documents")
    FLOWCHARTS_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "flowcharts")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg", "json"}

    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    @classmethod
    def validate(cls, env_name="development"):
        """
        Validates configuration variables and returns a dict with status and warnings.
        Raises ValueError in production if critical variables are missing or insecure.
        """
        issues = []
        warnings = []

        # 1. SECRET_KEY validation
        if not cls.SECRET_KEY:
            issues.append("SECRET_KEY must not be empty.")
        elif cls.SECRET_KEY in ("dev-fallback-key-campusquery-tybca-2026", "secret", "password"):
            if env_name == "production":
                issues.append("Production requires a strong, random SECRET_KEY.")
            else:
                warnings.append("Using default development SECRET_KEY.")

        # 2. Database validation
        if not cls.DB_HOST:
            issues.append("DB_HOST is required.")
        if not (1 <= cls.DB_PORT <= 65535):
            issues.append(f"DB_PORT must be an integer between 1 and 65535 (got {cls.DB_PORT}).")
        if not cls.DB_NAME:
            issues.append("DB_NAME is required.")
        if not cls.DB_USER:
            issues.append("DB_USER is required.")

        # 3. Gemini API Key (warning in dev, required in production AI)
        if not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY is not set. AI Assistant features will use safe fallback.")

        if issues and env_name == "production":
            raise ValueError(f"Configuration validation failed: {'; '.join(issues)}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "env": env_name
        }


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False}
    }


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
