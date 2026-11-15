"""
Models package for CampusQuery.
Exports all 10 SQLAlchemy ORM models matching schema.sql.
"""
from app.models.user import User
from app.models.category import Category
from app.models.office import OfficeInformation
from app.models.notice import Notice
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.notice_document import NoticeDocument
from app.models.flowchart import Flowchart
from app.models.notice_flowchart import NoticeFlowchart
from app.models.notification import Notification

__all__ = [
    "User",
    "Category",
    "OfficeInformation",
    "Notice",
    "Deadline",
    "Document",
    "NoticeDocument",
    "Flowchart",
    "NoticeFlowchart",
    "Notification",
]
