"""
Notice-Flowchart junction model.
Links visual procedure diagrams to official notices.
"""
from datetime import datetime
from app.database import db


class NoticeFlowchart(db.Model):
    __tablename__ = "notice_flowcharts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notice_id = db.Column(db.Integer, db.ForeignKey("notices.id", ondelete="CASCADE"), nullable=False, index=True)
    flowchart_id = db.Column(db.Integer, db.ForeignKey("flowcharts.id", ondelete="CASCADE"), nullable=False, index=True)
    caption = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("notice_id", "flowchart_id", name="uk_notice_flowchart"),
    )

    # Relationships
    flowchart = db.relationship("Flowchart", backref=db.backref("notice_links", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "notice_id": self.notice_id,
            "flowchart_id": self.flowchart_id,
            "caption": self.caption,
            "flowchart": self.flowchart.to_dict() if self.flowchart else None
        }

    def __repr__(self):
        return f"<NoticeFlowchart notice={self.notice_id} flowchart={self.flowchart_id}>"
