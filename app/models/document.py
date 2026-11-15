"""
Document model for official PDF and DOCX attachments (Phase 7).
Stores file metadata, extracted academic text, extraction audit status,
and filesystem references without raw file binaries in the database.
"""
from datetime import datetime
from app.database import db


# Canonical Academic Document Labels (Phase 7 Requirement 7)
ALLOWED_DOCUMENT_LABELS = (
    "Official Form",
    "Required-Document Checklist",
    "Detailed Instructions",
    "Supporting Document"
)


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(255), nullable=False, unique=True, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # size in bytes
    file_type = db.Column(db.String(100), nullable=False)  # MIME type
    label = db.Column(
        db.String(100),
        default="Supporting Document",
        nullable=False,
        index=True
    )  # 'Official Form', 'Required-Document Checklist', 'Detailed Instructions', 'Supporting Document'
    description = db.Column(db.Text, nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)
    extraction_status = db.Column(
        db.String(50),
        default="pending",
        nullable=False,
        index=True
    )  # 'success', 'empty', 'scanned_ocr_required', 'encrypted', 'failed', 'pending'
    sha256_hash = db.Column(db.String(64), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def file_size_kb(self) -> float:
        """Returns file size in kilobytes rounded to two decimals."""
        return round(self.file_size / 1024, 2)

    @property
    def file_size_mb(self) -> float:
        """Returns file size in megabytes rounded to two decimals."""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def is_pdf(self) -> bool:
        """True if document is a PDF format."""
        return self.filename.lower().endswith(".pdf") or "pdf" in self.file_type.lower()

    @property
    def is_docx(self) -> bool:
        """True if document is a DOCX format."""
        return self.filename.lower().endswith(".docx") or "word" in self.file_type.lower() or "officedocument" in self.file_type.lower()

    @property
    def label_badge_class(self) -> str:
        """Returns visual badge class for academic document label."""
        mapping = {
            "Official Form": "bg-primary-subtle text-primary border border-primary-subtle",
            "Required-Document Checklist": "bg-success-subtle text-success border border-success-subtle",
            "Detailed Instructions": "bg-info-subtle text-info border border-info-subtle",
            "Supporting Document": "bg-secondary-subtle text-secondary border border-secondary-subtle",
        }
        return mapping.get(self.label, "bg-light text-dark border")

    @property
    def extraction_badge(self) -> dict:
        """Returns visual presentation badge and status label for text extraction."""
        mapping = {
            "success": {
                "badge_class": "bg-success text-white",
                "label": "Text Extracted",
                "icon": "bi-check2-circle",
                "description": "Text content parsed and searchable."
            },
            "scanned_ocr_required": {
                "badge_class": "bg-warning text-dark border border-warning",
                "label": "Scanned (OCR Req)",
                "icon": "bi-image",
                "description": "Scanned image-only PDF. No selectable text (OCR not implemented)."
            },
            "encrypted": {
                "badge_class": "bg-danger text-white",
                "label": "Encrypted",
                "icon": "bi-shield-lock-fill",
                "description": "Password-protected document."
            },
            "empty": {
                "badge_class": "bg-secondary text-white",
                "label": "No Text",
                "icon": "bi-file-earmark",
                "description": "Document contains 0 pages or no text paragraphs."
            },
            "failed": {
                "badge_class": "bg-danger-subtle text-danger border border-danger-subtle",
                "label": "Parse Failed",
                "icon": "bi-exclamation-triangle-fill",
                "description": "Corrupt or unreadable document file."
            },
            "pending": {
                "badge_class": "bg-info text-dark",
                "label": "Pending",
                "icon": "bi-hourglass-split",
                "description": "Text extraction pending."
            }
        }
        return mapping.get(self.extraction_status, {
            "badge_class": "bg-secondary text-white",
            "label": "Unknown",
            "icon": "bi-question-circle",
            "description": "Status unspecified."
        })

    @property
    def preview_text(self) -> str:
        """Returns a safe short preview snippet of extracted text."""
        if not self.extracted_text:
            return ""
        clean = " ".join(self.extracted_text.split())
        return clean[:200] + ("..." if len(clean) > 200 else "")

    def is_accessible_by(self, user) -> bool:
        """
        Evaluates download authorization and publication state (Phase 7 Requirement 11):
        - Administrators can download any uploaded document.
        - Students / public can ONLY download if the document is linked to at least ONE published notice.
        - Documents linked ONLY to draft or archived notices are strictly inaccessible.
        """
        if user and getattr(user, "is_admin", False):
            return True

        if not self.notice_links:
            return False

        # Must have at least one associated notice that is currently in 'published' state
        return any(
            nl.notice is not None and nl.notice.status == "published"
            for nl in self.notice_links
        )

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_name": self.original_name,
            "label": self.label,
            "description": self.description,
            "file_size_kb": self.file_size_kb,
            "file_type": self.file_type,
            "is_pdf": self.is_pdf,
            "is_docx": self.is_docx,
            "extraction_status": self.extraction_status,
            "sha256_hash": self.sha256_hash,
            "has_extracted_text": bool(self.extracted_text),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "uploader_name": self.uploader.full_name if self.uploader else None,
            "associated_notices": [
                {"id": nl.notice.id, "title": nl.notice.title, "status": nl.notice.status}
                for nl in self.notice_links if nl.notice
            ]
        }

    def __repr__(self):
        return f"<Document id={self.id} '{self.original_name}' [{self.label}] ({self.extraction_status})>"
