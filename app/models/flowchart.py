"""
Flowchart model for interactive diagram workflows.
Stores node/edge graph data as structured JSON.
"""
from datetime import datetime
from app.database import db


class Flowchart(db.Model):
    __tablename__ = "flowcharts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    description = db.Column(db.String(300), nullable=True)
    graph_data = db.Column(db.JSON, nullable=False)  # JSON structure containing nodes, edges, positions
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def node_count(self) -> int:
        if isinstance(self.graph_data, dict):
            return len(self.graph_data.get("nodes", []))
        return 0

    @property
    def edge_count(self) -> int:
        if isinstance(self.graph_data, dict):
            return len(self.graph_data.get("edges", []))
        return 0

    @property
    def has_decision_nodes(self) -> bool:
        """True if graph contains at least one decision branch node."""
        if isinstance(self.graph_data, dict):
            nodes = self.graph_data.get("nodes", [])
            return any(n.get("type") == "decision" for n in nodes)
        return False

    def is_accessible_by(self, user) -> bool:
        """
        Access control rule (Phase 8 Requirement 11):
        - Administrators can access all flowcharts.
        - Students and visitors can ONLY access if the flowchart is associated with
          at least ONE currently published circular.
        - Flowcharts linked only to draft/archived notices or unattached are strictly blocked.
        """
        if user and getattr(user, "is_admin", False):
            return True

        if not self.notice_links:
            return False

        return any(
            nl.notice is not None and nl.notice.status == "published"
            for nl in self.notice_links
        )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "description": self.description,
            "graph_data": self.graph_data,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "has_decision_nodes": self.has_decision_nodes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "creator_name": self.creator.full_name if getattr(self, "creator", None) else None,
            "associated_notices": [
                {"id": nl.notice.id, "title": nl.notice.title, "status": nl.notice.status}
                for nl in self.notice_links if nl.notice
            ]
        }

    def __repr__(self):
        return f"<Flowchart {self.title}>"

