"""
Notice model for official college announcements and circulars.
Maintains separate publication status ('draft', 'published', 'archived') from deadline status.
Includes academic criteria: eligibility, required documents, submission instructions, and responsible office.
"""
from datetime import datetime
from app.database import db


class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    summary = db.Column(db.String(300), nullable=True)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    priority = db.Column(
        db.Enum("low", "medium", "high", "urgent", name="notice_priority_enum"),
        default="medium",
        nullable=False,
        index=True
    )
    status = db.Column(
        db.Enum("draft", "published", "archived", name="notice_status_enum"),
        default="draft",
        nullable=False,
        index=True
    )
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Academic Notice Fields (Phase 4)
    eligibility = db.Column(db.Text, nullable=True)
    required_documents = db.Column(db.Text, nullable=True)
    submission_instructions = db.Column(db.Text, nullable=True)
    office_id = db.Column(db.Integer, db.ForeignKey("office_information.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    office = db.relationship("OfficeInformation", foreign_keys=[office_id], backref="associated_notices", lazy=True)
    deadlines = db.relationship("Deadline", backref="notice", lazy=True, cascade="all, delete-orphan", order_by="Deadline.due_date")
    notice_documents = db.relationship("NoticeDocument", backref="notice", lazy=True, cascade="all, delete-orphan")
    notice_flowcharts = db.relationship("NoticeFlowchart", backref="notice", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="notice", lazy=True)

    @property
    def is_published(self) -> bool:
        return self.status == "published"

    @property
    def is_draft(self) -> bool:
        return self.status == "draft"

    @property
    def is_archived(self) -> bool:
        return self.status == "archived"

    @property
    def is_urgent(self) -> bool:
        return self.priority == "urgent"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < datetime.utcnow())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary,
            "content": self.content,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "priority": self.priority,
            "status": self.status,
            "eligibility": self.eligibility,
            "required_documents": self.required_documents,
            "submission_instructions": self.submission_instructions,
            "office": self.office.to_dict() if self.office else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "creator_name": self.creator.full_name if self.creator else None,
            "deadlines": [d.to_dict() for d in self.deadlines],
            "document_count": len(self.notice_documents),
            "flowchart_count": len(self.notice_flowcharts),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Notice {self.title[:30]} ({self.status})>"
