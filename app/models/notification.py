"""
Notification model for student alerts, circular announcements, and deadline reminders (Phase 6).
Supports in-dashboard notifications only (no external email/SMS), read/unread state tracking,
and notification categorization.
"""
from datetime import datetime
from app.database import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notices.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    notification_type = db.Column(
        db.String(50),
        default="info",
        nullable=False,
        index=True
    )  # 'new_notice', 'deadline_reminder', 'deadline_changed', 'info'
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def badge_class(self) -> str:
        """Returns visual badge class based on notification type."""
        mapping = {
            "new_notice": "bg-primary-subtle text-primary border border-primary-subtle",
            "deadline_reminder": "bg-warning-subtle text-warning border border-warning-subtle",
            "deadline_changed": "bg-danger-subtle text-danger border border-danger-subtle",
            "info": "bg-info-subtle text-info border border-info-subtle"
        }
        return mapping.get(self.notification_type, "bg-secondary-subtle text-secondary")

    @property
    def icon_class(self) -> str:
        """Returns visual icon based on notification type."""
        mapping = {
            "new_notice": "bi-megaphone-fill text-primary",
            "deadline_reminder": "bi-hourglass-split text-warning",
            "deadline_changed": "bi-calendar-event-fill text-danger",
            "info": "bi-info-circle-fill text-info"
        }
        return mapping.get(self.notification_type, "bi-bell-fill text-secondary")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "notice_id": self.notice_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Notification '{self.title}' (read={self.is_read})>"
