"""
Notice-Document junction model.
Links uploaded files to official notices.
"""
from datetime import datetime
from app.database import db


class NoticeDocument(db.Model):
    __tablename__ = "notice_documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notices.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    display_label = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("notice_id", "document_id", name="uk_notice_document"),
    )

    # Relationships
    document = db.relationship("Document", backref=db.backref("notice_links", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "notice_id": self.notice_id,
            "document_id": self.document_id,
            "display_label": self.display_label,
            "document": self.document.to_dict() if self.document else None
        }

    def __repr__(self):
        return f"<NoticeDocument notice={self.notice_id} doc={self.document_id}>"
