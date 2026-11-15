"""
User model for CampusQueri (Students & Administrators).
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=True, index=True)
    role = db.Column(db.Enum("student", "admin", name="user_role_enum"), default="student", nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    notices_created = db.relationship("Notice", backref="creator", lazy=True, cascade="all, delete-orphan")
    documents_uploaded = db.relationship("Document", backref="uploader", lazy=True, cascade="all, delete-orphan")
    flowcharts_created = db.relationship("Flowchart", backref="creator", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        """Hashes and sets the user's password using Werkzeug scrypt."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies the plain password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Checks if the user has administrator privileges."""
        return self.role == "admin"

    def to_dict(self):
        """Serializes user info for JSON responses (omits password_hash)."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "roll_number": self.roll_number,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
