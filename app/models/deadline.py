"""
Deadline model for academic and administrative target date milestones (Phase 6).
Supports:
- Multiple milestones per notice
- Derived status dynamically computed from publication state and target dates
- Inclusive closing dates and opening dates
- Days/hours remaining countdown calculations
- Visual badge helpers and formatted deadline labels
"""
from datetime import datetime
from app.database import db


class Deadline(db.Model):
    __tablename__ = "deadlines"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notices.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_name = db.Column(db.String(150), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    is_closing_date = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(
        db.Enum("upcoming", "ongoing", "extended", "closed", name="deadline_status_enum"),
        default="upcoming",
        nullable=False,
        index=True
    )
    office_id = db.Column(db.Integer, db.ForeignKey("office_information.id", ondelete="SET NULL"), nullable=True, index=True)
    instructions = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_overdue(self) -> bool:
        """True if the target due datetime has already passed UTC now."""
        return datetime.utcnow() > self.due_date

    @property
    def days_remaining(self) -> int:
        """Calculates days remaining until due date, minimum 0."""
        delta = self.due_date - datetime.utcnow()
        return max(0, delta.days)

    @property
    def hours_remaining(self) -> int:
        """Calculates total hours remaining until due date, minimum 0."""
        delta = self.due_date - datetime.utcnow()
        return max(0, int(delta.total_seconds() // 3600))

    @property
    def is_due_today(self) -> bool:
        """True if the deadline falls within the next 24 hours and is not yet overdue."""
        return not self.is_overdue and self.hours_remaining <= 24

    @property
    def effective_status(self) -> str:
        """
        Dynamically computes milestone status from notice publication state and dates.
        Never relies blindly on stored labels.
        Returns: 'draft', 'archived', 'closed', 'extended', 'ongoing', or 'upcoming'.
        """
        if self.notice:
            if self.notice.status == "draft":
                return "draft"
            if self.notice.status == "archived":
                return "archived"

        now = datetime.utcnow()

        # If past due date, always closed/expired
        if now > self.due_date:
            return "closed"

        # Explicitly marked as extended by administration
        if self.status == "extended":
            return "extended"

        # Check if milestone is an opening/commencement milestone
        name_lower = (self.milestone_name or "").lower()
        if any(w in name_lower for w in ["opening", "portal open", "starts", "commence", "begins"]):
            if now < self.due_date:
                return "upcoming"
            return "ongoing"

        return "upcoming"

    @property
    def status_badge(self) -> dict:
        """
        Returns visual presentation metadata for templates:
        {'badge_class': str, 'label': str, 'icon': str}
        """
        eff_status = self.effective_status

        if eff_status == "closed":
            return {
                "badge_class": "bg-secondary text-white",
                "label": "Closed / Expired",
                "icon": "bi-x-circle"
            }

        if eff_status == "extended":
            return {
                "badge_class": "bg-info text-dark border border-info",
                "label": f"Extended ({self.days_remaining}d left)",
                "icon": "bi-arrow-repeat"
            }

        if eff_status == "ongoing":
            return {
                "badge_class": "bg-success text-white",
                "label": "Open Now",
                "icon": "bi-door-open-fill"
            }

        if self.is_due_today:
            return {
                "badge_class": "bg-danger text-white animate-pulse",
                "label": "Due Today!",
                "icon": "bi-exclamation-circle-fill"
            }

        if self.days_remaining <= 3:
            return {
                "badge_class": "bg-danger text-white",
                "label": f"{self.days_remaining} days left",
                "icon": "bi-hourglass-bottom"
            }

        return {
            "badge_class": "bg-warning-subtle text-warning-emphasis border border-warning-subtle",
            "label": f"{self.days_remaining} days left",
            "icon": "bi-hourglass-split"
        }

    @property
    def formatted_due_date(self) -> str:
        """Formats due date for clean academic display."""
        if not self.due_date:
            return "No Date"
        if self.due_date.hour == 23 and self.due_date.minute == 59:
            return self.due_date.strftime("%b %d, %Y (End of Day)")
        if self.due_date.hour == 0 and self.due_date.minute == 0:
            return self.due_date.strftime("%b %d, %Y (Start of Day)")
        return self.due_date.strftime("%b %d, %Y at %I:%M %p")

    def to_dict(self):
        return {
            "id": self.id,
            "notice_id": self.notice_id,
            "milestone_name": self.milestone_name,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "formatted_due_date": self.formatted_due_date,
            "days_remaining": self.days_remaining,
            "hours_remaining": self.hours_remaining,
            "is_overdue": self.is_overdue,
            "is_due_today": self.is_due_today,
            "status": self.effective_status,
            "status_badge": self.status_badge,
            "office": self.office.to_dict() if self.office else None,
            "instructions": self.instructions
        }

    def __repr__(self):
        return f"<Deadline '{self.milestone_name}' due {self.due_date} ({self.effective_status})>"
