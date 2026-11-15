"""
Database helper redirector.
Re-exports the shared SQLAlchemy instance from app.database.
"""
from app.database import db

__all__ = ["db"]
