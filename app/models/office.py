"""
Office Information model for CampusQuery (Phase 6).
Stores administrative office details, departments, locations, operating hours,
contact details, and student visit/submission instructions.
Supports clearly marked sample data indicators.
"""
from datetime import datetime
from app.database import db


class OfficeInformation(db.Model):
    __tablename__ = "office_information"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    office_name = db.Column(db.String(120), nullable=False, index=True)
    department = db.Column(db.String(100), nullable=True)
    building_room = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(30), nullable=True)
    office_hours = db.Column(db.String(100), default="[SAMPLE] Mon-Fri 10:00 AM - 04:30 PM", nullable=False)
    visit_instructions = db.Column(db.Text, nullable=True)
    is_sample = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deadlines = db.relationship("Deadline", backref="office", lazy=True)

    @property
    def display_name(self) -> str:
        """Returns clean display name with sample indicator if applicable."""
        prefix = "[SAMPLE] " if self.is_sample and not self.office_name.startswith("[SAMPLE]") else ""
        return f"{prefix}{self.office_name}"

    def to_dict(self):
        return {
            "id": self.id,
            "office_name": self.office_name,
            "department": self.department,
            "building_room": self.building_room,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "office_hours": self.office_hours,
            "visit_instructions": self.visit_instructions,
            "is_sample": self.is_sample,
            "deadline_count": len(self.deadlines) if self.deadlines else 0
        }

    def __repr__(self):
        return f"<OfficeInformation {self.office_name} ({self.building_room})>"
